
import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from .database import query


def generate_review_pdf(advance_id: int) -> str:
    os.makedirs("data/reports", exist_ok=True)
    path = f"data/reports/acta_revision_avance_{advance_id}.pdf"
    adv = query(
        """SELECT a.*, u.name student, p.name program FROM advances a
           JOIN users u ON u.id=a.student_id JOIN programs p ON p.id=a.program_id
           WHERE a.id=?""",
        (advance_id,)
    )[0]
    ana = query("SELECT * FROM ai_analyses WHERE advance_id=?", (advance_id,))
    findings = []
    if ana:
        findings = query("SELECT * FROM findings WHERE analysis_id=?", (ana[0]["id"],))

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4)
    story = []
    story.append(Paragraph("ACTA DE REVISIÓN DE AVANCE DE TESIS", styles["Title"]))
    story.append(Spacer(1, 12))
    data = [
        ["Estudiante", adv["student"]],
        ["Programa", adv["program"]],
        ["Título", adv["title"]],
        ["Tipo de avance", adv["advance_type"]],
        ["Versión", str(adv["version"] or 1)],
        ["Estado", adv["status"]],
    ]
    if ana:
        data += [
            ["Cumplimiento IA", f'{ana[0]["overall_score"]:.2f}%'],
            ["Nota estimada", f'{ana[0]["grade"]:.2f}/20'],
            ["Modelo", ana[0]["model_used"]],
        ]
    t = Table(data, colWidths=[130, 360])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    if ana:
        story.append(Paragraph("Resumen ejecutivo de IA", styles["Heading2"]))
        story.append(Paragraph(ana[0]["executive_summary"], styles["BodyText"]))
        story.append(Spacer(1, 12))

        # ── Comparación con esquema institucional ─────────────────────────────
        sec_comp_raw = ana[0].get("section_comparison") or "[]"
        try:
            sec_comp = json.loads(sec_comp_raw)
        except Exception:
            sec_comp = []

        if sec_comp:
            story.append(Paragraph("Comparación con esquema institucional", styles["Heading2"]))
            present_count = sum(1 for s in sec_comp if s.get("present"))
            total_count = len(sec_comp)
            story.append(Paragraph(
                f"Secciones encontradas: {present_count} de {total_count} "
                f"({round(present_count/total_count*100)}% de cumplimiento estructural)",
                styles["Normal"]
            ))
            story.append(Spacer(1, 6))

            comp_rows = [["#", "Sección requerida", "Estado"]]
            for i, s in enumerate(sec_comp, 1):
                if s.get("present") and s.get("optional"):
                    estado = "Opcional (no penaliza)"
                elif s.get("present"):
                    estado = "✓ Presente"
                else:
                    estado = "✗ Ausente"
                comp_rows.append([str(i), s.get("section", "-"), estado])

            comp_table = Table(comp_rows, colWidths=[25, 290, 170])
            comp_style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
            for i, s in enumerate(sec_comp, 1):
                if s.get("present") and not s.get("optional"):
                    comp_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#d4edda")))
                elif s.get("optional"):
                    comp_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fff3cd")))
                else:
                    comp_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8d7da")))
            comp_table.setStyle(TableStyle(comp_style))
            story.append(comp_table)
            story.append(Spacer(1, 14))

    story.append(Paragraph("Hallazgos principales", styles["Heading2"]))
    for f in findings[:20]:
        story.append(Paragraph(
            f'<b>{f["severity"]} - {f["section_ref"]}</b>: {f["description"]}',
            styles["BodyText"]
        ))
        story.append(Paragraph(f'Corrección: {f["correction_steps"]}', styles["BodyText"]))
        story.append(Spacer(1, 6))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Firma del asesor: ________________________________", styles["BodyText"]))
    story.append(Paragraph("Firma del estudiante: _____________________________", styles["BodyText"]))
    doc.build(story)
    return path


def generate_comparative_pdf(program_id: int) -> str:
    """Genera un PDF comparativo con todos los alumnos del programa y sus métricas."""
    os.makedirs("data/reports", exist_ok=True)
    path = f"data/reports/reporte_comparativo_programa_{program_id}.pdf"

    programs = query("SELECT * FROM programs WHERE id=?", (program_id,))
    if not programs:
        raise ValueError(f"Programa {program_id} no encontrado")
    program = programs[0]

    students = query(
        """SELECT u.id, u.name, u.email, adv.name AS advisor
           FROM users u
           LEFT JOIN users adv ON adv.id = u.advisor_id
           WHERE u.role='STUDENT' AND u.program_id=?
           ORDER BY u.name""",
        (program_id,)
    )

    student_data = []
    for s in students:
        rows = query(
            """SELECT a.id, a.title, a.advance_type, a.status, a.version, a.created_at,
                      ai.overall_score, ai.grade,
                      ai.structure_score, ai.content_score, ai.form_score, ai.originality_score
               FROM advances a
               LEFT JOIN ai_analyses ai ON ai.advance_id = a.id
               WHERE a.student_id=?
               ORDER BY a.id DESC LIMIT 1""",
            (s["id"],)
        )
        latest = dict(rows[0]) if rows else {}
        student_data.append({**dict(s), **latest})

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=36, rightMargin=36)
    story = []

    story.append(Paragraph(f"REPORTE COMPARATIVO — {program['name'].upper()}", styles["Title"]))
    story.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} | ThesisReview AI",
        styles["Normal"]
    ))
    story.append(Spacer(1, 10))

    grades = [d["grade"] for d in student_data if d.get("grade") is not None]
    avg_grade = sum(grades) / len(grades) if grades else 0
    story.append(Paragraph(
        f"Total estudiantes: {len(students)}  |  Con análisis IA: {len(grades)}  |  "
        f"Nota promedio: {avg_grade:.1f}/20",
        styles["Normal"]
    ))
    story.append(Spacer(1, 12))

    headers = ["Estudiante", "Asesor", "Último avance", "Estado", "Nota", "%"]
    rows_data = [headers]
    for d in student_data:
        rows_data.append([
            (d.get("name") or "-")[:28],
            (d.get("advisor") or "-")[:18],
            (d.get("title") or "Sin avance")[:32],
            (d.get("status") or "Sin avance")[:16],
            f'{d["grade"]:.1f}' if d.get("grade") is not None else "-",
            f'{d["overall_score"]:.0f}%' if d.get("overall_score") is not None else "-",
        ])

    col_widths = [110, 80, 130, 80, 45, 40]
    t = Table(rows_data, colWidths=col_widths)
    header_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(1, len(rows_data)):
        bg = colors.white if i % 2 == 0 else colors.HexColor("#f5f5f5")
        header_style.append(("BACKGROUND", (0, i), (-1, i), bg))
    t.setStyle(TableStyle(header_style))
    story.append(t)
    story.append(Spacer(1, 18))

    ranked = sorted(
        [d for d in student_data if d.get("grade") is not None],
        key=lambda x: x["grade"],
        reverse=True
    )
    if ranked:
        story.append(Paragraph("Ranking por nota IA", styles["Heading2"]))
        for i, d in enumerate(ranked, 1):
            story.append(Paragraph(
                f"{i}. {d['name']} — {d['grade']:.1f}/20 "
                f"(Estructura {d.get('structure_score', 0):.0f}% | "
                f"Contenido {d.get('content_score', 0):.0f}%)",
                styles["BodyText"]
            ))

    doc.build(story)
    return path


def generate_management_pdf() -> str:
    """Genera un reporte ejecutivo de gestión académica para toda la plataforma."""
    os.makedirs("data/reports", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"data/reports/reporte_gestion_{ts}.pdf"

    programs = query("SELECT * FROM programs ORDER BY name")
    total_students = query("SELECT COUNT(*) AS c FROM users WHERE role='STUDENT'")[0]["c"]
    total_advisors = query("SELECT COUNT(*) AS c FROM users WHERE role='ADVISOR'")[0]["c"]
    total_advances = query("SELECT COUNT(*) AS c FROM advances")[0]["c"]
    total_analyses = query("SELECT COUNT(*) AS c FROM ai_analyses")[0]["c"]
    avg_grade_row = query("SELECT AVG(grade) AS g FROM ai_analyses")[0]
    avg_grade = avg_grade_row["g"] or 0

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4)
    story = []

    story.append(Paragraph("REPORTE DE GESTIÓN ACADÉMICA", styles["Title"]))
    story.append(Paragraph(
        f"ThesisReview AI  ·  {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 14))

    summary_data = [
        ["Indicador", "Valor"],
        ["Estudiantes registrados", str(total_students)],
        ["Asesores registrados", str(total_advisors)],
        ["Avances cargados", str(total_advances)],
        ["Avances con análisis IA", str(total_analyses)],
        ["Nota promedio global IA", f"{avg_grade:.1f}/20"],
    ]
    t = Table(summary_data, colWidths=[260, 200])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(t)
    story.append(Spacer(1, 18))

    story.append(Paragraph("Estadísticas por programa académico", styles["Heading2"]))
    for prog in programs:
        pid = prog["id"]
        p_students = query(
            "SELECT COUNT(*) AS c FROM users WHERE role='STUDENT' AND program_id=?", (pid,)
        )[0]["c"]
        p_advances = query(
            "SELECT COUNT(*) AS c FROM advances WHERE program_id=?", (pid,)
        )[0]["c"]
        p_avg_row = query(
            """SELECT AVG(ai.grade) AS g FROM ai_analyses ai
               JOIN advances a ON a.id=ai.advance_id WHERE a.program_id=?""",
            (pid,)
        )[0]
        p_avg = p_avg_row["g"] or 0
        p_approved = query(
            "SELECT COUNT(*) AS c FROM advances WHERE program_id=? AND status='Aprobado'", (pid,)
        )[0]["c"]
        p_pending = query(
            "SELECT COUNT(*) AS c FROM advances WHERE program_id=? AND status IN ('Pendiente','Análisis IA en proceso','En revisión humana')",
            (pid,)
        )[0]["c"]

        story.append(Paragraph(f"■ {prog['name']}", styles["Heading3"]))
        p_data = [
            ["Estudiantes", str(p_students)],
            ["Avances cargados", str(p_advances)],
            ["Nota promedio IA", f"{p_avg:.1f}/20"],
            ["Avances aprobados", str(p_approved)],
            ["Avances en proceso", str(p_pending)],
        ]
        pt = Table(p_data, colWidths=[200, 150])
        pt.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ]))
        story.append(pt)
        story.append(Spacer(1, 10))

    statuses = query(
        "SELECT status, COUNT(*) AS c FROM advances GROUP BY status ORDER BY c DESC"
    )
    if statuses:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Distribución por estado de avances", styles["Heading2"]))
        status_data = [["Estado", "Cantidad"]] + [[s["status"], str(s["c"])] for s in statuses]
        st_table = Table(status_data, colWidths=[220, 100])
        st_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(st_table)

    doc.build(story)
    return path

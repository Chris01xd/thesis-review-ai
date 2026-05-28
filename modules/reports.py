
import os
import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
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


# ── Reporte PDF de Similitud Académica Abierta ───────────────────────────────

def generate_similarity_pdf(report: dict) -> bytes:
    """
    Genera un PDF con los resultados del análisis de similitud académica abierta.
    Recibe el dict devuelto por run_open_similarity() y retorna los bytes del PDF.
    """
    NAVY = colors.HexColor("#1e3a5f")
    RISK_BG = {
        "Bajo":      colors.HexColor("#d4edda"),
        "Moderado":  colors.HexColor("#fff3cd"),
        "Alto":      colors.HexColor("#fde8d8"),
        "Muy alto":  colors.HexColor("#f8d7da"),
    }
    RISK_TC = {
        "Bajo":      colors.HexColor("#155724"),
        "Moderado":  colors.HexColor("#856404"),
        "Alto":      colors.HexColor("#7d3c00"),
        "Muy alto":  colors.HexColor("#721c24"),
    }

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
    )
    W = A4[0] - 5*cm

    def mk_para(text, size=9, bold=False, color=None, align=0, leading=13):
        return Paragraph(text, ParagraphStyle(
            'sp', fontSize=size, leading=leading,
            fontName='Helvetica-Bold' if bold else 'Helvetica',
            textColor=color or colors.black,
            alignment=align, spaceAfter=3,
        ))

    story = []

    # Encabezado
    hdr = Table([[mk_para(
        'REPORTE DE SIMILITUD ACADÉMICA ABIERTA',
        size=13, bold=True, color=colors.white, align=1,
    )]], colWidths=[W])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [hdr, Spacer(1, 4)]
    story.append(mk_para('Universidad Nacional de Trujillo — ThesisReview AI',
                         size=8, color=colors.HexColor("#6b7280")))
    story.append(Spacer(1, 10))

    # Info del documento
    story.append(mk_para("Información del documento", size=11, bold=True, color=NAVY))
    story.append(Spacer(1, 3))
    risk     = report.get("risk_level", "Moderado")
    overall  = report.get("overall_similarity", 0)
    filename = report.get("filename", "—")
    analyzed = report.get("analyzed_at", "—")
    apis     = ", ".join(report.get("apis_consulted", [])) or "—"
    info_rows = [
        ["Archivo analizado",         filename],
        ["Fecha de análisis",         analyzed],
        ["APIs consultadas",          apis],
        ["Fuentes consultadas",       str(report.get("total_sources_checked", 0))],
        ["Fuentes con coincidencias", str(report.get("matching_sources", 0))],
    ]
    info_tbl = Table(info_rows, colWidths=[W*0.36, W*0.64])
    info_tbl.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [info_tbl, Spacer(1, 10)]

    # Resultado global
    story.append(mk_para("Resultado Global", size=11, bold=True, color=NAVY))
    story.append(Spacer(1, 3))
    res_data = [[
        mk_para(f'<b><font size="20">{overall:.1f}%</font></b><br/>'
                '<font size="8" color="#6b7280">Similitud estimada</font>', align=1),
        mk_para(f'Nivel de riesgo:<br/><b><font size="13">{risk}</font></b>',
                size=9, color=RISK_TC.get(risk, colors.black), align=1, leading=16),
    ]]
    res_tbl = Table(res_data, colWidths=[W*0.35, W*0.65])
    res_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), colors.HexColor("#eef2ff")),
        ("BACKGROUND",    (1, 0), (1, 0), RISK_BG.get(risk, colors.lightyellow)),
        ("BOX",           (0, 0), (-1, -1), 1, NAVY),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.white),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [res_tbl, Spacer(1, 12)]

    # Metadatos del documento
    meta = report.get("document_metadata", {})
    if meta.get("title"):
        story.append(mk_para("Metadatos detectados", size=10, bold=True, color=NAVY))
        story.append(mk_para(f'<b>Título:</b> {meta["title"]}', size=8))
        if meta.get("keywords"):
            story.append(mk_para(f'<b>Palabras clave:</b> {", ".join(meta["keywords"])}', size=8))
        story.append(Spacer(1, 8))

    # Tabla de fuentes
    sources = report.get("sources", [])
    if sources:
        story.append(mk_para(f"Fuentes con mayor coincidencia ({len(sources)})",
                             size=11, bold=True, color=NAVY))
        story.append(Spacer(1, 3))
        sh  = ParagraphStyle('sh', fontSize=8, fontName='Helvetica-Bold',
                              textColor=colors.white, leading=10)
        sc8 = ParagraphStyle('sc', fontSize=8, fontName='Helvetica', leading=11)
        sc8c= ParagraphStyle('scc',fontSize=8, fontName='Helvetica-Bold', leading=11,
                              alignment=1)
        src_rows = [[
            Paragraph('#',         sh),
            Paragraph('Título completo', sh),
            Paragraph('API',       sh),
            Paragraph('Año',       sh),
            Paragraph('Similitud', sh),
        ]]
        for i, s in enumerate(sources, 1):
            def _esc(t): return str(t).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n',' ')
            title_raw  = _esc(s.get("title") or "—")
            sim_val    = s.get("similarity_score", 0)
            sim_color  = ("#721c24" if sim_val >= 35 else
                          "#7d3c00" if sim_val >= 20 else
                          "#856404" if sim_val >= 10 else "#155724")
            autores    = _esc(", ".join((s.get("authors") or [])[:3]))
            src_name   = _esc(s.get("source_name") or "")
            subtitle   = ""
            if autores or src_name:
                subtitle = f'<br/><font color="#6b7280" size="7"><i>{autores}{" — " + src_name if src_name else ""}</i></font>'
            src_rows.append([
                Paragraph(str(i), sc8),
                Paragraph(f'{title_raw}{subtitle}', sc8),
                Paragraph(s.get("api", "—"), sc8c),
                Paragraph(str(s.get("year") or "—"), sc8c),
                Paragraph(f'<b><font color="{sim_color}">{sim_val}%</font></b>', sc8c),
            ])
        src_tbl = Table(src_rows, colWidths=[W*0.05, W*0.55, W*0.12, W*0.10, W*0.18])
        src_style = [
            ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("ALIGN",         (2, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]
        for i, s in enumerate(sources, 1):
            sim = s.get("similarity_score", 0)
            bg = (colors.HexColor("#f8d7da") if sim >= 35 else
                  colors.HexColor("#fde8d8") if sim >= 20 else
                  colors.HexColor("#fff3cd") if sim >= 10 else
                  colors.white)
            src_style.append(("BACKGROUND", (0, i), (-1, i), bg))
        src_tbl.setStyle(TableStyle(src_style))
        story += [src_tbl, Spacer(1, 12)]

    # Fragmentos similares
    top_frags = report.get("top_fragments", [])
    if top_frags:
        story.append(HRFlowable(width=W, thickness=0.5, color=colors.lightgrey))
        story.append(mk_para(f"Fragmentos más similares ({len(top_frags)})",
                             size=11, bold=True, color=NAVY))
        story.append(Spacer(1, 4))
        for i, frag in enumerate(top_frags[:10], 1):
            sim_val = frag.get("similarity", 0)
            tc = (colors.HexColor("#155724") if sim_val < 10 else
                  colors.HexColor("#856404") if sim_val < 20 else
                  colors.HexColor("#7d3c00") if sim_val < 35 else
                  colors.HexColor("#721c24"))
            blue_hl = "#93c5fd" if sim_val >= 35 else "#bfdbfe" if sim_val >= 20 else "#dbeafe"
            story.append(mk_para(
                f'<b>Fragmento {i}</b> — <b>{sim_val}% de solapamiento</b>',
                size=8, color=tc,
            ))
            doc_txt   = (frag.get("doc_fragment") or "—")
            src_txt   = (frag.get("source_fragment") or "—")
            src_title = (frag.get("source_title") or "fuente externa")
            doc_safe  = doc_txt.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n',' ')
            src_safe  = src_txt.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n',' ')
            st_safe   = src_title.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            frag_data = [[
                mk_para(
                    f'<b><font color="#1e3a5f">Tu documento:</font></b><br/>'
                    f'<font backColor="{blue_hl}"><i>{doc_safe}</i></font>',
                    size=7, leading=10,
                ),
                mk_para(
                    f'<b><font color="#7d3c00">Fuente:</font></b> '
                    f'<font size="7" color="#374151"><i>{st_safe}</i></font><br/>'
                    f'<i>{src_safe}</i>',
                    size=7, leading=10,
                ),
            ]]
            ft = Table(frag_data, colWidths=[W*0.49, W*0.49])
            ft.setStyle(TableStyle([
                ("BOX",           (0, 0), (-1, -1), 0.8, colors.HexColor("#3b82f6")),
                ("BACKGROUND",    (0, 0), (0, 0),   colors.HexColor("#eff6ff")),
                ("BACKGROUND",    (1, 0), (1, 0),   colors.HexColor("#fffbea")),
                ("INNERGRID",     (0, 0), (-1, -1), 0.4, colors.HexColor("#93c5fd")),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ]))
            story += [ft, Spacer(1, 5)]

    # Limitaciones
    story += [Spacer(1, 6), HRFlowable(width=W, thickness=0.5, color=colors.lightgrey)]
    story.append(mk_para("Limitaciones del análisis", size=10, bold=True, color=NAVY))
    for lim in report.get("limitations", []):
        story.append(mk_para(f"• {lim}", size=8))
    story.append(Spacer(1, 8))

    # Disclaimer
    disc = Table([[mk_para(
        '<b>⚠ AVISO:</b> Este reporte es una estimación técnica basada en fuentes de acceso '
        'abierto. No equivale a Turnitin ni accede a bases privadas. Un resultado bajo '
        '<b>no garantiza</b> originalidad absoluta. No constituye prueba definitiva de plagio.',
        size=8, color=colors.HexColor("#7d3c00"), leading=12,
    )]], colWidths=[W])
    disc.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#fff3cd")),
        ("BOX",           (0, 0), (-1, -1), 0.8, colors.HexColor("#ffc107")),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story += [disc, Spacer(1, 10)]
    story.append(mk_para(
        f'Generado por ThesisReview AI — {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        size=7, color=colors.HexColor("#9ca3af"),
    ))

    doc.build(story)
    return buf.getvalue()


# ── Reporte PDF del Detector de Contenido IA ─────────────────────────────────

def generate_ai_detection_pdf(report: dict) -> bytes:
    """
    Genera un PDF con los resultados del detector de contenido IA.
    Los párrafos sospechosos se muestran con resaltado azul sobre el texto
    para indicar exactamente dónde se detectó posible contenido generado por IA.
    """
    NAVY = colors.HexColor("#1e3a5f")
    VIOLET = colors.HexColor("#7c3aed")
    RISK_BG = {
        "Bajo":      colors.HexColor("#d4edda"),
        "Moderado":  colors.HexColor("#fff3cd"),
        "Alto":      colors.HexColor("#fde8d8"),
        "Muy alto":  colors.HexColor("#f8d7da"),
    }
    RISK_TC = {
        "Bajo":      colors.HexColor("#155724"),
        "Moderado":  colors.HexColor("#856404"),
        "Alto":      colors.HexColor("#7d3c00"),
        "Muy alto":  colors.HexColor("#721c24"),
    }
    # Azul según intensidad del score
    def blue_hl(score):
        if score >= 65: return "#93c5fd"   # blue-300 — muy sospechoso
        if score >= 50: return "#bfdbfe"   # blue-200 — sospechoso
        return "#dbeafe"                   # blue-100 — moderado

    def esc(t):
        return (t or "").replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
    )
    W = A4[0] - 5*cm

    def mk(text, size=9, bold=False, color=None, align=0, leading=13):
        return Paragraph(text, ParagraphStyle(
            'ai', fontSize=size, leading=leading,
            fontName='Helvetica-Bold' if bold else 'Helvetica',
            textColor=color or colors.black,
            alignment=align, spaceAfter=3,
        ))

    story = []

    # Encabezado violeta
    hdr = Table([[mk(
        'REPORTE DE DETECCIÓN DE CONTENIDO IA',
        size=13, bold=True, color=colors.white, align=1,
    )]], colWidths=[W])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), VIOLET),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [hdr, Spacer(1, 4)]
    story.append(mk('Universidad Nacional de Trujillo — ThesisReview AI',
                    size=8, color=colors.HexColor("#6b7280")))
    story.append(mk(
        '<font color="#9ca3af"><i>Estimación técnica — no constituye prueba definitiva de uso de IA</i></font>',
        size=7,
    ))
    story.append(Spacer(1, 10))

    # Info del documento
    story.append(mk("Información del documento", size=11, bold=True, color=NAVY))
    story.append(Spacer(1, 3))
    risk     = report.get("risk_level", "Moderado")
    prob     = report.get("ai_probability", 0)
    stat     = report.get("statistical_score", 0)
    hf_sc    = report.get("hf_score")
    filename = report.get("filename", "—")
    analyzed = report.get("analyzed_at", "—")
    elapsed  = report.get("elapsed_s", 0)
    methods  = ", ".join(report.get("methods_used", ["statistical"]))
    info_rows = [
        ["Archivo analizado",      filename],
        ["Fecha de análisis",      analyzed],
        ["Palabras analizadas",    str(report.get("total_words", 0))],
        ["Oraciones / Párrafos",   f'{report.get("total_sentences",0)} / {report.get("total_paragraphs",0)}'],
        ["Métodos utilizados",     methods],
        ["Tiempo de análisis",     f'{elapsed} s'],
    ]
    inf = Table(info_rows, colWidths=[W*0.36, W*0.64])
    inf.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [inf, Spacer(1, 10)]

    # Resultado global
    story.append(mk("Resultado Global", size=11, bold=True, color=NAVY))
    story.append(Spacer(1, 3))
    hf_cell = (f'Score modelo HF:<br/><b><font size="14">{hf_sc:.1f}%</font></b>'
               if hf_sc is not None else
               '<font size="8" color="#9ca3af">Modelo HF no disponible<br/>Solo análisis estadístico</font>')
    res_data = [[
        mk(f'<b><font size="22">{prob:.1f}%</font></b><br/>'
           '<font size="8" color="#6b7280">Prob. contenido IA</font>', align=1),
        mk(f'Nivel de riesgo:<br/><b><font size="13">{risk}</font></b>',
           size=9, color=RISK_TC.get(risk, colors.black), align=1, leading=16),
        mk(f'Score estadístico:<br/><b><font size="14">{stat:.1f}%</font></b><br/>{hf_cell}',
           size=8, color=colors.HexColor("#374151"), align=1, leading=12),
    ]]
    res_tbl = Table(res_data, colWidths=[W*0.30, W*0.35, W*0.35])
    res_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), colors.HexColor("#f5f3ff")),
        ("BACKGROUND",    (1, 0), (1, 0), RISK_BG.get(risk, colors.lightyellow)),
        ("BACKGROUND",    (2, 0), (2, 0), colors.HexColor("#f9fafb")),
        ("BOX",           (0, 0), (-1, -1), 1, VIOLET),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.white),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [res_tbl, Spacer(1, 12)]

    # Métricas lingüísticas
    gm = report.get("global_metrics", {})
    if gm:
        story.append(mk("Métricas Lingüísticas Globales", size=11, bold=True, color=NAVY))
        story.append(Spacer(1, 3))
        story.append(mk(
            'Las barras indican qué tan "IA-típico" es cada indicador '
            '(rojo = señal de IA fuerte, verde = texto humano típico).',
            size=7, color=colors.HexColor("#6b7280"),
        ))
        story.append(Spacer(1, 4))

        def clamp(v): return max(0.0, min(1.0, v))
        cv   = gm.get("sentence_cv", 0)
        ttr  = gm.get("type_token_ratio", 0)
        rep  = gm.get("ngram_repetition", 0)
        ent  = gm.get("bigram_entropy", 0)
        frm  = gm.get("formal_word_ratio", 0)
        asl  = gm.get("avg_sentence_len", 0)
        p_cv  = clamp((0.60 - cv)   / 0.52)
        p_ttr = clamp((0.72 - ttr)  / 0.28)
        p_rep = clamp((rep - 0.01)  / 0.09)
        p_ent = clamp((3.5 - ent)   / 2.5)
        p_frm = clamp((frm - 0.01)  / 0.07)
        p_asl = clamp((asl - 14.0)  / 16.0)

        def bar_color(p):
            if p < 0.35: return colors.HexColor("#22c55e")
            if p < 0.65: return colors.HexColor("#eab308")
            return colors.HexColor("#ef4444")

        metric_rows = [["Métrica", "Valor", "Indicador IA", "Interpretación"]]
        metrics_data = [
            ("Uniformidad oracional (CV)", f"{cv:.3f}", p_cv,
             "Uniforme (señal IA)" if cv < 0.30 else "Variación normal"),
            ("Diversidad léxica (TTR)",   f"{ttr:.3f}", p_ttr,
             "Vocabulario limitado" if ttr < 0.55 else "Vocabulario variado"),
            ("Repetición n-gramas",        f"{rep*100:.2f}%", p_rep,
             "Frases repetidas" if rep > 0.06 else "Repetición baja"),
            ("Entropía bigrama",           f"{ent:.3f}", p_ent,
             "Texto predecible (señal IA)" if ent < 2.0 else "Entropía normal"),
            ("Transiciones formales",      f"{frm*100:.2f}%", p_frm,
             "Conectores excesivos" if frm > 0.045 else "Conectores normales"),
            ("Long. prom. oración",        f"{asl:.1f} pal.", p_asl,
             "Oraciones largas (señal IA)" if asl > 26 else "Longitud normal"),
        ]
        for name, val, prob_ai, hint in metrics_data:
            bar_w = int(prob_ai * 60)
            metric_rows.append([name, val, f"{'█' * max(1, bar_w // 6)}{'░' * (10 - max(1, bar_w // 6))} {int(prob_ai*100)}%", hint])

        met_tbl = Table(metric_rows, colWidths=[W*0.35, W*0.12, W*0.22, W*0.31])
        met_style = [
            ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 7),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]
        for r_idx, (_, _, p, _) in enumerate(metrics_data, 1):
            bg = (colors.HexColor("#fee2e2") if p >= 0.65 else
                  colors.HexColor("#fef9c3") if p >= 0.35 else
                  colors.HexColor("#dcfce7"))
            met_style.append(("BACKGROUND", (2, r_idx), (2, r_idx), bg))
        met_tbl.setStyle(TableStyle(met_style))
        story += [met_tbl, Spacer(1, 12)]

    # Párrafos sospechosos con resaltado azul
    suspicious = report.get("suspicious_paragraphs", [])
    if suspicious:
        story.append(HRFlowable(width=W, thickness=0.5, color=VIOLET))
        story.append(Spacer(1, 4))
        story.append(mk(
            f'Párrafos Sospechosos ({len(suspicious)}) — '
            '<font color="#3b82f6">Resaltado azul = zona de posible contenido IA</font>',
            size=11, bold=True, color=NAVY,
        ))
        story.append(mk(
            'El texto con fondo azul indica los fragmentos donde los indicadores '
            'lingüísticos sugieren mayor probabilidad de contenido generado por IA.',
            size=7, color=colors.HexColor("#6b7280"),
        ))
        story.append(Spacer(1, 6))

        for idx, para in enumerate(suspicious, 1):
            sc    = para.get("score", 0)
            txt   = esc(para.get("text", "—"))
            hl    = blue_hl(sc)
            tc_sc = RISK_TC.get(
                "Muy alto" if sc >= 65 else "Alto" if sc >= 40 else "Moderado", colors.black
            )
            # Badge header
            badge_data = [[
                mk(f'Párrafo {idx}', size=8, bold=True, color=NAVY),
                mk(f'<b>Probabilidad IA: {sc:.1f}%</b>', size=9, color=tc_sc, align=2),
            ]]
            badge_tbl = Table(badge_data, colWidths=[W*0.5, W*0.5])
            badge_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#f0f4ff")),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING",   (0, 0), (0, -1),  6),
                ("RIGHTPADDING",  (-1, 0), (-1, -1), 6),
                ("BOX",           (0, 0), (-1, -1), 0.8, VIOLET),
            ]))
            story.append(badge_tbl)

            # Texto con resaltado azul
            hl_data = [[mk(
                f'<font backColor="{hl}">{txt}</font>',
                size=8, leading=13,
            )]]
            hl_tbl = Table(hl_data, colWidths=[W])
            hl_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ("BOX",           (0, 0), (-1, -1), 0.8, colors.HexColor("#3b82f6")),
                ("TOPPADDING",    (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ]))
            story += [hl_tbl, Spacer(1, 8)]

        # Mini tabla de métricas de los párrafos
        story.append(mk("Distribución de scores por párrafo (todos los párrafos analizados)",
                        size=9, bold=True, color=NAVY))
        story.append(Spacer(1, 3))
        all_paras = report.get("all_paragraphs", [])
        if all_paras:
            # Usar Paragraph para que el texto haga word-wrap sin cortar
            hdr_para_style = ParagraphStyle('dh', fontSize=7, fontName='Helvetica-Bold',
                                             textColor=colors.white, leading=9)
            cell_style     = ParagraphStyle('dc', fontSize=7, fontName='Helvetica',
                                             leading=10, spaceAfter=0)
            dist_rows = [[
                Paragraph('#',          hdr_para_style),
                Paragraph('Párrafo (texto completo)', hdr_para_style),
                Paragraph('Score IA',   hdr_para_style),
            ]]
            for j, p in enumerate(all_paras[:30], 1):
                full_text = esc(p.get("text", "")).replace('\n', ' ')
                sc = p.get("score", 0)
                score_color = ("#721c24" if sc >= 65 else
                               "#7d3c00" if sc >= 50 else
                               "#374151")
                dist_rows.append([
                    Paragraph(str(j), cell_style),
                    Paragraph(full_text, cell_style),
                    Paragraph(f'<b><font color="{score_color}">{sc:.1f}%</font></b>',
                              ParagraphStyle('ds', fontSize=7, fontName='Helvetica-Bold',
                                             leading=10, alignment=1)),
                ])
            dist_tbl = Table(dist_rows, colWidths=[W*0.06, W*0.76, W*0.18])
            dist_style = [
                ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
                ("GRID",          (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING",   (0, 0), (-1, -1), 4),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
                ("ALIGN",         (2, 0), (-1, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ]
            for j, p in enumerate(all_paras[:30], 1):
                sc = p.get("score", 0)
                bg = (colors.HexColor("#bfdbfe") if sc >= 65 else
                      colors.HexColor("#dbeafe") if sc >= 50 else
                      colors.HexColor("#eff6ff") if sc >= 35 else
                      colors.white)
                dist_style.append(("BACKGROUND", (0, j), (-1, j), bg))
            dist_tbl.setStyle(TableStyle(dist_style))
            story += [dist_tbl, Spacer(1, 10)]

    else:
        story.append(Spacer(1, 6))
        ok_data = [[mk(
            '✓  No se detectaron párrafos con alta probabilidad de contenido IA '
            '(ninguno superó el umbral del 50%).',
            size=9, color=colors.HexColor("#155724"),
        )]]
        ok_tbl = Table(ok_data, colWidths=[W])
        ok_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#d4edda")),
            ("BOX",           (0, 0), (-1, -1), 0.8, colors.HexColor("#28a745")),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story += [ok_tbl, Spacer(1, 10)]

    # Limitaciones
    story += [HRFlowable(width=W, thickness=0.5, color=colors.lightgrey), Spacer(1, 4)]
    story.append(mk("Limitaciones del análisis", size=10, bold=True, color=NAVY))
    for lim in report.get("limitations", []):
        story.append(mk(f"• {lim}", size=8))
    story.append(Spacer(1, 8))

    # Disclaimer
    disc_txt = (report.get("disclaimer") or
                "Este resultado es una estimación técnica y no constituye una prueba definitiva "
                "de uso de inteligencia artificial.")
    disc = Table([[mk(
        f'<b>⚠ AVISO IMPORTANTE:</b> {esc(disc_txt)}',
        size=8, color=colors.HexColor("#5b21b6"), leading=12,
    )]], colWidths=[W])
    disc.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#f5f3ff")),
        ("BOX",           (0, 0), (-1, -1), 0.8, VIOLET),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story += [disc, Spacer(1, 10)]
    story.append(mk(
        f'Generado por ThesisReview AI — {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        size=7, color=colors.HexColor("#9ca3af"),
    ))

    doc.build(story)
    return buf.getvalue()

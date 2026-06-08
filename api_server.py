from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional
import os, json, time
import httpx

from modules.database import init_db, query, execute, log, hash_password, check_password, now
from modules.document_processing import extract_text_from_upload
from modules.ai_engine import local_agentic_analysis, agent_plan_for_document
from modules.plagiarism import run_similarity_check
from modules.citations import validate_citations
from modules.reports import generate_review_pdf, generate_similarity_pdf, generate_ai_detection_pdf
from modules.email_service import send_review_email, send_batch_review_email, send_test_email
from modules.thesis_generator import generate_thesis
from modules.open_similarity import run_open_similarity
from modules.ai_detector import run_ai_detection

init_db()
os.makedirs("data/uploads", exist_ok=True)

app = FastAPI(
    title="ThesisReview API",
    description="API REST para ThesisReview AI — frontend React y app móvil.",
    version="3.0.0",
    contact={"name": "ThesisReview AI", "email": "admin@tesis.edu"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def row_to_dict(row):
    return dict(row) if row else None


def get_user_from_token(token: str) -> Optional[dict]:
    """Extract user from demo token demo-token-{id}."""
    if not token or not token.startswith("demo-token-"):
        return None
    try:
        uid = int(token.replace("demo-token-", ""))
        rows = query("SELECT * FROM users WHERE id=?", (uid,))
        return dict(rows[0]) if rows else None
    except Exception:
        return None


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login", summary="Autenticación de usuario", tags=["Auth"])
def login(req: LoginRequest):
    rows = query("SELECT * FROM users WHERE email=?", (req.email,))
    if not rows:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not check_password(req.password, rows[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    u = dict(rows[0])
    u.pop("password_hash", None)
    log(u["id"], "LOGIN", "users", u["id"])
    return {
        "user": u,
        "token": f"demo-token-{u['id']}",
        "note": "Token demo. En producción usar JWT con expiración."
    }


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/", summary="Health check", tags=["Sistema"])
def root():
    return {"status": "ok", "name": "ThesisReview API", "version": "3.0.0", "docs": "/docs"}


# ── Programas ─────────────────────────────────────────────────────────────────

@app.get("/api/programs", summary="Listar programas", tags=["Programas"])
def get_programs():
    return [dict(r) for r in query("SELECT id, name FROM programs ORDER BY id")]


# ── Estudiantes ───────────────────────────────────────────────────────────────

@app.get("/api/students", summary="Listar estudiantes", tags=["Estudiantes"])
def students():
    rows = query(
        """SELECT u.id, u.name, u.email, u.role, p.name AS program, adv.name AS advisor
           FROM users u
           LEFT JOIN programs p ON p.id = u.program_id
           LEFT JOIN users adv ON adv.id = u.advisor_id
           WHERE u.role='STUDENT' ORDER BY u.id"""
    )
    return [dict(r) for r in rows]


@app.get("/api/student/{student_id}/dashboard", summary="Dashboard del estudiante", tags=["Estudiantes"])
def student_dashboard(student_id: int):
    student_rows = query(
        """SELECT u.id, u.name, u.email, p.name AS program, adv.name AS advisor
           FROM users u
           LEFT JOIN programs p ON p.id = u.program_id
           LEFT JOIN users adv ON adv.id = u.advisor_id
           WHERE u.id=? AND u.role='STUDENT'""", (student_id,)
    )
    if not student_rows:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    advances = query(
        """SELECT a.id, a.title, a.status, a.advance_type, a.version, a.created_at,
                  ai.overall_score, ai.grade,
                  (SELECT COUNT(*) FROM findings f JOIN ai_analyses ai2 ON ai2.id=f.analysis_id
                   WHERE ai2.advance_id=a.id AND COALESCE(f.human_action,'Pendiente') != 'Aceptado') AS findings_pending
           FROM advances a LEFT JOIN ai_analyses ai ON ai.advance_id = a.id
           WHERE a.student_id=? ORDER BY a.id DESC""", (student_id,)
    )
    latest = dict(advances[0]) if advances else None
    return {
        "student": dict(student_rows[0]),
        "latest": latest,
        "summary": {
            "total_advances": len(advances),
            "pending_findings": sum([(r["findings_pending"] or 0) for r in advances]),
            "last_grade": latest["grade"] if latest else None,
            "last_score": latest["overall_score"] if latest else None,
        }
    }


@app.get("/api/student/{student_id}/advances", summary="Avances del estudiante", tags=["Estudiantes"])
def student_advances(student_id: int):
    rows = query(
        """SELECT a.id, a.title, a.status, a.advance_type, a.version, a.created_at,
                  ai.overall_score, ai.grade,
                  (SELECT COUNT(*) FROM findings f JOIN ai_analyses ai2 ON ai2.id=f.analysis_id
                   WHERE ai2.advance_id=a.id) AS total_findings
           FROM advances a LEFT JOIN ai_analyses ai ON ai.advance_id = a.id
           WHERE a.student_id=? ORDER BY a.id DESC""", (student_id,)
    )
    return [dict(r) for r in rows]


@app.get("/api/student/{student_id}/grade-history", summary="Historial de notas", tags=["Avances"])
def grade_history(student_id: int):
    rows = query(
        """SELECT a.id, a.title, a.version, a.created_at, ai.grade, ai.overall_score
           FROM advances a JOIN ai_analyses ai ON ai.advance_id = a.id
           WHERE a.student_id=? ORDER BY a.id ASC""", (student_id,)
    )
    return [dict(r) for r in rows]


# ── Avances ───────────────────────────────────────────────────────────────────

@app.get("/api/advances", summary="Listar avances", tags=["Avances"])
def list_advances(
    student_id: Optional[int] = None,
    advisor_id: Optional[int] = None,
    program_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: Optional[int] = 200,
):
    conditions = []
    params: list = []
    if student_id:
        conditions.append("a.student_id=?"); params.append(student_id)
    if advisor_id:
        conditions.append("a.advisor_id=?"); params.append(advisor_id)
    if program_id:
        conditions.append("a.program_id=?"); params.append(program_id)
    if status:
        conditions.append("a.status=?"); params.append(status)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = query(
        f"""SELECT a.id, a.title, a.status, a.advance_type, a.version, a.created_at,
                   a.page_count, a.student_id, a.advisor_id,
                   ai.overall_score, ai.grade,
                   s.name AS student_name, adv.name AS advisor_name, p.name AS program_name,
                   (SELECT COUNT(*) FROM findings f JOIN ai_analyses ai2 ON ai2.id=f.analysis_id
                    WHERE ai2.advance_id=a.id) AS total_findings
            FROM advances a
            LEFT JOIN ai_analyses ai ON ai.advance_id = a.id
            LEFT JOIN users s ON s.id = a.student_id
            LEFT JOIN users adv ON adv.id = a.advisor_id
            LEFT JOIN programs p ON p.id = a.program_id
            {where} ORDER BY a.id DESC LIMIT ?""",
        params + [limit],
    )
    return [dict(r) for r in rows]


@app.get("/api/advance/{advance_id}", summary="Detalle de avance", tags=["Avances"])
def get_advance(advance_id: int):
    rows = query(
        """SELECT a.*, s.name AS student_name, adv.name AS advisor_name, p.name AS program_name
           FROM advances a
           LEFT JOIN users s ON s.id = a.student_id
           LEFT JOIN users adv ON adv.id = a.advisor_id
           LEFT JOIN programs p ON p.id = a.program_id
           WHERE a.id=?""", (advance_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Avance no encontrado")
    analysis_rows = query("SELECT * FROM ai_analyses WHERE advance_id=?", (advance_id,))
    return {
        "advance": dict(rows[0]),
        "analysis": dict(analysis_rows[0]) if analysis_rows else None,
    }


@app.post("/api/advance/upload", summary="Subir avance + análisis IA", tags=["Avances"])
async def upload_advance(
    file: UploadFile = File(...),
    title: str = Form(...),
    student_id: int = Form(...),
    advance_type: str = Form("Capítulo I"),
    version: int = Form(1),
    auto_analyze: str = Form("1"),
):
    student_rows = query(
        "SELECT id, program_id, advisor_id FROM users WHERE id=? AND role='STUDENT'",
        (student_id,),
    )
    if not student_rows:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    student = dict(student_rows[0])

    program_id = student["program_id"] or 1
    advisor_id = student["advisor_id"]

    # Pick active template for this program (fallback to first available)
    tpl_rows = query(
        "SELECT * FROM templates WHERE program_id=? AND active=1 LIMIT 1", (program_id,)
    )
    if not tpl_rows:
        tpl_rows = query("SELECT * FROM templates WHERE active=1 LIMIT 1")
    if not tpl_rows:
        raise HTTPException(status_code=400, detail="No hay plantillas activas configuradas")
    tpl = dict(tpl_rows[0])

    # Save file
    ext = os.path.splitext(file.filename or "")[1].lower()
    fname = f"{int(time.time())}_{file.filename or 'upload' + ext}"
    fpath = os.path.join("data", "uploads", fname)
    content = await file.read()
    with open(fpath, "wb") as f:
        f.write(content)

    # Extract text
    text, pages = extract_text_from_upload(fpath, ext)

    # Create advance record
    advance_id = execute(
        """INSERT INTO advances(student_id,advisor_id,program_id,template_id,title,advance_type,
                                version,filename,file_path,file_type,text_content,page_count,status,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (student_id, advisor_id, program_id, tpl["id"], title, advance_type,
         version, file.filename, fpath, ext, text, pages,
         "Análisis IA en proceso" if auto_analyze == "1" else "Pendiente", now()),
    )
    log(student_id, "UPLOAD", "advances", advance_id, {"title": title})

    if auto_analyze == "1":
        _run_analysis(advance_id, tpl, student_id)

    return {"advance_id": advance_id, "message": "Avance cargado exitosamente."}


def _run_analysis(advance_id: int, tpl: dict, actor_id: int):
    adv_rows = query("SELECT * FROM advances WHERE id=?", (advance_id,))
    if not adv_rows:
        return
    adv = dict(adv_rows[0])
    expected = (tpl.get("expected_sections") or "").split("|")
    rubric = {}
    try:
        rubric = json.loads(tpl.get("rubric_json") or "{}")
    except Exception:
        pass

    t0 = time.time()
    result = local_agentic_analysis(adv["text_content"] or "", expected, rubric, adv["advance_type"])
    ms = int((time.time() - t0) * 1000)

    execute("DELETE FROM ai_analyses WHERE advance_id=?", (advance_id,))
    aid = execute(
        """INSERT INTO ai_analyses(advance_id,structure_score,content_score,form_score,
                                   originality_score,overall_score,grade,executive_summary,
                                   section_comparison,model_used,processing_ms,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (advance_id, result["scores"]["structure"], result["scores"]["content"],
         result["scores"]["form"], result["scores"]["originality"], result["scores"]["overall"],
         result["grade"], result["executiveSummary"],
         json.dumps(result.get("sectionComparison", []), ensure_ascii=False),
         result.get("modelUsed", "local"), ms, now()),
    )

    for f in result.get("findings", []):
        execute(
            """INSERT INTO findings(analysis_id,type,section_ref,page_ref,severity,description,
                                    correction_steps,example_improvement,recommendation,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (aid, f.get("type"), f.get("section_ref"), f.get("page_ref"), f.get("severity"),
             f.get("description"), f.get("correction_steps"), f.get("example_improvement"),
             f.get("recommendation"), now()),
        )

    run_similarity_check(advance_id, adv["text_content"] or "", adv["program_id"])
    validate_citations(advance_id, adv["text_content"] or "", online=False)
    execute("UPDATE advances SET status=? WHERE id=?", ("En revisión humana", advance_id))
    log(actor_id, "AI_ANALYSIS", "advances", advance_id, {"grade": result["grade"]})
    # Enviar reporte por correo (no bloquea si falla)
    try:
        pdf_path = generate_review_pdf(advance_id)
        send_review_email(advance_id, pdf_path)
    except Exception as _exc:
        print(f"[email] Error al enviar reporte del avance {advance_id}: {_exc}")


@app.post("/api/advance/{advance_id}/analyze", summary="Ejecutar análisis IA", tags=["Avances"])
def analyze_advance(advance_id: int):
    adv_rows = query("SELECT * FROM advances WHERE id=?", (advance_id,))
    if not adv_rows:
        raise HTTPException(status_code=404, detail="Avance no encontrado")
    adv = dict(adv_rows[0])
    # Buscar plantilla: asignada → del programa → cualquier activa
    tpl_rows = query("SELECT * FROM templates WHERE id=?", (adv.get("template_id"),))
    if not tpl_rows:
        tpl_rows = query(
            "SELECT * FROM templates WHERE program_id=? AND active=1 LIMIT 1",
            (adv.get("program_id"),)
        )
    if not tpl_rows:
        tpl_rows = query("SELECT * FROM templates WHERE active=1 LIMIT 1")
    if not tpl_rows:
        raise HTTPException(status_code=400, detail="No hay plantillas activas configuradas en el sistema")
    execute("UPDATE advances SET status=? WHERE id=?", ("Análisis IA en proceso", advance_id))
    try:
        _run_analysis(advance_id, dict(tpl_rows[0]), adv["student_id"])
    except Exception as exc:
        execute("UPDATE advances SET status=? WHERE id=?", ("Error en análisis", advance_id))
        raise HTTPException(status_code=500, detail=f"Error durante el análisis: {exc}")
    return {"message": "Análisis IA completado"}


class BatchAnalyzeRequest(BaseModel):
    advance_ids: list[int]


@app.post("/api/advances/batch-analyze", summary="Análisis IA por lotes", tags=["Avances"])
def batch_analyze(data: BatchAnalyzeRequest):
    """Ejecuta el pipeline de IA en múltiples avances y envía un correo resumen al finalizar."""
    if not data.advance_ids:
        raise HTTPException(status_code=400, detail="Lista de avances vacía")

    results = []
    for advance_id in data.advance_ids:
        try:
            adv_rows = query("SELECT * FROM advances WHERE id=?", (advance_id,))
            if not adv_rows:
                results.append({"advance_id": advance_id, "status": "not_found"})
                continue
            adv = dict(adv_rows[0])
            # Buscar plantilla: primero la asignada, luego cualquier activa del programa, luego la primera activa
            tpl_rows = query("SELECT * FROM templates WHERE id=?", (adv.get("template_id"),))
            if not tpl_rows:
                tpl_rows = query(
                    "SELECT * FROM templates WHERE program_id=? AND active=1 LIMIT 1",
                    (adv.get("program_id"),)
                )
            if not tpl_rows:
                tpl_rows = query("SELECT * FROM templates WHERE active=1 LIMIT 1")
            if not tpl_rows:
                results.append({"advance_id": advance_id, "status": "no_template"})
                continue
            execute("UPDATE advances SET status=? WHERE id=?", ("Análisis IA en proceso", advance_id))
            _run_analysis(advance_id, dict(tpl_rows[0]), adv["student_id"])
            results.append({"advance_id": advance_id, "status": "completed"})
        except Exception as exc:
            print(f"[batch_analyze] Error en avance {advance_id}: {exc}")
            execute("UPDATE advances SET status=? WHERE id=?", ("Error en análisis", advance_id))
            results.append({"advance_id": advance_id, "status": "error", "detail": str(exc)})

    # Enviar correo resumen del lote completo
    processed_ids = [r["advance_id"] for r in results if r["status"] == "completed"]
    try:
        send_batch_review_email(processed_ids)
    except Exception as _exc:
        print(f"[email] Error al enviar resumen del lote: {_exc}")

    return {"processed": len(processed_ids), "results": results}


# ── Hallazgos ─────────────────────────────────────────────────────────────────

@app.get("/api/advance/{advance_id}/findings", summary="Hallazgos de un avance", tags=["Hallazgos"])
def advance_findings(advance_id: int):
    rows = query(
        """SELECT f.id, f.type, f.section_ref, f.severity, f.description,
                  f.correction_steps, f.example_improvement, f.recommendation,
                  f.human_action, f.human_comment
           FROM findings f JOIN ai_analyses ai ON ai.id = f.analysis_id
           WHERE ai.advance_id=?
           ORDER BY CASE f.severity WHEN 'Crítico' THEN 1 WHEN 'Mayor' THEN 2
                    WHEN 'Menor' THEN 3 ELSE 4 END, f.id""",
        (advance_id,),
    )
    return [dict(r) for r in rows]


class FindingUpdate(BaseModel):
    human_action: str
    human_comment: str = ""


@app.patch("/api/finding/{finding_id}", summary="Revisar hallazgo", tags=["Hallazgos"])
def update_finding(finding_id: int, data: FindingUpdate):
    rows = query("SELECT id FROM findings WHERE id=?", (finding_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")
    execute(
        "UPDATE findings SET human_action=?, human_comment=? WHERE id=?",
        (data.human_action, data.human_comment, finding_id),
    )
    return dict(query("SELECT * FROM findings WHERE id=?", (finding_id,))[0])


# ── Citas y similitud ─────────────────────────────────────────────────────────

@app.get("/api/advance/{advance_id}/citations", summary="Citas bibliográficas", tags=["Avances"])
def citations(advance_id: int):
    rows = query(
        "SELECT id, raw_reference, title, year, doi, status, source, suggestion FROM citations WHERE advance_id=? ORDER BY id",
        (advance_id,),
    )
    return [dict(r) for r in rows]


@app.get("/api/advance/{advance_id}/similarity", summary="Resultados de similitud", tags=["Avances"])
def similarity(advance_id: int):
    rows = query(
        """SELECT pr.id, pr.similarity, pr.section_ref, pr.status, a.title AS compared_title
           FROM plagiarism_results pr LEFT JOIN advances a ON a.id = pr.compared_advance_id
           WHERE pr.advance_id=? ORDER BY pr.similarity DESC""",
        (advance_id,),
    )
    return [dict(r) for r in rows]


# ── Reportes ──────────────────────────────────────────────────────────────────

@app.get("/api/advance/{advance_id}/report", summary="Descargar reporte PDF", tags=["Reportes"])
def download_report(advance_id: int):
    rows = query("SELECT id, status FROM advances WHERE id=?", (advance_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Avance no encontrado")
    path = generate_review_pdf(advance_id)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=500, detail="No se pudo generar el reporte")
    return FileResponse(path, media_type="application/pdf", filename=os.path.basename(path))


# ── Estadísticas ──────────────────────────────────────────────────────────────

@app.get("/api/stats", summary="Estadísticas del programa", tags=["Stats"])
def get_stats(program_id: Optional[int] = None):
    cond = "WHERE a.program_id=?" if program_id else ""
    params_prog = (program_id,) if program_id else ()

    total_students = query(
        "SELECT COUNT(*) AS c FROM users WHERE role='STUDENT'" +
        (" AND program_id=?" if program_id else ""), params_prog
    )[0]["c"]

    total_advances = query(
        f"SELECT COUNT(*) AS c FROM advances a {cond}", params_prog
    )[0]["c"]

    pending = query(
        f"SELECT COUNT(*) AS c FROM advances a {cond} {'AND' if cond else 'WHERE'} a.status='En revisión humana'",
        params_prog,
    )[0]["c"]

    approved = query(
        f"SELECT COUNT(*) AS c FROM advances a {cond} {'AND' if cond else 'WHERE'} a.status='Aprobado'",
        params_prog,
    )[0]["c"]

    rejected = query(
        f"SELECT COUNT(*) AS c FROM advances a {cond} {'AND' if cond else 'WHERE'} a.status='Rechazado'",
        params_prog,
    )[0]["c"]

    avg_rows = query(
        f"""SELECT AVG(ai.grade) AS avg_grade, AVG(ai.overall_score) AS avg_score
            FROM ai_analyses ai JOIN advances a ON a.id=ai.advance_id {cond}""",
        params_prog,
    )
    avg_grade = avg_rows[0]["avg_grade"] if avg_rows else None
    avg_score = avg_rows[0]["avg_score"] if avg_rows else None

    sev_rows = query(
        f"""SELECT f.severity, COUNT(*) AS count FROM findings f
            JOIN ai_analyses ai ON ai.id=f.analysis_id
            JOIN advances a ON a.id=ai.advance_id {cond}
            GROUP BY f.severity ORDER BY count DESC""",
        params_prog,
    )

    status_rows = query(
        f"SELECT a.status, COUNT(*) AS count FROM advances a {cond} GROUP BY a.status ORDER BY count DESC",
        params_prog,
    )

    grade_dist = []
    ranges = [(0, 10, "0-10"), (11, 13, "11-13"), (14, 16, "14-16"), (17, 18, "17-18"), (19, 20, "19-20")]
    for lo, hi, label in ranges:
        cnt = query(
            f"SELECT COUNT(*) AS c FROM ai_analyses ai JOIN advances a ON a.id=ai.advance_id {cond} {'AND' if cond else 'WHERE'} ai.grade BETWEEN ? AND ?",
            list(params_prog) + [lo, hi],
        )[0]["c"]
        grade_dist.append({"range": label, "count": cnt})

    return {
        "total_students": total_students,
        "total_advances": total_advances,
        "advances_pending": pending,
        "advances_approved": approved,
        "advances_rejected": rejected,
        "avg_grade": round(avg_grade, 2) if avg_grade else None,
        "avg_score": round(avg_score, 2) if avg_score else None,
        "findings_by_severity": [dict(r) for r in sev_rows],
        "advances_by_status": [dict(r) for r in status_rows],
        "grades_distribution": grade_dist,
    }


# ── Usuarios ──────────────────────────────────────────────────────────────────

@app.get("/api/users", summary="Listar usuarios", tags=["Usuarios"])
def list_users(role: Optional[str] = None):
    cond = "WHERE u.role=?" if role else ""
    params = (role,) if role else ()
    rows = query(
        f"""SELECT u.id, u.name, u.email, u.role, u.program_id, u.advisor_id, u.orcid_id,
                   u.affiliation, u.expertise, u.created_at, p.name AS program, adv.name AS advisor
            FROM users u
            LEFT JOIN programs p ON p.id = u.program_id
            LEFT JOIN users adv ON adv.id = u.advisor_id
            {cond} ORDER BY u.id""",
        params,
    )
    return [dict(r) for r in rows]


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "STUDENT"
    program_id: Optional[int] = None
    advisor_id: Optional[int] = None
    orcid_id: Optional[str] = None
    affiliation: Optional[str] = None


@app.post("/api/users", summary="Crear usuario", tags=["Usuarios"])
def create_user(data: UserCreate):
    existing = query("SELECT id FROM users WHERE email=?", (data.email,))
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    uid = execute(
        """INSERT INTO users(name,email,password_hash,role,program_id,advisor_id,orcid_id,affiliation,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (data.name, data.email, hash_password(data.password), data.role,
         data.program_id, data.advisor_id, data.orcid_id, data.affiliation, now()),
    )
    rows = query("SELECT id,name,email,role,program_id,advisor_id,created_at FROM users WHERE id=?", (uid,))
    return dict(rows[0])


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    program_id: Optional[int] = None
    advisor_id: Optional[int] = None
    orcid_id: Optional[str] = None
    affiliation: Optional[str] = None
    expertise: Optional[str] = None


@app.patch("/api/users/{user_id}", summary="Actualizar usuario", tags=["Usuarios"])
def update_user(user_id: int, data: UserUpdate):
    rows = query("SELECT id FROM users WHERE id=?", (user_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    fields = data.model_dump(exclude_none=True)
    if "password" in fields:
        fields["password_hash"] = hash_password(fields.pop("password"))
    if not fields:
        raise HTTPException(status_code=400, detail="Sin campos para actualizar")
    set_clause = ", ".join(f"{k}=?" for k in fields)
    execute(f"UPDATE users SET {set_clause} WHERE id=?", list(fields.values()) + [user_id])
    result = query(
        """SELECT u.id, u.name, u.email, u.role, u.program_id, u.advisor_id,
                  p.name AS program, adv.name AS advisor
           FROM users u LEFT JOIN programs p ON p.id=u.program_id
           LEFT JOIN users adv ON adv.id=u.advisor_id WHERE u.id=?""", (user_id,)
    )
    return dict(result[0])


@app.delete("/api/users/{user_id}", summary="Eliminar usuario", tags=["Usuarios"])
def delete_user(user_id: int):
    rows = query("SELECT id FROM users WHERE id=?", (user_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    execute("DELETE FROM users WHERE id=?", (user_id,))
    return {"message": "Usuario eliminado"}


# ── Plantillas ────────────────────────────────────────────────────────────────

@app.get("/api/templates", summary="Listar plantillas", tags=["Plantillas"])
def list_templates():
    rows = query(
        """SELECT t.*, p.name AS program_name FROM templates t
           LEFT JOIN programs p ON p.id = t.program_id ORDER BY t.id"""
    )
    return [dict(r) for r in rows]


class TemplateData(BaseModel):
    id: Optional[int] = None
    program_id: int
    name: str
    version: str = "1.0"
    content: str = ""
    expected_sections: str = ""
    rubric_json: str = "{}"
    active: int = 1


@app.post("/api/templates", summary="Guardar plantilla", tags=["Plantillas"])
def save_template(data: TemplateData):
    if data.id:
        execute(
            """UPDATE templates SET program_id=?,name=?,version=?,content=?,expected_sections=?,rubric_json=?,active=?
               WHERE id=?""",
            (data.program_id, data.name, data.version, data.content,
             data.expected_sections, data.rubric_json, data.active, data.id),
        )
        tid = data.id
    else:
        tid = execute(
            """INSERT INTO templates(program_id,name,version,content,expected_sections,rubric_json,active,created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (data.program_id, data.name, data.version, data.content,
             data.expected_sections, data.rubric_json, data.active, now()),
        )
    rows = query("SELECT t.*, p.name AS program_name FROM templates t LEFT JOIN programs p ON p.id=t.program_id WHERE t.id=?", (tid,))
    return dict(rows[0])


# ── ORCID ─────────────────────────────────────────────────────────────────────

@app.get("/api/orcid/verify/{orcid_id}", summary="Verificar ORCID en registro público", tags=["Usuarios"])
async def verify_orcid(orcid_id: str):
    orcid_enabled = os.getenv("ORCID_ENABLED", "false").lower() == "true"
    if not orcid_enabled:
        return {
            "demo": True,
            "name": "Modo demo",
            "bio": None,
            "works": None,
            "message": "Activa ORCID_ENABLED=true en .env para verificación real contra el registro público.",
        }
    try:
        async with httpx.AsyncClient(timeout=10) as hc:
            r = await hc.get(
                f"https://pub.orcid.org/v3.0/{orcid_id}/person",
                headers={"Accept": "application/json"},
            )
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="ORCID no encontrado. Verifica que el ID sea correcto.")
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Respuesta inesperada del servidor ORCID: HTTP {r.status_code}")

            data = r.json()
            name_data = data.get("name") or {}
            given = (name_data.get("given-names") or {}).get("value", "")
            family = (name_data.get("family-name") or {}).get("value", "")
            bio = ((data.get("biography") or {}).get("content") or None)
            full_name = f"{given} {family}".strip()

            works_count = None
            try:
                rw = await hc.get(
                    f"https://pub.orcid.org/v3.0/{orcid_id}/works",
                    headers={"Accept": "application/json"},
                )
                if rw.status_code == 200:
                    works_count = len(rw.json().get("group", []))
            except Exception:
                pass

            return {"name": full_name, "bio": bio, "works": works_count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"No se pudo conectar al servidor ORCID: {e}")


# ── Expertise ─────────────────────────────────────────────────────────────────

class ExpertiseRequest(BaseModel):
    thesis_title: str
    expertise: str


@app.post("/api/expertise/validate", summary="Validar compatibilidad asesor–tesis con IA", tags=["Usuarios"])
def validate_expertise(data: ExpertiseRequest):
    title = (data.thesis_title or "").strip()
    expertise = (data.expertise or "").strip()
    if not title or not expertise:
        raise HTTPException(status_code=400, detail="Se requiere título de tesis y expertise del asesor.")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if api_key:
        try:
            import openai
            client_ai = openai.OpenAI(api_key=api_key)
            prompt = (
                "Eres un experto en gestión académica universitaria. "
                "Analiza si el perfil de investigación del asesor es compatible con la tesis del estudiante.\n\n"
                f"Título de la tesis: {title}\n"
                f"Expertise / líneas de investigación del asesor: {expertise}\n\n"
                "Responde SOLO con un objeto JSON con esta estructura exacta:\n"
                '{"score": <entero 0-100>, "compatible": <true|false>, '
                '"analysis": "<explicación breve en español, máx 120 palabras>", '
                '"keywords": ["<término1>", "<término2>", ...]}\n\n'
                "Donde score indica el % de afinidad temática, compatible=true si score>=50, "
                "analysis es la justificación, y keywords son los términos clave compartidos."
            )
            resp = client_ai.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
            return {
                "score":      int(result.get("score", 0)),
                "compatible": bool(result.get("compatible", False)),
                "analysis":   result.get("analysis", ""),
                "keywords":   result.get("keywords", []),
                "engine":     f"OpenAI {model}",
            }
        except Exception as exc:
            print(f"[expertise] OpenAI falló, usando motor local: {exc}")

    # Fallback: coincidencia de palabras clave normalizadas
    stop = {"de","la","el","los","las","y","o","en","del","un","una","por","para","con","que","es","al","a","su","sus","como"}
    title_words  = {w for w in title.lower().split()  if len(w) > 3 and w not in stop}
    expert_words = {w for w in expertise.lower().replace(",", " ").split() if len(w) > 3 and w not in stop}
    matched = title_words & expert_words
    score = min(100, round(len(matched) / max(1, len(title_words)) * 100 + len(matched) * 5))
    return {
        "score":      score,
        "compatible": score >= 30,
        "analysis":   (
            f"Se encontraron {len(matched)} término(s) en común: {', '.join(matched)}. "
            if matched else
            "No se detectaron términos comunes directos entre el título y el expertise. "
            "Considera activar OPENAI_API_KEY para un análisis semántico más preciso."
        ),
        "keywords": list(matched),
        "engine":   "local",
    }


# ── Copyleaks ─────────────────────────────────────────────────────────────────

@app.get("/api/copyleaks/verify", summary="Verificar conexión con Copyleaks", tags=["Usuarios"])
async def verify_copyleaks():
    api_key = os.getenv("COPYLEAKS_API_KEY", "").strip()
    email   = os.getenv("COPYLEAKS_EMAIL",   "").strip()

    if not api_key or not email:
        return {
            "configured": False,
            "message": "Configura COPYLEAKS_API_KEY y COPYLEAKS_EMAIL en .env para activar la detección externa de plagio.",
        }

    try:
        async with httpx.AsyncClient(timeout=15) as hc:
            # 1 — Autenticar
            auth = await hc.post(
                "https://id.copyleaks.com/v3/account/login/api",
                json={"email": email, "key": api_key},
            )
            if not auth.is_success:
                raise HTTPException(
                    status_code=502,
                    detail=f"Autenticación Copyleaks fallida: HTTP {auth.status_code} — verifica API key y email.",
                )
            token = auth.json().get("access_token", "")
            if not token:
                raise HTTPException(status_code=502, detail="Copyleaks no devolvió un token de acceso.")

            hdrs = {"Authorization": f"Bearer {token}"}

            # 2 — Consultar créditos disponibles
            credits_r = await hc.get("https://api.copyleaks.com/v3/account/credits", headers=hdrs)
            credits = None
            if credits_r.is_success:
                credits = credits_r.json().get("copyleaksCredits")

            return {
                "configured": True,
                "connected": True,
                "email": email,
                "credits": credits,
                "message": "Conexión exitosa con Copyleaks.",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"No se pudo conectar a Copyleaks: {e}")


# ── Email ─────────────────────────────────────────────────────────────────────

@app.post("/api/email/test", summary="Enviar correo de prueba", tags=["Sistema"])
def test_email():
    """
    Envía un correo de prueba a EMAIL_RECIPIENT y retorna el diagnóstico completo.
    Útil para verificar que SMTP funciona en producción.
    """
    result = send_test_email()
    return result


# ── Auditoría ─────────────────────────────────────────────────────────────────

@app.get("/api/audit", summary="Logs de auditoría", tags=["Auditoría"])
def get_audit(limit: int = 200):
    rows = query(
        """SELECT al.id, al.user_id, al.action,
                  al.entity AS resource, al.entity_id AS resource_id,
                  al.metadata AS details, al.created_at,
                  u.name AS user_name
           FROM audit_logs al LEFT JOIN users u ON u.id = al.user_id
           ORDER BY al.id DESC LIMIT ?""",
        (limit,),
    )
    return [dict(r) for r in rows]


# ── Generador de tesis ────────────────────────────────────────────────────────

class ThesisRequest(BaseModel):
    title:         str
    authors:       str          # comma-separated names
    advisor:       str
    research_line: str
    city:          str  = "Trujillo"
    year:          int  = 2026
    jurado:        list[str] = []
    logo_data:     Optional[str] = None   # base64 data-URL of logo image


@app.post("/api/generar_tesis", summary="Generar tesis completa (PDF + DOCX)", tags=["Tesis"])
def generar_tesis(req: ThesisRequest):
    """
    Recibe los datos de la tesis y genera automáticamente:
    - Capítulo I completo (Introducción en prosa)
    - Referencias APA V7 (mínimo 30, 80% inglés, 80% últimos 5 años, 80% indexados)
    - Árbol de problemas y árbol de objetivos
    - Declaración jurada
    - Formato exacto: Arial Narrow 12pt, márgenes 3/2.5/2.5/2.5 cm, interlineado 1.5, justificado
    """
    try:
        result = generate_thesis({
            'title':         req.title,
            'authors':       req.authors,
            'advisor':       req.advisor,
            'research_line': req.research_line,
            'city':          req.city,
            'year':          req.year,
            'jurado':        req.jurado or [],
            'logo_data':     req.logo_data,
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando tesis: {e}")


@app.get("/api/generar_tesis/download/{filename}", summary="Descargar archivo de tesis", tags=["Tesis"])
def download_thesis_file(filename: str):
    """Descarga el PDF o DOCX generado."""
    path = os.path.join("data/thesis", filename)
    if not os.path.exists(path) or ".." in filename:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    media_type = "application/pdf" if filename.endswith(".pdf") else \
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path, media_type=media_type, filename=filename)


# ── Similitud académica abierta ────────────────────────────────────────────────

@app.post("/api/similitud/check",
          summary="Verificar similitud académica contra repositorios abiertos",
          tags=["Similitud abierta"])
async def check_open_similarity(file: UploadFile = File(...)):
    """
    Recibe un PDF, DOCX o TXT y lo compara contra:
    - OpenAlex, Crossref, arXiv, CORE (si hay clave) — repositorios abiertos
    - Documentos internos del sistema (full-text TF-IDF)

    NOTA: No es equivalente a Turnitin. Solo compara contra fuentes de acceso abierto.
    """
    # Guardar archivo temporal
    suffix = os.path.splitext(file.filename or "doc.pdf")[1].lower().lstrip('.')
    if suffix not in ("pdf", "docx", "txt"):
        raise HTTPException(status_code=400, detail="Formato no permitido. Usa PDF, DOCX o TXT.")

    os.makedirs("data/uploads", exist_ok=True)
    tmp_path = f"data/uploads/sim_tmp_{int(time.time())}_{file.filename}"
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f_out:
            f_out.write(content)

        text, _ = extract_text_from_upload(tmp_path, suffix)
        if not text or len(text.strip()) < 50:
            raise HTTPException(status_code=422, detail="No se pudo extraer texto suficiente del archivo.")

        result = run_open_similarity(text, file.filename or "")
        return result
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/similitud/report",
          summary="Generar PDF del reporte de similitud académica",
          tags=["Similitud abierta"])
async def download_similarity_report(report_data: dict):
    """
    Recibe el JSON del reporte de similitud (devuelto por /api/similitud/check)
    y genera un PDF descargable.
    """
    try:
        pdf_bytes = generate_similarity_pdf(report_data)
        filename  = f"reporte_similitud_{int(time.time())}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generando reporte PDF: {exc}")


@app.post("/api/ai-detector/report",
          summary="Generar PDF del reporte del detector IA",
          tags=["Detector IA"])
async def download_ai_detection_report(report_data: dict):
    """
    Recibe el JSON del análisis de detección IA y genera un PDF con
    los párrafos sospechosos resaltados en azul.
    """
    try:
        pdf_bytes = generate_ai_detection_pdf(report_data)
        filename  = f"reporte_detector_ia_{int(time.time())}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {exc}")


# ── Detector de contenido generado por IA ─────────────────────────────────────

@app.post("/api/ai-detector/check",
          summary="Detectar posible contenido generado por IA",
          tags=["Detector IA"])
async def check_ai_content(file: UploadFile = File(...)):
    """
    Recibe un PDF, DOCX o TXT y estima la probabilidad de que el texto
    haya sido generado por inteligencia artificial.

    Usa análisis lingüístico estadístico (uniformidad oracional, entropía,
    diversidad léxica, repetición de frases, palabras de transición formal)
    y opcionalmente el modelo Hello-SimpleAI/chatgpt-detector-roberta.

    NOTA: Es una estimación técnica, no una prueba definitiva.
    """
    suffix = os.path.splitext(file.filename or "doc.pdf")[1].lower().lstrip('.')
    if suffix not in ("pdf", "docx", "txt"):
        raise HTTPException(status_code=400, detail="Formato no permitido. Usa PDF, DOCX o TXT.")

    os.makedirs("data/uploads", exist_ok=True)
    tmp_path = f"data/uploads/ai_tmp_{int(time.time())}_{file.filename}"
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f_out:
            f_out.write(content)

        text, _ = extract_text_from_upload(tmp_path, suffix)
        if not text or len(text.strip().split()) < 50:
            raise HTTPException(status_code=422, detail="No se pudo extraer texto suficiente del archivo (mínimo 50 palabras).")

        result = run_ai_detection(text, file.filename or "")
        return result
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Chatbot inteligente ───────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []   # [{"role": "user"|"assistant", "content": "..."}]


def _get_system_stats() -> dict:
    def q(sql):
        rows = query(sql)
        return rows[0][list(rows[0].keys())[0]] if rows else 0

    avg_row = query("SELECT ROUND(AVG(overall_score),1) AS n FROM ai_analyses")
    avg = avg_row[0]["n"] if avg_row and avg_row[0]["n"] is not None else "N/A"
    return {
        "total_advances":  q("SELECT COUNT(*) AS n FROM advances"),
        "total_analyses":  q("SELECT COUNT(*) AS n FROM ai_analyses"),
        "total_reviews":   q("SELECT COUNT(*) AS n FROM reviews"),
        "total_users":     q("SELECT COUNT(*) AS n FROM users"),
        "total_students":  q("SELECT COUNT(*) AS n FROM users WHERE role='STUDENT'"),
        "total_advisors":  q("SELECT COUNT(*) AS n FROM users WHERE role='ADVISOR'"),
        "total_programs":  q("SELECT COUNT(*) AS n FROM programs"),
        "total_jobs":      q("SELECT COUNT(*) AS n FROM agent_jobs"),
        "completed_jobs":  q("SELECT COUNT(*) AS n FROM agent_jobs WHERE status='completed'"),
        "failed_jobs":     q("SELECT COUNT(*) AS n FROM agent_jobs WHERE status='failed'"),
        "pending_reviews": q("SELECT COUNT(*) AS n FROM reviews WHERE status='pending'"),
        "avg_score":       avg,
    }


def _fallback_chat(message: str, stats: dict) -> str:
    m = message.lower()
    if any(w in m for w in ['cuántas','cuantas','cuántos','cuantos','total','cantidad','número','numero']):
        if any(w in m for w in ['tesis','avance','trabajo']):
            return f"Actualmente hay **{stats['total_advances']}** tesis/avances registrados en el sistema."
        if any(w in m for w in ['análisis','analisis']):
            return f"Se han realizado **{stats['total_analyses']}** análisis de IA hasta la fecha."
        if any(w in m for w in ['revisión','revision','revisiones']):
            return f"Se han completado **{stats['total_reviews']}** revisiones. Hay **{stats['pending_reviews']}** pendientes."
        if any(w in m for w in ['estudiante','alumno']):
            return f"Hay **{stats['total_students']}** estudiantes registrados."
        if any(w in m for w in ['asesor','docente','profesor']):
            return f"Hay **{stats['total_advisors']}** asesores registrados."
        if any(w in m for w in ['usuario']):
            return f"El sistema tiene **{stats['total_users']}** usuarios: {stats['total_students']} estudiantes y {stats['total_advisors']} asesores."
        if any(w in m for w in ['program','carrera','escuela']):
            return f"Existen **{stats['total_programs']}** programas académicos registrados."
        if any(w in m for w in ['trabajo','job','lote','batch']):
            return f"Se han procesado **{stats['total_jobs']}** trabajos en lote: {stats['completed_jobs']} completados y {stats['failed_jobs']} con error."
    if any(w in m for w in ['promedio','puntaje','nota','calificación','score']):
        return f"El puntaje promedio de los análisis IA es **{stats['avg_score']}** sobre 100."
    if any(w in m for w in ['qué es','que es','para qué','para que','sirve','hace','función','funcion']):
        return ("**ThesisReview AI** es una plataforma universitaria para revisión inteligente de tesis. Funciones:\n\n"
                "• **Revisión IA**: estructura, contenido, forma y originalidad\n"
                "• **Detector IA**: detecta texto generado por IA\n"
                "• **Similitud académica**: OpenAlex, Crossref, arXiv, CORE\n"
                "• **Generador de tesis**: PDF y Word con ≥50 páginas\n"
                "• **Notificaciones**: feedback por email\n"
                "• **App móvil** para estudiantes")
    if any(w in m for w in ['rol','role','acceso','permiso','administrador','coordinador']):
        return ("Roles del sistema:\n\n"
                "• **Admin**: gestión completa\n"
                "• **Coordinador**: supervisión de programas\n"
                "• **Asesor**: revisión y feedback\n"
                "• **Estudiante**: carga y seguimiento de avances")
    if any(w in m for w in ['hola','buenas','buenos','hi','hello','saludos']):
        return ("¡Hola! Soy el asistente de **ThesisReview AI**. 👋\n\n"
                "Puedo contarte estadísticas del sistema, explicar sus funciones o responder dudas sobre la plataforma. ¿En qué te ayudo?")
    if any(w in m for w in ['ayuda','help','puedo preguntar','ejemplo']):
        return ("Puedo responder preguntas como:\n\n"
                "• ¿Cuántas tesis hay registradas?\n"
                "• ¿Cuántos análisis IA se han realizado?\n"
                "• ¿Cuál es el puntaje promedio?\n"
                "• ¿Qué funciones tiene el sistema?\n"
                "• ¿Cuántos estudiantes hay?\n"
                "• ¿Cuántas revisiones están pendientes?")
    return (f"El sistema gestiona **{stats['total_advances']}** tesis, "
            f"ha realizado **{stats['total_analyses']}** análisis de IA y tiene "
            f"**{stats['total_users']}** usuarios. ¿Quieres saber algo más específico?")


@app.post("/api/chat", summary="Chatbot inteligente del sistema", tags=["Chatbot"])
def chat_endpoint(req: ChatRequest):
    """Responde preguntas sobre el sistema usando estadísticas en tiempo real y GPT (fallback keywords)."""
    stats = _get_system_stats()
    api_key = os.getenv('OPENAI_API_KEY', '')

    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            system_prompt = (
                "Eres el asistente virtual de ThesisReview AI, plataforma de revisión de avances de tesis "
                "de la Universidad Nacional de Trujillo. Responde en español, de forma amigable y concisa "
                "(máximo 120 palabras). Usa **negrita** para datos importantes.\n\n"
                f"ESTADÍSTICAS ACTUALES:\n"
                f"- Tesis registradas: {stats['total_advances']}\n"
                f"- Análisis IA: {stats['total_analyses']}\n"
                f"- Revisiones: {stats['total_reviews']} ({stats['pending_reviews']} pendientes)\n"
                f"- Usuarios: {stats['total_users']} ({stats['total_students']} estudiantes, {stats['total_advisors']} asesores)\n"
                f"- Programas: {stats['total_programs']}\n"
                f"- Trabajos en lote: {stats['completed_jobs']}/{stats['total_jobs']} completados\n"
                f"- Puntaje IA promedio: {stats['avg_score']}/100\n\n"
                "FUNCIONES: revisión IA, detector IA, similitud académica, generador de tesis PDF+Word, email, app móvil.\n"
                "Solo responde sobre ThesisReview AI."
            )
            messages = [{"role": "system", "content": system_prompt}]
            for h in req.history[-6:]:
                if h.get("role") in ("user","assistant") and h.get("content"):
                    messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": req.message})
            resp = client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),
                messages=messages,
                temperature=0.5,
                max_tokens=300,
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[chat] OpenAI error: {e}")
            answer = _fallback_chat(req.message, stats)
    else:
        answer = _fallback_chat(req.message, stats)

    return {"answer": answer, "stats": stats}

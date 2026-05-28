
import os
import json
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from .database import query


# ── Configuración SMTP desde entorno ─────────────────────────────────────────
SMTP_HOST       = os.getenv("SMTP_HOST",       "smtp.gmail.com")
SMTP_PORT       = int(os.getenv("SMTP_PORT",   "587"))
EMAIL_SENDER    = os.getenv("EMAIL_SENDER",    "")
EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD",  "")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "christiannoriegaoliva2020@gmail.com")
RESEND_KEY      = os.getenv("RESEND_API_KEY",  "")

# Log de configuración al cargar el módulo
print("[email_service] == Configuracion cargada ==")
print(f"[email_service]   SMTP_HOST      : {SMTP_HOST}")
print(f"[email_service]   SMTP_PORT      : {SMTP_PORT}")
print(f"[email_service]   EMAIL_SENDER   : {('OK ' + EMAIL_SENDER) if EMAIL_SENDER else 'NO CONFIGURADO'}")
print(f"[email_service]   EMAIL_PASSWORD : {('OK (' + str(len(EMAIL_PASSWORD)) + ' chars)') if EMAIL_PASSWORD else 'NO CONFIGURADA'}")
print(f"[email_service]   EMAIL_RECIPIENT: {EMAIL_RECIPIENT}")
print(f"[email_service]   RESEND_KEY     : {'OK configurada' if RESEND_KEY else 'no configurada (opcional)'}")
print("[email_service] ===============================")


def _send_via_smtp(subject: str, html_body: str, recipients: list[str],
                   attachments: list[str] | None = None) -> tuple[bool, str]:
    """Intenta enviar por SMTP. Retorna (éxito, mensaje)."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return False, "EMAIL_SENDER o EMAIL_PASSWORD no configurados en las variables de entorno."

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    for path in (attachments or []):
        if os.path.exists(path):
            with open(path, "rb") as fh:
                part = MIMEApplication(fh.read(), Name=os.path.basename(path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
            msg.attach(part)

    try:
        print(f"[email_service] Conectando a {SMTP_HOST}:{SMTP_PORT} ...")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            print(f"[email_service] STARTTLS ...")
            server.starttls()
            server.ehlo()
            print(f"[email_service] Login como {EMAIL_SENDER} ...")
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
        print(f"[email_service] OK Correo enviado a {recipients}")
        return True, "OK"
    except smtplib.SMTPAuthenticationError as exc:
        msg_err = f"Autenticacion fallida: {exc} — verifica EMAIL_SENDER y EMAIL_PASSWORD (usa contrasena de app, no la contrasena normal)"
        print(f"[email_service] FALLO: {msg_err}")
        return False, msg_err
    except smtplib.SMTPConnectError as exc:
        msg_err = f"No se pudo conectar a {SMTP_HOST}:{SMTP_PORT} — Render puede estar bloqueando SMTP: {exc}"
        print(f"[email_service] FALLO: {msg_err}")
        return False, msg_err
    except Exception as exc:
        msg_err = f"{type(exc).__name__}: {exc}"
        print(f"[email_service] FALLO SMTP: {msg_err}")
        print(traceback.format_exc())
        return False, msg_err


def _send_via_resend(subject: str, html_body: str, recipients: list[str]) -> tuple[bool, str]:
    """Fallback: envía via Resend HTTP API si RESEND_API_KEY está configurado."""
    if not RESEND_KEY:
        return False, "RESEND_API_KEY no configurada."
    try:
        import httpx
        payload = {
            "from": EMAIL_SENDER or "ThesisReview AI <noreply@resend.dev>",
            "to": recipients,
            "subject": subject,
            "html": html_body,
        }
        resp = httpx.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={
                "Authorization": f"Bearer {RESEND_KEY}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )
        if resp.status_code in (200, 201):
            print(f"[email_service] OK Correo enviado via Resend a {recipients}")
            return True, "OK (Resend)"
        else:
            msg_err = f"Resend HTTP {resp.status_code}: {resp.text[:300]}"
            print(f"[email_service] FALLO Resend: {msg_err}")
            return False, msg_err
    except Exception as exc:
        msg_err = f"Resend error: {exc}"
        print(f"[email_service] FALLO Resend: {msg_err}")
        return False, msg_err


def _send(subject: str, html_body: str, recipients: list[str],
          attachments: list[str] | None = None) -> bool:
    """Envía correo: intenta SMTP primero, luego Resend como fallback HTTP."""
    print(f"[email_service] Enviando '{subject[:60]}' -> {recipients}")
    ok, detail = _send_via_smtp(subject, html_body, recipients, attachments)
    if ok:
        return True
    print(f"[email_service] SMTP fallo ({detail}). Intentando Resend ...")
    ok2, detail2 = _send_via_resend(subject, html_body, recipients)
    if not ok2:
        print(f"[email_service] Resend tambien fallo ({detail2}). Correo no enviado.")
    return ok2


def send_test_email() -> dict:
    """Envía un correo de prueba simple. Retorna dict con resultado y detalles."""
    subject = "[ThesisReview AI] Prueba de configuración de correo"
    html    = f"""<div style="font-family:Arial,sans-serif;padding:20px">
        <h2 style="color:#1e3a5f">✓ Prueba de correo exitosa</h2>
        <p>Este correo confirma que la configuración SMTP de ThesisReview AI está funcionando correctamente.</p>
        <table style="border-collapse:collapse;font-size:13px;margin-top:12px">
          <tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold">SMTP_HOST</td>
              <td style="padding:4px 10px">{SMTP_HOST}</td></tr>
          <tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold">SMTP_PORT</td>
              <td style="padding:4px 10px">{SMTP_PORT}</td></tr>
          <tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold">EMAIL_SENDER</td>
              <td style="padding:4px 10px">{EMAIL_SENDER}</td></tr>
          <tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold">Enviado a</td>
              <td style="padding:4px 10px">{EMAIL_RECIPIENT}</td></tr>
          <tr><td style="padding:4px 10px;background:#f3f4f6;font-weight:bold">Fecha</td>
              <td style="padding:4px 10px">{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</td></tr>
        </table>
    </div>"""

    smtp_ok, smtp_detail = _send_via_smtp(subject, html, [EMAIL_RECIPIENT])
    result = {
        "smtp_host":       SMTP_HOST,
        "smtp_port":       SMTP_PORT,
        "email_sender":    EMAIL_SENDER or "(no configurado)",
        "email_password":  f"{'OK ' + str(len(EMAIL_PASSWORD)) + ' chars' if EMAIL_PASSWORD else 'no configurada'}",
        "email_recipient": EMAIL_RECIPIENT,
        "smtp_result":     "OK" if smtp_ok else f"FALLO: {smtp_detail}",
        "sent_via":        None,
    }
    if smtp_ok:
        result["sent_via"] = "smtp"
        return result

    resend_ok, resend_detail = _send_via_resend(subject, html, [EMAIL_RECIPIENT])
    result["resend_key"]    = "OK configurada" if RESEND_KEY else "no configurada"
    result["resend_result"] = "OK" if resend_ok else f"FALLO: {resend_detail}"
    if resend_ok:
        result["sent_via"] = "resend"
    else:
        result["sent_via"] = None
        result["suggestion"] = (
            "Ambos metodos fallaron. "
            "Render bloquea SMTP saliente (puerto 587). "
            "Solución: crea una cuenta en resend.com, obtén tu API key "
            "y agrega RESEND_API_KEY en Render -> Environment."
        )
    return result


# ── Paleta de colores y helpers HTML ──────────────────────────────────────────
_SEVERITY_COLOR = {
    "Crítico": "#dc3545",
    "Mayor":   "#fd7e14",
    "Menor":   "#ffc107",
    "Info":    "#17a2b8",
}

def _severity_badge(severity: str) -> str:
    color = _SEVERITY_COLOR.get(severity, "#6c757d")
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:11px;font-weight:bold">{severity}</span>'
    )

def _score_bar(label: str, value: float, color: str = "#2c3e50") -> str:
    pct = min(max(value, 0), 100)
    return f"""
    <tr>
      <td style="padding:4px 8px;font-size:13px;width:160px">{label}</td>
      <td style="padding:4px 8px">
        <div style="background:#e9ecef;border-radius:4px;height:16px;width:100%">
          <div style="background:{color};height:16px;border-radius:4px;width:{pct:.0f}%"></div>
        </div>
      </td>
      <td style="padding:4px 8px;font-size:13px;font-weight:bold;width:60px">{pct:.1f}%</td>
    </tr>"""

def _grade_color(grade: float) -> str:
    if grade >= 17: return "#28a745"
    if grade >= 14: return "#17a2b8"
    if grade >= 11: return "#ffc107"
    return "#dc3545"


# ── Email individual ───────────────────────────────────────────────────────────
def send_review_email(advance_id: int, pdf_path: str | None = None) -> bool:
    """Envía el reporte detallado de un avance al correo configurado."""

    # 1. Datos principales
    rows = query(
        """SELECT a.*, u.name student, u.email student_email,
                  p.name program, adv.name advisor, adv.email advisor_email
           FROM advances a
           JOIN users u ON u.id = a.student_id
           JOIN programs p ON p.id = a.program_id
           LEFT JOIN users adv ON adv.id = u.advisor_id
           WHERE a.id=?""",
        (advance_id,)
    )
    if not rows:
        return False
    adv = rows[0]

    ana_rows = query("SELECT * FROM ai_analyses WHERE advance_id=?", (advance_id,))
    ana = ana_rows[0] if ana_rows else None

    findings = []
    if ana:
        findings = query(
            "SELECT * FROM findings WHERE analysis_id=? ORDER BY "
            "CASE severity WHEN 'Crítico' THEN 1 WHEN 'Mayor' THEN 2 WHEN 'Menor' THEN 3 ELSE 4 END, id",
            (ana["id"],)
        )

    sims = query(
        """SELECT pr.similarity, pr.status, a2.title compared_title
           FROM plagiarism_results pr
           LEFT JOIN advances a2 ON a2.id = pr.compared_advance_id
           WHERE pr.advance_id=?""",
        (advance_id,)
    )

    cites = query(
        "SELECT raw_reference, status, suggestion FROM citations WHERE advance_id=?",
        (advance_id,)
    )

    sec_comp = []
    if ana:
        try:
            sec_comp = json.loads(ana.get("section_comparison") or "[]")
        except Exception:
            pass

    # 2. Construir HTML
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    grade    = ana["grade"]    if ana else 0
    overall  = ana["overall_score"] if ana else 0
    gc       = _grade_color(grade) if ana else "#6c757d"

    # -- Métricas de puntaje --
    scores_html = ""
    if ana:
        scores_html = f"""
        <table style="width:100%;border-collapse:collapse">
          {_score_bar("Estructura",     ana["structure_score"],    "#2196F3")}
          {_score_bar("Contenido",      ana["content_score"],      "#4CAF50")}
          {_score_bar("Forma",          ana["form_score"],         "#9C27B0")}
          {_score_bar("Calidad interna",ana["originality_score"],  "#FF9800")}
          {_score_bar("Cumplimiento IA",overall,                   "#1e3a5f")}
        </table>"""

    # -- Hallazgos --
    findings_html = ""
    if findings:
        items = ""
        for f in findings[:25]:
            badge = _severity_badge(f["severity"])
            items += f"""
            <div style="border:1px solid #dee2e6;border-radius:6px;padding:12px;margin-bottom:10px">
              <p style="margin:0 0 4px">{badge}
                &nbsp;<strong>{f['type']}</strong>
                &nbsp;·&nbsp;<em>{f['section_ref']}</em>
              </p>
              <p style="margin:4px 0;font-size:13px">{f['description']}</p>
              <p style="margin:4px 0;font-size:12px;color:#555">
                <strong>Corrección:</strong> {f['correction_steps']}
              </p>
            </div>"""
        findings_html = f"<h3 style='color:#2c3e50'>Hallazgos ({len(findings)})</h3>{items}"

    # -- Similitud --
    sims_html = ""
    if sims:
        rows_sim = "".join(
            f"<tr><td style='padding:4px 8px'>{s.get('compared_title','—')}</td>"
            f"<td style='padding:4px 8px;text-align:center'>{s['similarity']:.1f}%</td>"
            f"<td style='padding:4px 8px;text-align:center'>{s['status']}</td></tr>"
            for s in sims
        )
        sims_html = f"""
        <h3 style='color:#2c3e50'>Similitud interna</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <tr style="background:#2c3e50;color:#fff">
            <th style="padding:6px 8px;text-align:left">Avance comparado</th>
            <th style="padding:6px 8px">Similitud</th>
            <th style="padding:6px 8px">Estado</th>
          </tr>{rows_sim}
        </table>"""

    # -- Citas --
    cites_html = ""
    if cites:
        rows_cit = "".join(
            f"<tr><td style='padding:4px 8px;font-size:12px'>{c['raw_reference'][:80]}...</td>"
            f"<td style='padding:4px 8px;text-align:center'>{c['status']}</td>"
            f"<td style='padding:4px 8px;font-size:12px'>{c.get('suggestion','')}</td></tr>"
            for c in cites[:20]
        )
        cites_html = f"""
        <h3 style='color:#2c3e50'>Validación de citas ({len(cites)})</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <tr style="background:#2c3e50;color:#fff">
            <th style="padding:6px 8px;text-align:left">Referencia</th>
            <th style="padding:6px 8px">Estado</th>
            <th style="padding:6px 8px;text-align:left">Sugerencia</th>
          </tr>{rows_cit}
        </table>"""

    # -- Comparación seccional --
    sec_html = ""
    if sec_comp:
        present  = sum(1 for s in sec_comp if s.get("present"))
        total    = len(sec_comp)
        sec_rows = ""
        for s in sec_comp:
            if s.get("present") and s.get("optional"):
                bg, lbl = "#fff3cd", "Opcional"
            elif s.get("present"):
                bg, lbl = "#d4edda", "✓ Presente"
            else:
                bg, lbl = "#f8d7da", "✗ Ausente"
            sec_rows += (
                f"<tr style='background:{bg}'>"
                f"<td style='padding:4px 8px'>{s.get('section','-')}</td>"
                f"<td style='padding:4px 8px;text-align:center'>{lbl}</td></tr>"
            )
        sec_html = f"""
        <h3 style='color:#2c3e50'>Comparación con esquema institucional</h3>
        <p style='font-size:13px'>Secciones encontradas: <strong>{present} de {total}</strong>
          ({round(present/total*100) if total else 0}% de cumplimiento estructural)</p>
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <tr style="background:#1e3a5f;color:#fff">
            <th style="padding:6px 8px;text-align:left">Sección requerida</th>
            <th style="padding:6px 8px">Estado</th>
          </tr>{sec_rows}
        </table>"""

    exec_summary = ana["executive_summary"] if ana else "Sin análisis disponible."

    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f9;margin:0;padding:0">
<div style="max-width:680px;margin:30px auto;background:#fff;border-radius:8px;
            box-shadow:0 2px 8px rgba(0,0,0,.12);overflow:hidden">

  <!-- Cabecera -->
  <div style="background:#1e3a5f;padding:24px 28px">
    <h1 style="margin:0;color:#fff;font-size:22px">ThesisReview AI</h1>
    <p style="margin:6px 0 0;color:#a8c4e0;font-size:13px">
      Reporte de revisión de avance de tesis · {now_str}
    </p>
  </div>

  <div style="padding:24px 28px">

    <!-- Nota destacada -->
    <div style="text-align:center;padding:20px;background:#f8f9fa;border-radius:8px;margin-bottom:24px">
      <p style="margin:0;font-size:13px;color:#666">Nota estimada IA</p>
      <p style="margin:4px 0 0;font-size:48px;font-weight:bold;color:{gc}">{grade:.1f}<span style="font-size:22px;color:#999">/20</span></p>
      <p style="margin:4px 0 0;font-size:14px;color:#555">Cumplimiento general: <strong>{overall:.1f}%</strong></p>
    </div>

    <!-- Info del avance -->
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px">
      <tr><td style="padding:5px 8px;background:#ecf0f1;font-weight:bold;width:35%">Estudiante</td>
          <td style="padding:5px 8px">{adv['student']}</td></tr>
      <tr><td style="padding:5px 8px;background:#ecf0f1;font-weight:bold">Programa</td>
          <td style="padding:5px 8px">{adv['program']}</td></tr>
      <tr><td style="padding:5px 8px;background:#ecf0f1;font-weight:bold">Título</td>
          <td style="padding:5px 8px">{adv['title']}</td></tr>
      <tr><td style="padding:5px 8px;background:#ecf0f1;font-weight:bold">Tipo de avance</td>
          <td style="padding:5px 8px">{adv['advance_type']}</td></tr>
      <tr><td style="padding:5px 8px;background:#ecf0f1;font-weight:bold">Versión</td>
          <td style="padding:5px 8px">v{adv.get('version') or 1}</td></tr>
      <tr><td style="padding:5px 8px;background:#ecf0f1;font-weight:bold">Estado</td>
          <td style="padding:5px 8px">{adv['status']}</td></tr>
      <tr><td style="padding:5px 8px;background:#ecf0f1;font-weight:bold">Asesor</td>
          <td style="padding:5px 8px">{adv.get('advisor') or '—'}</td></tr>
    </table>

    <!-- Barras de puntaje -->
    {"<h3 style='color:#2c3e50'>Puntajes por dimensión</h3>" + scores_html if scores_html else ""}

    <!-- Resumen ejecutivo -->
    <h3 style="color:#2c3e50">Resumen ejecutivo IA</h3>
    <div style="background:#f8f9fa;border-left:4px solid #1e3a5f;padding:14px 16px;
                font-size:13px;line-height:1.6;border-radius:0 4px 4px 0">
      {exec_summary}
    </div>

    {sec_html}
    {findings_html}
    {sims_html}
    {cites_html}

  </div>

  <!-- Pie -->
  <div style="background:#f4f6f9;padding:14px 28px;font-size:11px;color:#999;text-align:center">
    Este reporte fue generado automáticamente por <strong>ThesisReview AI</strong>.
    El PDF completo se adjunta a este correo si está disponible.
  </div>
</div>
</body>
</html>"""

    recipients = [EMAIL_RECIPIENT]

    subject = f"[ThesisReview AI] Revision — {adv['student']} · {adv['advance_type']} · {now_str}"
    attachments = [pdf_path] if pdf_path and os.path.exists(pdf_path) else []

    return _send(subject, html, recipients, attachments)


# ── Email resumen de lotes ─────────────────────────────────────────────────────
def send_batch_review_email(advance_ids: list[int]) -> bool:
    """Envía un resumen ejecutivo con todos los avances procesados en el lote."""
    if not advance_ids:
        return False

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    rows_data = []
    for aid in advance_ids:
        rows = query(
            """SELECT a.id, a.title, a.advance_type, a.status, a.version,
                      u.name student, p.name program,
                      ai.overall_score, ai.grade,
                      ai.structure_score, ai.content_score, ai.form_score,
                      (SELECT COUNT(*) FROM findings f2
                         JOIN ai_analyses aa2 ON aa2.id=f2.analysis_id
                         WHERE aa2.advance_id=a.id AND f2.severity='Crítico') AS criticos,
                      (SELECT COUNT(*) FROM findings f3
                         JOIN ai_analyses aa3 ON aa3.id=f3.analysis_id
                         WHERE aa3.advance_id=a.id AND f3.severity='Mayor') AS mayores
               FROM advances a
               JOIN users u ON u.id=a.student_id
               JOIN programs p ON p.id=a.program_id
               LEFT JOIN ai_analyses ai ON ai.advance_id=a.id
               WHERE a.id=?""",
            (aid,)
        )
        if rows:
            rows_data.append(dict(rows[0]))

    if not rows_data:
        return False

    grades = [r["grade"] for r in rows_data if r.get("grade") is not None]
    avg_grade = sum(grades) / len(grades) if grades else 0
    approved = sum(1 for r in rows_data if r.get("status") == "Aprobado")

    # Tabla resumen
    table_rows = ""
    for d in sorted(rows_data, key=lambda x: x.get("grade") or 0, reverse=True):
        grade    = d.get("grade")
        overall  = d.get("overall_score")
        gc       = _grade_color(grade) if grade is not None else "#6c757d"
        grade_str   = f'<strong style="color:{gc}">{grade:.1f}/20</strong>' if grade is not None else "—"
        overall_str = f"{overall:.0f}%" if overall is not None else "—"
        criticos = d.get("criticos", 0) or 0
        mayores  = d.get("mayores",  0) or 0
        crit_badge = (
            f'<span style="color:#dc3545;font-weight:bold">{criticos} crítico(s)</span>'
            if criticos > 0 else ""
        )
        mayor_badge = (
            f'<span style="color:#fd7e14">{mayores} mayor(es)</span>'
            if mayores > 0 else ""
        )
        hallazgos_cell = " &nbsp; ".join(filter(None, [crit_badge, mayor_badge])) or "—"
        table_rows += f"""
        <tr style="border-bottom:1px solid #dee2e6">
          <td style="padding:8px 10px">{d['student']}</td>
          <td style="padding:8px 10px;font-size:12px;color:#555">{d.get('title','—')[:40]}</td>
          <td style="padding:8px 10px;font-size:12px">{d['advance_type']}</td>
          <td style="padding:8px 10px;text-align:center">{grade_str}</td>
          <td style="padding:8px 10px;text-align:center">{overall_str}</td>
          <td style="padding:8px 10px">{hallazgos_cell}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f9;margin:0;padding:0">
<div style="max-width:740px;margin:30px auto;background:#fff;border-radius:8px;
            box-shadow:0 2px 8px rgba(0,0,0,.12);overflow:hidden">

  <div style="background:#1e3a5f;padding:24px 28px">
    <h1 style="margin:0;color:#fff;font-size:22px">ThesisReview AI — Reporte por lotes</h1>
    <p style="margin:6px 0 0;color:#a8c4e0;font-size:13px">
      Procesamiento completado · {now_str}
    </p>
  </div>

  <div style="padding:24px 28px">

    <!-- Indicadores globales -->
    <div style="display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap">
      <div style="flex:1;min-width:130px;background:#e8f5e9;border-radius:8px;padding:14px;text-align:center">
        <p style="margin:0;font-size:12px;color:#555">Avances procesados</p>
        <p style="margin:4px 0 0;font-size:32px;font-weight:bold;color:#2c3e50">{len(rows_data)}</p>
      </div>
      <div style="flex:1;min-width:130px;background:#e3f2fd;border-radius:8px;padding:14px;text-align:center">
        <p style="margin:0;font-size:12px;color:#555">Nota promedio IA</p>
        <p style="margin:4px 0 0;font-size:32px;font-weight:bold;color:{_grade_color(avg_grade)}">{avg_grade:.1f}<span style="font-size:14px;color:#999">/20</span></p>
      </div>
      <div style="flex:1;min-width:130px;background:#fff3e0;border-radius:8px;padding:14px;text-align:center">
        <p style="margin:0;font-size:12px;color:#555">En revisión humana</p>
        <p style="margin:4px 0 0;font-size:32px;font-weight:bold;color:#ff9800">{len(rows_data) - approved}</p>
      </div>
    </div>

    <h3 style="color:#2c3e50;margin-top:0">Detalle por avance</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tr style="background:#2c3e50;color:#fff">
        <th style="padding:8px 10px;text-align:left">Estudiante</th>
        <th style="padding:8px 10px;text-align:left">Título</th>
        <th style="padding:8px 10px;text-align:left">Tipo</th>
        <th style="padding:8px 10px;text-align:center">Nota</th>
        <th style="padding:8px 10px;text-align:center">Cumpl.</th>
        <th style="padding:8px 10px;text-align:left">Hallazgos</th>
      </tr>
      {table_rows}
    </table>

    <p style="margin-top:20px;font-size:12px;color:#777">
      Los reportes individuales (PDF) están disponibles en la plataforma ThesisReview AI
      o pueden descargarse desde la sección <em>Revisión humana</em>.
    </p>
  </div>

  <div style="background:#f4f6f9;padding:14px 28px;font-size:11px;color:#999;text-align:center">
    Reporte automático generado por <strong>ThesisReview AI</strong> · {now_str}
  </div>
</div>
</body>
</html>"""

    subject = f"[ThesisReview AI] Reporte lote - {len(rows_data)} avances procesados - {now_str}"
    return _send(subject, html, [EMAIL_RECIPIENT])

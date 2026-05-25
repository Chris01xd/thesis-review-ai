
from dotenv import load_dotenv
load_dotenv()                          # Carga .env antes que cualquier módulo

import streamlit as st
import pandas as pd
import plotly.express as px
import os, json, time
from datetime import datetime
from modules.database import init_db, query, execute, log, check_password, now
from modules.document_processing import extract_text_from_upload
from modules.ai_engine import local_agentic_analysis, agent_plan_for_document
from modules.plagiarism import run_similarity_check
from modules.citations import validate_citations
from modules.reports import generate_review_pdf, generate_comparative_pdf, generate_management_pdf

st.set_page_config(page_title="ThesisReview AI", page_icon="🎓", layout="wide")
init_db()

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "20"))

# ── Mapas de estado para la vista "Avances de Tesis" ─────────────────────────
STATUS_DISPLAY = {
    "Pendiente":               ("Pendiente",    "#9e9e9e"),
    "Análisis IA en proceso":  ("IA Procesando","#ff9800"),
    "En revisión humana":      ("IA Completo",  "#2196f3"),
    "Observado":               ("Observado",    "#ff5722"),
    "Aprobado":                ("Aprobado",     "#4caf50"),
    "Rechazado":               ("Rechazado",    "#f44336"),
}

STATUS_FILTER_MAP = [
    ("Todos",         []),
    ("Pendiente",     ["Pendiente"]),
    ("IA Procesando", ["Análisis IA en proceso"]),
    ("IA Completo",   ["En revisión humana"]),
    ("En Revisión",   ["En revisión humana"]),
    ("Observado",     ["Observado"]),
    ("Aprobado",      ["Aprobado"]),
    ("Rechazado",     ["Rechazado"]),
]

SEVERITY_COLORS = {
    "Crítico":     "#f44336",
    "Mayor":       "#ff9800",
    "Advertencia": "#ffc107",
    "Menor":       "#2196f3",
    "Sugerencia":  "#78909c",
}

# ── Páginas habilitadas por rol ───────────────────────────────────────────────
ROLE_PAGES = {
    "ADMIN": [
        "Dashboard", "Avances de Tesis", "Cargar avance", "Revisión IA",
        "Revisión humana", "Revisión por lotes", "Plantillas", "Usuarios y ORCID",
        "Estadísticas", "Reportes", "App móvil", "Auditoría", "Configuración"
    ],
    "COORDINATOR": [
        "Dashboard", "Avances de Tesis", "Cargar avance", "Revisión IA",
        "Revisión humana", "Revisión por lotes", "Plantillas", "Usuarios y ORCID",
        "Estadísticas", "Reportes", "App móvil", "Auditoría"
    ],
    "ADVISOR": [
        "Dashboard", "Avances de Tesis", "Cargar avance", "Revisión IA",
        "Revisión humana", "Revisión por lotes", "Estadísticas", "Reportes", "App móvil"
    ],
    "STUDENT": [
        "Dashboard", "Avances de Tesis", "Revisión IA", "App móvil"
    ],
}

def rerun():
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Design System Global CSS
# ─────────────────────────────────────────────────────────────────────────────
def inject_global_css():
    st.markdown("""
    <style>
    /* ══════════════════════════════════════════════════
       ThesisReview AI — Design System v2
    ══════════════════════════════════════════════════ */

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ── App shell ───────────────────────────────────── */
    .stApp {
        background: #f0f4f9 !important;
        font-family: 'Inter', 'Segoe UI', sans-serif !important;
    }
    .main .block-container {
        padding: 1.8rem 2.4rem 3rem !important;
        max-width: 1240px !important;
    }

    /* ── Sidebar ─────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(175deg, #0d1b4b 0%, #1a237e 45%, #1565c0 100%) !important;
        box-shadow: 4px 0 24px rgba(0,0,0,0.18) !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div { color: rgba(255,255,255,0.92) !important; }
    [data-testid="stSidebar"] .stRadio > div { gap: 3px !important; }
    [data-testid="stSidebar"] .stRadio label {
        background: rgba(255,255,255,0.07) !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        margin: 0 !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        border: 1px solid transparent !important;
        transition: all 0.18s ease !important;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.16) !important;
        border-color: rgba(255,255,255,0.22) !important;
    }

    /* ── Headings ────────────────────────────────────── */
    h1 {
        color: #1a237e !important;
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 0.2rem !important;
    }
    h2 {
        color: #283593 !important;
        font-size: 1.25rem !important;
        font-weight: 600 !important;
    }
    h3 {
        color: #1565c0 !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }

    /* ── Buttons ─────────────────────────────────────── */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 0.48rem 1.15rem !important;
        transition: all 0.2s ease !important;
        border: none !important;
        letter-spacing: 0.15px !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%) !important;
        color: white !important;
        box-shadow: 0 3px 12px rgba(26,115,232,0.38) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1558c0 0%, #0d47a1 100%) !important;
        box-shadow: 0 5px 18px rgba(26,115,232,0.52) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        background: white !important;
        color: #1a73e8 !important;
        border: 1.5px solid #1a73e8 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.07) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #e8f0fe !important;
        box-shadow: 0 3px 12px rgba(26,115,232,0.22) !important;
    }

    /* ── Metric cards ────────────────────────────────── */
    [data-testid="stMetric"] {
        background: white !important;
        border-radius: 14px !important;
        padding: 18px 22px !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.07) !important;
        border-left: 4px solid #1a73e8 !important;
    }
    [data-testid="stMetricValue"] {
        color: #1a237e !important;
        font-size: 1.9rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #5f6368 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.7px !important;
        font-weight: 600 !important;
    }

    /* ── Tabs ────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: white !important;
        border-radius: 12px !important;
        padding: 5px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        gap: 4px !important;
        border: 1px solid #e0e5f0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9px !important;
        padding: 9px 22px !important;
        font-weight: 500 !important;
        color: #5f6368 !important;
        font-size: 0.875rem !important;
        transition: all 0.18s !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1a73e8, #1557b0) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(26,115,232,0.38) !important;
    }

    /* ── Expanders ───────────────────────────────────── */
    [data-testid="stExpander"] {
        border: 1.5px solid #e0e5f0 !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        background: white !important;
        margin-bottom: 8px !important;
        box-shadow: 0 1px 5px rgba(0,0,0,0.05) !important;
        transition: box-shadow 0.2s !important;
    }
    [data-testid="stExpander"]:hover {
        box-shadow: 0 3px 14px rgba(26,115,232,0.12) !important;
    }
    [data-testid="stExpander"] summary {
        background: white !important;
        padding: 13px 18px !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stExpander"] summary:hover { background: #f5f8ff !important; }

    /* ── Input / Selects ─────────────────────────────── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        border-radius: 10px !important;
        border: 1.5px solid #d0d7e3 !important;
        background: white !important;
        padding: 10px 14px !important;
        font-size: 0.9rem !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #1a73e8 !important;
        box-shadow: 0 0 0 3px rgba(26,115,232,0.13) !important;
        outline: none !important;
    }
    .stSelectbox [data-baseweb="select"] > div {
        border-radius: 10px !important;
        border: 1.5px solid #d0d7e3 !important;
        background: white !important;
    }

    /* ── Progress bar ────────────────────────────────── */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #1a73e8 0%, #43a047 100%) !important;
        border-radius: 99px !important;
    }
    .stProgress > div > div > div {
        border-radius: 99px !important;
        height: 10px !important;
        background: #dce9fb !important;
    }

    /* ── DataFrames ──────────────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.07) !important;
        border: 1px solid #e0e5f0 !important;
    }

    /* ── Container border=True (cards) ──────────────── */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1.5px solid #e0e8f5 !important;
        box-shadow: 0 2px 14px rgba(0,0,0,0.06) !important;
        background: white !important;
        padding: 4px 8px !important;
        transition: box-shadow 0.22s ease, border-color 0.22s ease !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 6px 26px rgba(26,115,232,0.14) !important;
        border-color: #bbdefb !important;
    }

    /* ── Forms ───────────────────────────────────────── */
    [data-testid="stForm"] {
        background: white !important;
        border-radius: 14px !important;
        border: 1.5px solid #e0e5f0 !important;
        padding: 22px !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05) !important;
    }

    /* ── Alerts ──────────────────────────────────────── */
    .stAlert { border-radius: 10px !important; }

    /* ── Dividers ────────────────────────────────────── */
    hr { border-color: #e0e8f5 !important; margin: 1.2rem 0 !important; }

    /* ── Hide Streamlit chrome ───────────────────────── */
    #MainMenu    { visibility: hidden; }
    footer       { visibility: hidden; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stToolbar"]    { display: none !important; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Auth — Login page
# ─────────────────────────────────────────────────────────────────────────────
def auth():
    inject_global_css()
    if "user" not in st.session_state:
        st.session_state.user = None
    if st.session_state.user:
        return True

    # Login-only background override
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0a1628 0%, #1a237e 45%, #1565c0 100%) !important;
        min-height: 100vh;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.25, 1])

    with col:
        # Brand card
        st.markdown("""
        <div style="text-align:center;padding:34px 28px 26px;
                    background:rgba(255,255,255,0.07);
                    backdrop-filter:blur(14px);
                    border:1px solid rgba(255,255,255,0.18);
                    border-radius:20px;margin-bottom:14px">
            <div style="font-size:3rem;line-height:1;margin-bottom:10px">🎓</div>
            <div style="font-size:1.7rem;font-weight:700;color:white;
                        letter-spacing:-0.5px;margin-bottom:6px">
                ThesisReview AI
            </div>
            <div style="font-size:0.85rem;color:rgba(255,255,255,0.62)">
                Sistema inteligente de revisión de avances de tesis
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Form card header
        st.markdown("""
        <div style="background:white;border-radius:18px 18px 0 0;
                    padding:22px 28px 4px;
                    box-shadow:0 16px 48px rgba(0,0,0,0.38)">
            <div style="font-size:1rem;font-weight:600;color:#1a237e;
                        text-align:center;margin-bottom:4px">
                Iniciar sesión
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Form fields (native widgets — no nesting inside HTML)
        email    = st.text_input("Correo institucional", value="admin@tesis.edu",
                                 placeholder="usuario@tesis.edu")
        password = st.text_input("Contraseña", type="password", value="123456")

        if st.button("Ingresar al sistema", use_container_width=True, type="primary"):
            rows = query("SELECT * FROM users WHERE email=?", (email,))
            if rows and check_password(password, rows[0]["password_hash"]):
                st.session_state.user = dict(rows[0])
                log(rows[0]["id"], "LOGIN", "users", rows[0]["id"])
                rerun()
            else:
                st.error("Credenciales incorrectas. Verifica tu correo y contraseña.")

        st.markdown("<br>", unsafe_allow_html=True)

        # Demo credentials note
        st.markdown("""
        <div style="text-align:center;padding:14px 18px;margin-top:6px;
                    background:rgba(255,255,255,0.07);border-radius:12px;
                    border:1px solid rgba(255,255,255,0.14)">
            <p style="color:rgba(255,255,255,0.58);font-size:0.78rem;margin:0;line-height:1.8">
                <strong style="color:rgba(255,255,255,0.88)">Usuarios demo</strong><br>
                admin · coordinador · asesor · estudiante <em>@tesis.edu</em><br>
                Contraseña:
                <code style="background:rgba(0,0,0,0.32);color:#81d4fa;
                             padding:1px 8px;border-radius:4px">123456</code>
            </p>
        </div>
        """, unsafe_allow_html=True)

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
def sidebar():
    u = st.session_state.user
    role_meta = {
        "ADMIN":       ("Administrador", "#ef5350"),
        "COORDINATOR": ("Coordinador",   "#fb8c00"),
        "ADVISOR":     ("Asesor",        "#43a047"),
        "STUDENT":     ("Estudiante",    "#1e88e5"),
    }
    role_label, role_color = role_meta.get(u["role"], (u["role"], "#9e9e9e"))

    # Brand + user card
    st.sidebar.markdown(f"""
    <div style="padding:22px 4px 14px;text-align:center">
        <div style="font-size:2.3rem;margin-bottom:6px">🎓</div>
        <div style="font-size:1.1rem;font-weight:700;color:white;
                    letter-spacing:-0.3px;line-height:1.2">ThesisReview</div>
        <div style="font-size:0.7rem;color:rgba(255,255,255,0.5);
                    margin-top:3px;letter-spacing:0.4px">
            Sistema Inteligente de Tesis
        </div>
    </div>
    <div style="height:1px;background:rgba(255,255,255,0.14);margin:0 4px 14px"></div>
    <div style="background:rgba(255,255,255,0.09);border-radius:12px;
                padding:12px 14px;margin-bottom:16px;
                border:1px solid rgba(255,255,255,0.14)">
        <div style="font-size:0.85rem;font-weight:600;color:white;
                    margin-bottom:7px;overflow:hidden;text-overflow:ellipsis;
                    white-space:nowrap" title="{u['name']}">{u['name']}</div>
        <span style="background:{role_color};color:white;padding:3px 11px;
                     border-radius:20px;font-size:0.7rem;font-weight:600;
                     letter-spacing:0.3px">{role_label}</span>
    </div>
    <div style="font-size:0.7rem;color:rgba(255,255,255,0.42);
                text-transform:uppercase;letter-spacing:0.8px;
                padding:0 4px;margin-bottom:6px">Navegación</div>
    """, unsafe_allow_html=True)

    pages = ROLE_PAGES.get(u["role"], ROLE_PAGES["STUDENT"])
    if "page_override" in st.session_state:
        override = st.session_state.pop("page_override")
        if override in pages:
            st.session_state["_sidebar_page"] = override

    page = st.sidebar.radio("Menú", pages, key="_sidebar_page",
                            label_visibility="collapsed")

    # ── Indicadores de API en sidebar ────────────────────────────────────────
    flags = _get_api_flags()
    def _dot(active): return "🟢" if active else "🔴"
    ai_label = f"OpenAI {os.getenv('OPENAI_MODEL','gpt-4o-mini')}" if flags["openai"] else "Motor local"
    st.sidebar.markdown(f"""
    <div style="background:rgba(255,255,255,0.07);border-radius:10px;
                padding:10px 12px;margin:10px 0;font-size:0.75rem;
                border:1px solid rgba(255,255,255,0.12)">
        <div style="color:rgba(255,255,255,0.5);font-size:0.68rem;
                    text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px">
            APIs activas
        </div>
        <div style="line-height:1.9;color:rgba(255,255,255,0.85)">
            {_dot(flags['openai'])} IA: {ai_label}<br>
            {_dot(flags['crossref'])} CrossRef<br>
            {_dot(flags['copyleaks'])} Copyleaks<br>
            {_dot(flags['orcid'])} ORCID
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(
        "<div style='height:1px;background:rgba(255,255,255,0.14);margin:6px 4px 10px'></div>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("🔓 Cerrar sesión", use_container_width=True):
        st.session_state.user = None
        rerun()
    return page

def dashboard():
    st.title("Dashboard general")
    u = st.session_state.user
    if u["role"] == "STUDENT":
        advances = query("SELECT * FROM advances WHERE student_id=?", (u["id"],))
        analyses = query("""SELECT ai.* FROM ai_analyses ai
                            JOIN advances a ON a.id=ai.advance_id WHERE a.student_id=?""", (u["id"],))
    else:
        advances = query("SELECT * FROM advances")
        analyses = query("SELECT * FROM ai_analyses")
    c1, c2, c3, c4 = st.columns(4)
    pending = len([a for a in advances if a["status"] in ["Pendiente", "Análisis IA en proceso"]])
    reviewed = len([a for a in advances if a["status"] in ["Aprobado", "Observado", "Rechazado"]])
    avg = sum([a["overall_score"] for a in analyses]) / len(analyses) if analyses else 0
    grade = sum([a["grade"] for a in analyses]) / len(analyses) if analyses else 0
    c1.metric("Avances pendientes", pending)
    c2.metric("Revisados", reviewed)
    c3.metric("Cumplimiento IA promedio", f"{avg:.1f}%")
    c4.metric("Nota IA promedio", f"{grade:.1f}/20")
    st.subheader("Avances recientes")
    if u["role"] == "STUDENT":
        rows = query("""SELECT a.id,a.title,a.status,a.version,a.created_at,u.name student,p.name program
                        FROM advances a JOIN users u ON u.id=a.student_id JOIN programs p ON p.id=a.program_id
                        WHERE a.student_id=? ORDER BY a.id DESC LIMIT 10""", (u["id"],))
    else:
        rows = query("""SELECT a.id,a.title,a.status,a.version,a.created_at,u.name student,p.name program
                        FROM advances a JOIN users u ON u.id=a.student_id JOIN programs p ON p.id=a.program_id
                        ORDER BY a.id DESC LIMIT 10""")
    if rows:
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True)
    else:
        st.info("Aún no hay avances cargados.")
    st.subheader("Actividad agéntica")
    jobs = query("SELECT * FROM agent_jobs ORDER BY id DESC LIMIT 8")
    if jobs:
        for j in jobs:
            st.write(f"🤖 **{j['name']}** — {j['status']} — {j['created_at']}")

def cargar_avance():
    st.title("Cargar nuevo avance")
    user = st.session_state.user
    students = query("SELECT id,name FROM users WHERE role='STUDENT'")
    templates = query("SELECT t.id,t.name,p.name program FROM templates t JOIN programs p ON p.id=t.program_id WHERE t.active=1")
    c1, c2 = st.columns([1, 1])
    with c1:
        title = st.text_input("Título del avance", "Avance Capítulo 1")
        student_id = st.selectbox(
            "Estudiante",
            [s["id"] for s in students],
            format_func=lambda x: next(s["name"] for s in students if s["id"] == x)
        )
        template_id = st.selectbox(
            "Documento patrón",
            [t["id"] for t in templates],
            format_func=lambda x: next(t["name"] + " - " + t["program"] for t in templates if t["id"] == x)
        )
        advance_type = st.selectbox("Tipo de avance", ["Capítulo 1", "Capítulo 2", "Capítulo 3", "Tesis completa"])
        uploaded = st.file_uploader(
            f"Subir documento PDF, DOCX o TXT (máx. {MAX_FILE_MB} MB)",
            type=["pdf", "docx", "txt"]
        )
        analyze_now = st.checkbox("Ejecutar análisis IA automáticamente", value=True)
        if st.button("Guardar y procesar", use_container_width=True):
            if not uploaded:
                st.error("Sube un archivo.")
                return
            if uploaded.size > MAX_FILE_MB * 1024 * 1024:
                st.error(f"El archivo supera el límite de {MAX_FILE_MB} MB. Comprime o divide el documento.")
                return
            ext = uploaded.name.split(".")[-1].lower()
            if ext not in ("pdf", "docx", "txt"):
                st.error("Formato no permitido. Usa PDF, DOCX o TXT.")
                return
            os.makedirs("data/uploads", exist_ok=True)
            fpath = os.path.join("data/uploads", f"{int(time.time())}_{uploaded.name}")
            with open(fpath, "wb") as f:
                f.write(uploaded.getbuffer())
            text, pages = extract_text_from_upload(fpath, ext)
            with st.expander(f"Vista previa del texto extraído ({len(text):,} caracteres, ~{pages} páginas)"):
                st.text(text[:1500] if text else "No se pudo extraer texto del documento.")
            tpl = query("SELECT * FROM templates WHERE id=?", (template_id,))[0]
            student = query("SELECT * FROM users WHERE id=?", (student_id,))[0]
            program_id = student["program_id"] if student["program_id"] is not None else tpl["program_id"]
            if student["program_id"] is None:
                execute("UPDATE users SET program_id=? WHERE id=?", (program_id, student_id))
            # Auto-incrementar versión para mismo estudiante + tipo de avance
            prev_ver = query(
                "SELECT MAX(version) AS v FROM advances WHERE student_id=? AND advance_type=?",
                (student_id, advance_type)
            )
            version = (prev_ver[0]["v"] or 0) + 1
            adv_id = execute(
                """INSERT INTO advances(student_id,advisor_id,program_id,template_id,title,advance_type,
                   version,filename,file_path,file_type,text_content,page_count,status,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (student_id, student["advisor_id"], program_id, template_id, title, advance_type,
                 version, uploaded.name, fpath, ext, text, pages, "Pendiente", now())
            )
            log(user["id"], "UPLOAD_ADVANCE", "advances", adv_id, {"filename": uploaded.name, "version": version})
            execute(
                "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
                ("Agente extractor de documentos", adv_id, "Finalizado",
                 f"Texto extraído: {len(text)} caracteres", now(), now())
            )
            if analyze_now:
                run_full_ai_pipeline(adv_id, silent=True)
            st.success(f"Avance guardado — ID {adv_id} · versión v{version}")
            st.balloons()
    with c2:
        st.subheader("Pipeline IA agéntico")
        steps = ["Carga Word/PDF", "Extracción", "Chunking", "Evaluación IA", "Similitud", "Citas", "Reporte"]
        for i, s in enumerate(steps, 1):
            st.markdown(f"**{i}. {s}**")
        st.info("El sistema funciona sin API externa. Si configuras OpenAI/CrossRef/Copyleaks, puede conectarse a servicios reales.")

def run_full_ai_pipeline(advance_id: int, silent=False):
    adv = query("SELECT * FROM advances WHERE id=?", (advance_id,))[0]
    tpl = query("SELECT * FROM templates WHERE id=?", (adv["template_id"],))[0]
    rubric = json.loads(tpl["rubric_json"])
    expected = tpl["expected_sections"].split("|")
    execute("UPDATE advances SET status=? WHERE id=?", ("Análisis IA en proceso", advance_id))
    execute(
        "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
        ("Agente planificador", advance_id, "Finalizado",
         " | ".join(agent_plan_for_document(adv["text_content"] or "")), now(), now())
    )
    result = local_agentic_analysis(adv["text_content"] or "", expected, rubric, adv["advance_type"])
    execute("DELETE FROM ai_analyses WHERE advance_id=?", (advance_id,))
    aid = execute(
        """INSERT INTO ai_analyses(advance_id,structure_score,content_score,form_score,originality_score,
           overall_score,grade,executive_summary,model_used,processing_ms,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (advance_id, result["scores"]["structure"], result["scores"]["content"],
         result["scores"]["form"], result["scores"]["originality"],
         result["scores"]["overall"], result["grade"], result["executiveSummary"],
         result["modelUsed"], result["processingMs"], now())
    )
    for f in result["findings"]:
        execute(
            """INSERT INTO findings(analysis_id,type,section_ref,page_ref,severity,description,
               correction_steps,example_improvement,recommendation,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (aid, f["type"], f["section_ref"], f.get("page_ref"), f["severity"],
             f["description"], f["correction_steps"], f["example_improvement"],
             f["recommendation"], now())
        )
    sim = run_similarity_check(advance_id, adv["text_content"] or "", adv["program_id"])
    cites = validate_citations(advance_id, adv["text_content"] or "", online=False)
    execute("UPDATE advances SET status=? WHERE id=?", ("En revisión humana", advance_id))
    execute(
        "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
        ("Agente evaluador IA", advance_id, "Finalizado",
         f"Cumplimiento: {result['scores']['overall']}%", now(), now())
    )
    execute(
        "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
        ("Agente similitud/plagio", advance_id, "Finalizado",
         f"{len(sim)} coincidencias internas", now(), now())
    )
    execute(
        "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
        ("Agente validador de citas", advance_id, "Finalizado",
         f"{len(cites)} referencias procesadas", now(), now())
    )
    if not silent:
        st.success("Análisis IA completado.")

def revision_ia():
    st.title("Revisión inteligente con IA")
    u = st.session_state.user
    if u["role"] == "STUDENT":
        advances = query(
            "SELECT id,title,status FROM advances WHERE student_id=? ORDER BY id DESC", (u["id"],)
        )
    else:
        advances = query("SELECT id,title,status FROM advances ORDER BY id DESC")
    if not advances:
        st.info("Primero carga un avance.")
        return
    adv_id = st.selectbox(
        "Selecciona avance",
        [a["id"] for a in advances],
        format_func=lambda x: f"{x} - {next(a['title'] for a in advances if a['id']==x)}"
    )
    if u["role"] != "STUDENT":
        st.info("Si este avance fue analizado con una versión anterior, presiona el botón para recalcular con motor v4.")
        if st.button("Ejecutar/Re-ejecutar pipeline IA"):
            run_full_ai_pipeline(adv_id)
    ana = query("SELECT * FROM ai_analyses WHERE advance_id=?", (adv_id,))
    if not ana:
        st.warning("Este avance aún no tiene análisis IA.")
        return
    a = ana[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Estructura", f"{a['structure_score']:.1f}%")
    c2.metric("Contenido", f"{a['content_score']:.1f}%")
    c3.metric("Forma", f"{a['form_score']:.1f}%")
    c4.metric("Calidad interna", f"{a['originality_score']:.1f}%")
    c5.metric("Nota", f"{a['grade']:.1f}/20")
    st.caption("Nota: este sistema no es detector de IA como Turnitin. 'Calidad interna' evalúa repetición, consistencia y desarrollo académico. La similitud se muestra en la sección correspondiente.")
    st.subheader("Resumen ejecutivo")
    st.write(a["executive_summary"])
    st.subheader("Hallazgos")
    findings = query("SELECT * FROM findings WHERE analysis_id=?", (a["id"],))
    for f in findings:
        with st.expander(f"{f['severity']} · {f['type']} · {f['section_ref']}"):
            st.write("**Descripción:**", f["description"])
            st.write("**Corrección:**", f["correction_steps"])
            st.write("**Ejemplo:**", f["example_improvement"])
            st.write("**Recomendación:**", f["recommendation"])
    st.subheader("Similitud interna")
    sims = query(
        """SELECT pr.*, a.title compared_title FROM plagiarism_results pr
           LEFT JOIN advances a ON a.id=pr.compared_advance_id WHERE pr.advance_id=?""",
        (adv_id,)
    )
    st.dataframe(pd.DataFrame([dict(s) for s in sims]) if sims else pd.DataFrame(), use_container_width=True)
    st.subheader("Citas")
    cites = query("SELECT raw_reference,status,suggestion FROM citations WHERE advance_id=?", (adv_id,))
    st.dataframe(pd.DataFrame([dict(c) for c in cites]) if cites else pd.DataFrame(), use_container_width=True)

def revision_humana():
    st.title("Revisión humana + IA")
    advances = query("SELECT id,title,status FROM advances ORDER BY id DESC")
    if not advances:
        st.info("No hay avances.")
        return
    adv_id = st.selectbox(
        "Avance",
        [a["id"] for a in advances],
        format_func=lambda x: f"{x} - {next(a['title'] for a in advances if a['id']==x)}"
    )
    ana = query("SELECT * FROM ai_analyses WHERE advance_id=?", (adv_id,))
    if not ana:
        st.warning("Ejecuta primero la revisión IA.")
        return
    findings = query("SELECT * FROM findings WHERE analysis_id=?", (ana[0]["id"],))
    for f in findings:
        with st.expander(f"Hallazgo {f['id']} · {f['severity']} · {f['section_ref']}"):
            st.write(f["description"])
            action = st.selectbox(
                "Acción humana",
                ["Pendiente", "Aceptado", "Modificado", "Rechazado"],
                key=f"act{f['id']}",
                index=["Pendiente", "Aceptado", "Modificado", "Rechazado"].index(f["human_action"])
                if f["human_action"] in ["Pendiente", "Aceptado", "Modificado", "Rechazado"] else 0
            )
            comment = st.text_area("Comentario del asesor", value=f["human_comment"] or "", key=f"com{f['id']}")
            if st.button("Guardar validación", key=f"save{f['id']}"):
                execute("UPDATE findings SET human_action=?, human_comment=? WHERE id=?", (action, comment, f["id"]))
                st.success("Validación guardada para aprendizaje futuro.")
    st.divider()
    final_grade = st.number_input("Nota final del asesor", min_value=0.0, max_value=20.0,
                                  value=float(ana[0]["grade"]), step=0.5)
    status = st.selectbox("Estado final", ["Observado", "Aprobado", "Rechazado"])
    human_comment = st.text_area("Comentario final")
    if st.button("Cerrar revisión y generar acta"):
        reviewer_id = st.session_state.user["id"]
        execute("DELETE FROM reviews WHERE advance_id=?", (adv_id,))
        execute(
            """INSERT INTO reviews(advance_id,reviewer_id,final_grade,human_comment,status,reviewed_at,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (adv_id, reviewer_id, final_grade, human_comment, status, now(), now())
        )
        execute("UPDATE advances SET status=? WHERE id=?", (status, adv_id))
        path = generate_review_pdf(adv_id)
        log(reviewer_id, "HUMAN_REVIEW_CLOSED", "advances", adv_id, {"status": status, "grade": final_grade})
        st.success("Revisión cerrada.")
        with open(path, "rb") as f:
            st.download_button("Descargar acta PDF", f, file_name=os.path.basename(path), mime="application/pdf")

def revision_lotes():
    st.title("Revisión por lotes")
    rows = query("SELECT id,title,status FROM advances ORDER BY id DESC")
    ids = st.multiselect(
        "Selecciona avances",
        [r["id"] for r in rows],
        format_func=lambda x: f"{x} - {next(r['title'] for r in rows if r['id']==x)}"
    )
    if st.button("Iniciar análisis IA masivo"):
        prog = st.progress(0)
        for i, aid in enumerate(ids, 1):
            run_full_ai_pipeline(aid, silent=True)
            prog.progress(i / len(ids))
        st.success("Procesamiento por lotes finalizado.")

def plantillas():
    st.title("Documentos patrón institucionales")
    programs = query("SELECT * FROM programs")
    with st.form("tpl"):
        pid = st.selectbox(
            "Programa",
            [p["id"] for p in programs],
            format_func=lambda x: next(p["name"] for p in programs if p["id"] == x)
        )
        name = st.text_input("Nombre", "Nuevo patrón institucional")
        version = st.text_input("Versión", "v1.0")
        sections = st.text_area(
            "Secciones obligatorias separadas por |",
            "Carátula|Índice|Resumen|Introducción|Planteamiento del problema|Objetivos|Justificación|Marco teórico|Metodología|Resultados|Discusión|Conclusiones|Referencias"
        )
        content = st.text_area("Contenido/criterios del patrón", "Criterios institucionales de tesis...")
        if st.form_submit_button("Guardar plantilla"):
            rubric = {"estructura": 30, "contenido": 40, "forma": 20, "originalidad": 10,
                      "nota_maxima": 20, "umbral_alerta": 65}
            execute(
                """INSERT INTO templates(program_id,name,version,content,expected_sections,rubric_json,active,created_at)
                   VALUES (?,?,?,?,?,?,1,?)""",
                (pid, name, version, content, sections, json.dumps(rubric), now())
            )
            st.success("Plantilla creada.")
    st.dataframe(
        pd.DataFrame([dict(t) for t in query(
            """SELECT t.id,t.name,t.version,p.name program,t.active,t.created_at
               FROM templates t JOIN programs p ON p.id=t.program_id"""
        )]),
        use_container_width=True
    )

def usuarios_orcid():
    st.title("Usuarios, roles y ORCID")
    st.caption("Aquí puedes registrar alumnos, asesores, coordinadores y administradores para la demostración.")
    tabs = st.tabs(["Listado de usuarios", "Registrar usuario", "Asignar asesor", "ORCID / Expertise"])

    with tabs[0]:
        rows = query("""SELECT u.id,u.name,u.email,u.role,p.name program, adv.name advisor,
                        u.orcid_id,u.affiliation,u.expertise
                        FROM users u
                        LEFT JOIN programs p ON p.id=u.program_id
                        LEFT JOIN users adv ON adv.id=u.advisor_id
                        ORDER BY u.id""")
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True)

    with tabs[1]:
        st.subheader("Registrar nuevo usuario")
        programs = query("SELECT * FROM programs ORDER BY name")
        advisors = query("SELECT id,name FROM users WHERE role='ADVISOR' ORDER BY name")
        with st.form("form_create_user"):
            name = st.text_input("Nombres y apellidos")
            email = st.text_input("Correo institucional o demo")
            password = st.text_input("Contraseña", type="password", value="123456")
            role = st.selectbox("Rol", ["STUDENT", "ADVISOR", "COORDINATOR", "ADMIN"])
            program_id = st.selectbox(
                "Programa académico",
                [None] + [p["id"] for p in programs],
                format_func=lambda x: "Sin programa" if x is None else next(p["name"] for p in programs if p["id"] == x),
                help="Para alumnos y asesores se recomienda seleccionar un programa."
            )
            advisor_id = None
            if role == "STUDENT":
                advisor_id = st.selectbox(
                    "Asesor asignado",
                    [None] + [a["id"] for a in advisors],
                    format_func=lambda x: "Sin asesor" if x is None else next(a["name"] for a in advisors if a["id"] == x)
                )
            orcid_id = st.text_input("ORCID, solo si es asesor", placeholder="0000-0000-0000-0000")
            affiliation = st.text_input("Afiliación", placeholder="Universidad Nacional de Trujillo")
            expertise = st.text_area("Líneas de investigación / expertise",
                                     placeholder="desarrollo de software, inteligencia artificial, sistemas web")
            submitted = st.form_submit_button("Registrar usuario")
            if submitted:
                if not name.strip() or not email.strip():
                    st.error("Nombre y correo son obligatorios.")
                else:
                    from modules.database import hash_password
                    exists = query("SELECT id FROM users WHERE email=?", (email.strip(),))
                    if exists:
                        st.error("Ya existe un usuario con ese correo.")
                    else:
                        uid = execute(
                            """INSERT INTO users(name,email,password_hash,role,program_id,advisor_id,
                               orcid_id,affiliation,expertise,created_at)
                               VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (name.strip(), email.strip(), hash_password(password), role,
                             program_id, advisor_id, orcid_id.strip() or None,
                             affiliation.strip() or None, expertise.strip() or None, now())
                        )
                        log(st.session_state.user["id"], "CREATE_USER", "users", uid,
                            {"role": role, "email": email})
                        st.success(f"Usuario registrado correctamente. ID: {uid}")

    with tabs[2]:
        st.subheader("Asignar o cambiar asesor de un alumno")
        students = query("SELECT id,name,email,advisor_id FROM users WHERE role='STUDENT' ORDER BY name")
        advisors = query("SELECT id,name,email FROM users WHERE role='ADVISOR' ORDER BY name")
        if not students:
            st.info("No hay alumnos registrados.")
        elif not advisors:
            st.info("No hay asesores registrados.")
        else:
            student_id = st.selectbox(
                "Alumno",
                [s["id"] for s in students],
                format_func=lambda x: next(f"{s['name']} ({s['email']})" for s in students if s["id"] == x)
            )
            advisor_id = st.selectbox(
                "Asesor",
                [a["id"] for a in advisors],
                format_func=lambda x: next(f"{a['name']} ({a['email']})" for a in advisors if a["id"] == x)
            )
            if st.button("Guardar asignación"):
                execute("UPDATE users SET advisor_id=? WHERE id=?", (advisor_id, student_id))
                log(st.session_state.user["id"], "ASSIGN_ADVISOR", "users", student_id,
                    {"advisor_id": advisor_id})
                st.success("Asesor asignado correctamente.")

    with tabs[3]:
        st.subheader("Vinculación ORCID / Validación de expertise del asesor")
        advisors = query("SELECT * FROM users WHERE role='ADVISOR'")
        if advisors:
            aid = st.selectbox(
                "Asesor",
                [a["id"] for a in advisors],
                format_func=lambda x: next(a["name"] for a in advisors if a["id"] == x),
                key="advisor_orcid"
            )
            adv = next(a for a in advisors if a["id"] == aid)
            with st.form("form_orcid_update"):
                orcid_id = st.text_input("ORCID", value=adv["orcid_id"] or "")
                affiliation = st.text_input("Afiliación", value=adv["affiliation"] or "")
                expertise = st.text_area("Expertise / líneas de investigación",
                                         value=adv["expertise"] or "")
                if st.form_submit_button("Actualizar perfil del asesor"):
                    execute(
                        "UPDATE users SET orcid_id=?, affiliation=?, expertise=? WHERE id=?",
                        (orcid_id.strip() or None, affiliation.strip() or None,
                         expertise.strip() or None, aid)
                    )
                    log(st.session_state.user["id"], "UPDATE_ORCID_PROFILE", "users", aid)
                    st.success("Perfil actualizado.")
            thesis_title = st.text_input(
                "Título de tesis para validación semántica",
                "Sistema web inteligente de gestión y predicción de desperdicio alimentario"
            )
            if st.button("Validar expertise"):
                exp = (adv["expertise"] or "").lower()
                score = sum(1 for w in thesis_title.lower().split() if len(w) > 4 and w in exp)
                if score:
                    st.success("El perfil del asesor tiene coincidencias temáticas con la tesis.")
                else:
                    st.warning("No se detectó coincidencia fuerte. El coordinador debería validar manualmente.")

            st.divider()
            orcid_enabled = os.getenv("ORCID_ENABLED", "false").lower() == "true"
            orcid_to_check = adv["orcid_id"] or ""

            # ── Encabezado dinámico según flag ───────────────────────────────
            st.subheader("Verificar ORCID en registro público")
            if orcid_enabled:
                st.success("🟢 ORCID activo — verificación contra el registro público habilitada.")
            else:
                st.warning("🔴 ORCID desactivado (`ORCID_ENABLED=false`). Las verificaciones son solo locales.")

            if orcid_to_check:
                # Mostrar enlace al perfil siempre
                st.markdown(
                    f"🔗 [Ver perfil en orcid.org](https://orcid.org/{orcid_to_check}) "
                    f"— ID: `{orcid_to_check}`"
                )

                btn_label = "Verificar en ORCID Registry" if orcid_enabled else "Verificar ORCID (modo demo)"
                if st.button(btn_label):
                    import requests as _req
                    if not orcid_enabled:
                        st.info("Activa `ORCID_ENABLED=true` en .env para verificación real.")
                    else:
                        with st.spinner(f"Consultando pub.orcid.org para {orcid_to_check} …"):
                            try:
                                url = f"https://pub.orcid.org/v3.0/{orcid_to_check}/person"
                                r = _req.get(url, headers={"Accept": "application/json"}, timeout=10)
                                if r.status_code == 200:
                                    data      = r.json()
                                    name_data = data.get("name") or {}
                                    given     = (name_data.get("given-names")  or {}).get("value", "")
                                    family    = (name_data.get("family-name")  or {}).get("value", "")
                                    bio       = ((data.get("biography") or {}).get("content") or "")
                                    full_name = f"{given} {family}".strip()
                                    st.success(f"✅ ORCID válido — Nombre registrado: **{full_name}**")
                                    if bio:
                                        st.info(f"Biografía: {bio[:400]}")
                                    # Mostrar campos del registro
                                    works_url = f"https://pub.orcid.org/v3.0/{orcid_to_check}/works"
                                    try:
                                        rw = _req.get(works_url, headers={"Accept": "application/json"}, timeout=8)
                                        if rw.ok:
                                            works = rw.json().get("group", [])
                                            st.caption(f"Publicaciones registradas en ORCID: {len(works)}")
                                    except Exception:
                                        pass
                                    log(st.session_state.user["id"], "ORCID_VERIFIED", "users", aid,
                                        {"orcid": orcid_to_check, "registered_name": full_name})
                                elif r.status_code == 404:
                                    st.error("❌ ORCID no encontrado. Verifica que el ID sea correcto.")
                                else:
                                    st.warning(f"Respuesta inesperada del servidor ORCID: HTTP {r.status_code}")
                            except Exception as e:
                                st.warning(f"No se pudo conectar al servidor ORCID: {e}")
            else:
                st.info("Guarda primero un ORCID en el perfil del asesor para poder verificarlo.")
        else:
            st.info("No hay asesores registrados.")

def estadisticas():
    st.title("Estadísticas del programa")
    analyses = query(
        "SELECT ai.*, a.created_at, a.status FROM ai_analyses ai JOIN advances a ON a.id=ai.advance_id"
    )
    advances = query("SELECT * FROM advances")
    if not advances:
        st.info("No hay datos.")
        return
    df_adv = pd.DataFrame([dict(a) for a in advances])
    st.plotly_chart(px.pie(df_adv, names="status", title="Distribución de estados"), use_container_width=True)
    if analyses:
        df = pd.DataFrame([dict(a) for a in analyses])
        st.plotly_chart(
            px.histogram(df, x="grade", nbins=10, title="Distribución de notas IA"),
            use_container_width=True
        )
        st.plotly_chart(
            px.bar(df, y=["structure_score", "content_score", "form_score", "originality_score"],
                   title="Dimensiones de evaluación académica"),
            use_container_width=True
        )

def reportes():
    st.title("Reportes y exportación")

    # ── Acta individual ─────────────────────────────────────────────
    st.subheader("Acta de revisión individual")
    advances = query("SELECT id,title FROM advances ORDER BY id DESC")
    if advances:
        aid = st.selectbox(
            "Avance",
            [a["id"] for a in advances],
            format_func=lambda x: f"{x} - {next(a['title'] for a in advances if a['id']==x)}"
        )
        if st.button("Generar acta PDF individual"):
            path = generate_review_pdf(aid)
            with open(path, "rb") as f:
                st.download_button("Descargar acta PDF", f, os.path.basename(path),
                                   "application/pdf", key="dl_ind")
    else:
        st.info("No hay avances cargados aún.")

    st.divider()

    # ── Reporte comparativo ──────────────────────────────────────────
    st.subheader("Reporte comparativo del programa")
    programs = query("SELECT * FROM programs ORDER BY name")
    if programs:
        prog_id = st.selectbox(
            "Programa",
            [p["id"] for p in programs],
            format_func=lambda x: next(p["name"] for p in programs if p["id"] == x),
            key="rep_prog"
        )
        if st.button("Generar reporte comparativo (todos los alumnos)"):
            path = generate_comparative_pdf(prog_id)
            with open(path, "rb") as f:
                st.download_button(
                    "Descargar reporte comparativo PDF", f,
                    os.path.basename(path), "application/pdf", key="dl_comp"
                )

    st.divider()

    # ── Reporte de gestión global ────────────────────────────────────
    st.subheader("Reporte de gestión global")
    if st.button("Generar reporte de gestión"):
        path = generate_management_pdf()
        with open(path, "rb") as f:
            st.download_button(
                "Descargar reporte de gestión PDF", f,
                os.path.basename(path), "application/pdf", key="dl_mgmt"
            )

    st.divider()

    # ── Exportación CSV ──────────────────────────────────────────────
    st.subheader("Exportar datos en CSV")
    for table in ["advances", "ai_analyses", "findings", "citations", "plagiarism_results", "audit_logs"]:
        rows = query(f"SELECT * FROM {table}")
        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            st.download_button(
                f"Descargar {table}.csv",
                df.to_csv(index=False).encode("utf-8"),
                file_name=f"{table}.csv"
            )

def app_movil():
    st.title("App móvil para estudiantes")
    st.success("La carpeta `mobile/` contiene una app funcional React Native + Expo, alineada al documento original.")
    st.code("cd mobile\nnpm install\nnpx expo start")
    st.write("Además, se mantiene una vista previa web simple de la app para demostrar la interfaz desde Streamlit.")
    html_path = os.path.join("mobile_app_mock", "index.html")
    if os.path.exists(html_path):
        st.components.v1.html(open(html_path, encoding="utf-8").read(), height=760)

def auditoria():
    st.title("Auditoría y trazabilidad")
    rows = query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 200")
    st.dataframe(pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame(), use_container_width=True)
    st.subheader("Jobs agénticos")
    jobs = query("SELECT * FROM agent_jobs ORDER BY id DESC LIMIT 200")
    st.dataframe(pd.DataFrame([dict(j) for j in jobs]) if jobs else pd.DataFrame(), use_container_width=True)

def _get_api_flags():
    """Retorna dict con qué APIs están configuradas según el .env cargado."""
    return {
        "openai":    bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "crossref":  os.getenv("CROSSREF_ENABLED", "false").lower() == "true",
        "copyleaks": bool(os.getenv("COPYLEAKS_API_KEY", "").strip())
                     and bool(os.getenv("COPYLEAKS_EMAIL", "").strip()),
        "orcid":     os.getenv("ORCID_ENABLED", "false").lower() == "true",
    }

def _api_badge(active: bool, label_on: str, label_off: str):
    color = "#4caf50" if active else "#9e9e9e"
    label = label_on if active else label_off
    dot   = "●" if active else "○"
    st.markdown(
        f'<span style="background:{color}22;color:{color};border:1.5px solid {color};'
        f'padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600">'
        f'{dot} {label}</span>',
        unsafe_allow_html=True,
    )

def configuracion():
    st.title("Configuración del sistema")
    flags = _get_api_flags()

    # ── Estado visual de APIs ─────────────────────────────────────────────────
    st.subheader("Estado de integraciones externas")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _api_badge(flags["openai"],    "OpenAI activo",     "OpenAI no configurado")
    with c2:
        _api_badge(flags["crossref"],  "CrossRef activo",   "CrossRef desactivado")
    with c3:
        _api_badge(flags["copyleaks"], "Copyleaks activo",  "Copyleaks no configurado")
    with c4:
        _api_badge(flags["orcid"],     "ORCID activo",      "ORCID desactivado")
    with c5:
        motor = f"OpenAI {os.getenv('OPENAI_MODEL','gpt-4o-mini')}" if flags["openai"] else "Motor local v4"
        _api_badge(True, motor, motor)

    st.markdown("---")

    # ── Pruebas en tiempo real ────────────────────────────────────────────────
    st.subheader("Probar conexión en tiempo real")

    col_oa, col_cr, col_cp, col_or = st.columns(4)

    # ── OpenAI ────────────────────────────────────────────────────────────────
    with col_oa:
        st.markdown("**OpenAI GPT**")
        key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if key:
            st.caption(f"Modelo: `{model}`")
            st.caption(f"Key: `...{key[-6:]}`")
        else:
            st.caption("_No configurada_")
        if st.button("Probar OpenAI", disabled=not key, use_container_width=True):
            with st.spinner("Conectando con OpenAI…"):
                try:
                    import openai
                    client = openai.OpenAI(api_key=key)
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "Responde solo: OK"}],
                        max_tokens=5,
                        temperature=0,
                    )
                    reply = resp.choices[0].message.content.strip()
                    st.success(f"✅ Conexión exitosa — respuesta: `{reply}`")
                except ImportError:
                    st.error("❌ Paquete `openai` no instalado. Ejecuta: `pip install openai`")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # ── CrossRef ──────────────────────────────────────────────────────────────
    with col_cr:
        st.markdown("**CrossRef API**")
        cr_on = flags["crossref"]
        st.caption(f"Estado: `CROSSREF_ENABLED={os.getenv('CROSSREF_ENABLED','false')}`")
        st.caption("API pública — no requiere clave")
        if st.button("Probar CrossRef", use_container_width=True):
            with st.spinner("Consultando CrossRef…"):
                try:
                    import requests as _req
                    r = _req.get(
                        "https://api.crossref.org/works",
                        params={"query.title": "machine learning", "rows": 1},
                        timeout=8,
                    )
                    if r.ok and r.json().get("message", {}).get("items"):
                        title = r.json()["message"]["items"][0].get("title", ["—"])[0]
                        st.success(f"✅ CrossRef responde — ejemplo: _{title[:60]}…_")
                        if not cr_on:
                            st.info("Activa con `CROSSREF_ENABLED=true` en .env para validar automáticamente.")
                    else:
                        st.warning(f"Respuesta inesperada: HTTP {r.status_code}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # ── Copyleaks ─────────────────────────────────────────────────────────────
    with col_cp:
        st.markdown("**Copyleaks**")
        cp_key   = os.getenv("COPYLEAKS_API_KEY", "").strip()
        cp_email = os.getenv("COPYLEAKS_EMAIL",   "").strip()
        if cp_key:
            st.caption(f"Email: `{cp_email}`")
            st.caption(f"Key: `...{cp_key[-6:]}`")
        else:
            st.caption("_No configurada_")
        if st.button("Probar Copyleaks", disabled=not flags["copyleaks"], use_container_width=True):
            with st.spinner("Autenticando en Copyleaks…"):
                try:
                    import requests as _req
                    r = _req.post(
                        "https://id.copyleaks.com/v3/account/login/api",
                        json={"email": cp_email, "key": cp_key},
                        timeout=12,
                    )
                    if r.ok and r.json().get("access_token"):
                        st.success("✅ Autenticación exitosa — Copyleaks listo para escanear.")
                    else:
                        st.error(f"❌ Fallo de auth: HTTP {r.status_code} — {r.text[:120]}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    # ── ORCID ─────────────────────────────────────────────────────────────────
    with col_or:
        st.markdown("**ORCID Registry**")
        orcid_on = flags["orcid"]
        st.caption(f"Estado: `ORCID_ENABLED={os.getenv('ORCID_ENABLED','false')}`")
        st.caption("API pública — no requiere clave")
        if st.button("Probar ORCID", use_container_width=True):
            with st.spinner("Consultando ORCID Registry…"):
                try:
                    import requests as _req
                    # Consultar un ORCID público de ejemplo (Stephen Hawking)
                    test_orcid = "0000-0002-1825-0097"
                    r = _req.get(
                        f"https://pub.orcid.org/v3.0/{test_orcid}/person",
                        headers={"Accept": "application/json"},
                        timeout=10,
                    )
                    if r.ok:
                        name = r.json().get("name", {})
                        given  = (name.get("given-names")  or {}).get("value", "")
                        family = (name.get("family-name")  or {}).get("value", "")
                        st.success(f"✅ ORCID responde — ejemplo: **{given} {family}**")
                        if not orcid_on:
                            st.info("Activa con `ORCID_ENABLED=true` en .env para verificación automática.")
                    else:
                        st.warning(f"HTTP {r.status_code} — ORCID no respondió correctamente.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    st.markdown("---")

    # ── Variables de entorno activas ──────────────────────────────────────────
    st.subheader("Variables de entorno cargadas")
    env_vars = {
        "OPENAI_API_KEY":    f"...{os.getenv('OPENAI_API_KEY','')[-6:]}" if os.getenv("OPENAI_API_KEY") else "❌ no definida",
        "OPENAI_MODEL":      os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "CROSSREF_ENABLED":  os.getenv("CROSSREF_ENABLED", "false"),
        "ORCID_ENABLED":     os.getenv("ORCID_ENABLED", "false"),
        "COPYLEAKS_API_KEY": f"...{os.getenv('COPYLEAKS_API_KEY','')[-6:]}" if os.getenv("COPYLEAKS_API_KEY") else "❌ no definida",
        "COPYLEAKS_EMAIL":   os.getenv("COPYLEAKS_EMAIL", "❌ no definida"),
        "MAX_FILE_MB":       os.getenv("MAX_FILE_MB", "20"),
        "DB_PATH":           os.getenv("DB_PATH", "data/thesis_review.db"),
    }
    for k, v in env_vars.items():
        ok = "❌" not in str(v)
        icon = "🟢" if ok else "🔴"
        st.markdown(f"{icon} `{k}` = `{v}`")

    st.markdown("---")
    st.subheader("Rúbrica base por defecto")
    st.json({"estructura": 30, "contenido": 40, "forma": 20, "originalidad": 10,
             "nota_maxima": 20, "umbral_alerta": 65})

    st.markdown("---")
    st.caption("Los cambios en .env se aplican al **reiniciar** la app. "
               "El sistema usa las APIs si están configuradas; si fallan, cae automáticamente al motor local.")

    st.markdown("---")

    # ── Zona de peligro ───────────────────────────────────────────────────────
    st.subheader("⚠️ Zona de peligro")
    st.warning("Estas acciones **eliminan datos permanentemente** y no se pueden deshacer.")

    with st.expander("Limpiar avances y análisis de prueba"):
        st.markdown(
            "Elimina **todos** los avances, análisis IA, hallazgos, citas, "
            "resultados de plagio, revisiones y jobs agénticos. "
            "Los usuarios, programas y plantillas **se conservan**."
        )
        confirmar = st.text_input(
            "Escribe **LIMPIAR** para confirmar",
            placeholder="LIMPIAR",
            key="confirm_clean"
        )
        if st.button("🗑️ Limpiar todos los avances", type="primary"):
            if confirmar.strip().upper() == "LIMPIAR":
                tablas = [
                    "findings", "ai_analyses", "plagiarism_results",
                    "citations", "reviews", "agent_jobs", "advances"
                ]
                from modules.database import connect as _connect
                conn = _connect()
                totales = {}
                for t in tablas:
                    cur = conn.execute(f"DELETE FROM {t}")
                    totales[t] = cur.rowcount
                conn.commit()
                conn.close()
                log(st.session_state.user["id"], "CLEAN_ALL_ADVANCES", "advances", None,
                    {"filas_eliminadas": totales})
                st.success(
                    "✅ Base de datos limpia. " +
                    " | ".join(f"{t}: {n}" for t, n in totales.items())
                )
                st.balloons()
            else:
                st.error("Escribe exactamente LIMPIAR para confirmar.")

def _avance_query(u, filter_statuses):
    """Devuelve todos los avances con sus métricas IA, aplicando filtros de rol y estado."""
    where_parts = []
    params = []
    if u["role"] == "STUDENT":
        where_parts.append("a.student_id = ?")
        params.append(u["id"])
    if filter_statuses:
        placeholders = ",".join("?" * len(filter_statuses))
        where_parts.append(f"a.status IN ({placeholders})")
        params.extend(filter_statuses)
    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    sql = f"""
        SELECT a.id, a.title, a.status, a.version, a.advance_type, a.created_at,
               u.name AS student_name, p.name AS program,
               ai.overall_score, ai.grade
        FROM advances a
        JOIN users u ON u.id = a.student_id
        JOIN programs p ON p.id = a.program_id
        LEFT JOIN ai_analyses ai ON ai.advance_id = a.id
        {where}
        ORDER BY a.id DESC
    """
    return query(sql, tuple(params))


def _render_status_badge(status):
    label, color = STATUS_DISPLAY.get(status, (status, "#9e9e9e"))
    st.markdown(
        f'<span style="background:{color};color:#fff;padding:5px 13px;'
        f'border-radius:20px;font-size:12px;font-weight:bold;white-space:nowrap">'
        f'{label}</span>',
        unsafe_allow_html=True,
    )


def avances_tesis():
    """Vista principal: listado de avances con filtros y acceso al detalle."""
    if "avances_filter" not in st.session_state:
        st.session_state.avances_filter = "Todos"
    if "avances_selected_id" not in st.session_state:
        st.session_state.avances_selected_id = None

    # ── Vista de detalle ──────────────────────────────────────────────────────
    if st.session_state.avances_selected_id is not None:
        avance_detalle(st.session_state.avances_selected_id)
        return

    # ── Cabecera y botones de filtro ──────────────────────────────────────────
    st.title("Avances de Tesis")
    u = st.session_state.user

    # Fila de filtros
    filter_names = [f for f, _ in STATUS_FILTER_MAP]
    n_filters = len(filter_names)
    can_upload = u["role"] in ("ADMIN", "COORDINATOR", "ADVISOR")
    btn_cols = st.columns(n_filters + (1 if can_upload else 0))
    for i, fname in enumerate(filter_names):
        with btn_cols[i]:
            btype = "primary" if st.session_state.avances_filter == fname else "secondary"
            if st.button(fname, key=f"flt_{fname}", type=btype, use_container_width=True):
                st.session_state.avances_filter = fname
                rerun()
    if can_upload:
        with btn_cols[n_filters]:
            if st.button("+ Subir avance", type="primary", use_container_width=True):
                st.session_state.page_override = "Cargar avance"
                rerun()

    st.write("")

    # ── Obtener avances ───────────────────────────────────────────────────────
    active_filter = st.session_state.avances_filter
    filter_statuses = next(v for k, v in STATUS_FILTER_MAP if k == active_filter)
    advances = _avance_query(u, filter_statuses)

    if not advances:
        st.info("No hay avances registrados con este filtro.")
        return

    # ── Tarjetas de avance ────────────────────────────────────────────────────
    for adv in advances:
        score = adv["overall_score"] or 0
        grade = adv["grade"] or 0
        with st.container(border=True):
            col_info, col_status, col_btn = st.columns([6, 2, 1])
            with col_info:
                st.markdown(f"**{adv['title']}**")
                c1, c2, c3, c4 = st.columns(4)
                c1.caption(f"👤 {adv['student_name']}")
                c2.caption(f"📖 {adv['advance_type']}")
                c3.caption(f"🔢 v{adv['version']}")
                c4.caption(f"🎓 {adv['program']}")
                if score > 0:
                    st.progress(
                        score / 100,
                        text=f"Cumplimiento: {score:.0f}%  ·  Nota: {grade:.1f}/20",
                    )
                else:
                    st.caption("_Sin análisis IA aún_")
                st.caption(f"📅 {adv['created_at']}")
            with col_status:
                st.write("")
                _render_status_badge(adv["status"])
            with col_btn:
                st.write("")
                if st.button("Ver →", key=f"det_{adv['id']}"):
                    st.session_state.avances_selected_id = adv["id"]
                    rerun()


def avance_detalle(adv_id):
    """Vista de detalle de un avance con pestañas Hallazgos, Plagio y Referencias."""
    if st.button("← Volver a Avances"):
        st.session_state.avances_selected_id = None
        rerun()

    # ── Datos del avance ──────────────────────────────────────────────────────
    rows = query(
        """SELECT a.*, u.name AS student_name, p.name AS program_name,
                  adv.name AS advisor_name
           FROM advances a
           JOIN users u   ON u.id  = a.student_id
           JOIN programs p ON p.id = a.program_id
           LEFT JOIN users adv ON adv.id = a.advisor_id
           WHERE a.id = ?""",
        (adv_id,),
    )
    if not rows:
        st.error("Avance no encontrado.")
        return
    adv = rows[0]

    # ── Encabezado ────────────────────────────────────────────────────────────
    st.title(adv["title"])
    h1, h2, h3, h4 = st.columns(4)
    h1.markdown(f"**Autor:** {adv['student_name']}")
    h2.markdown(f"**Capítulo:** {adv['advance_type']}")
    h3.markdown(f"**Versión:** v{adv['version']}")
    h4.markdown(f"**Programa:** {adv['program_name']}")
    st.caption(f"Estado: ")
    _render_status_badge(adv["status"])
    st.write("")

    # ── Análisis IA ───────────────────────────────────────────────────────────
    ana = query("SELECT * FROM ai_analyses WHERE advance_id = ?", (adv_id,))

    if not ana:
        st.warning("Este avance aún no tiene análisis IA. Ejecuta el pipeline desde 'Revisión IA'.")
    else:
        a = ana[0]
        grade = a["grade"] or 0
        overall = a["overall_score"] or 0

        # Métricas principales
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Nota", f"{grade:.1f}/20")
        m2.metric("Estructura", f"{a['structure_score']:.0f}%")
        m3.metric("Contenido", f"{a['content_score']:.0f}%")
        m4.metric("Forma", f"{a['form_score']:.0f}%")
        m5.metric("Originalidad", f"{a['originality_score']:.0f}%")

        # Resumen IA
        st.markdown("#### Resumen IA")
        st.info(a["executive_summary"] or "_Sin resumen disponible._")

        # ── Cargar datos para pestañas ────────────────────────────────────────
        findings = query(
            "SELECT * FROM findings WHERE analysis_id = ? ORDER BY "
            "CASE severity WHEN 'Crítico' THEN 1 WHEN 'Mayor' THEN 2 "
            "WHEN 'Advertencia' THEN 3 WHEN 'Menor' THEN 4 ELSE 5 END",
            (a["id"],),
        )
        sims = query(
            """SELECT pr.*, av.title AS compared_title
               FROM plagiarism_results pr
               LEFT JOIN advances av ON av.id = pr.compared_advance_id
               WHERE pr.advance_id = ?
               ORDER BY pr.similarity DESC""",
            (adv_id,),
        )
        cites = query("SELECT * FROM citations WHERE advance_id = ? ORDER BY id", (adv_id,))

        # ── Pestañas ──────────────────────────────────────────────────────────
        tab_findings, tab_plagio, tab_refs = st.tabs([
            f"Hallazgos ({len(findings)})",
            f"Plagio ({len(sims)})",
            f"Referencias ({len(cites)})",
        ])

        # ── Hallazgos ─────────────────────────────────────────────────────────
        with tab_findings:
            if not findings:
                st.success("No se encontraron hallazgos para este avance.")
            for f in findings:
                color = SEVERITY_COLORS.get(f["severity"], "#9e9e9e")
                badge = (
                    f'<span style="background:{color};color:#fff;padding:3px 10px;'
                    f'border-radius:12px;font-size:12px;font-weight:bold">'
                    f'{f["severity"]}</span>'
                )
                with st.expander(
                    f"[{f['severity']}] {f['section_ref']} — {f['type']}",
                    expanded=f["severity"] == "Crítico",
                ):
                    st.markdown(badge, unsafe_allow_html=True)
                    st.markdown(f"**Sección:** {f['section_ref']}")
                    st.markdown(f"**Descripción:** {f['description']}")
                    st.markdown(f"**Corrección:** {f['correction_steps']}")
                    st.markdown(f"**Ejemplo de mejora:** {f['example_improvement']}")
                    st.markdown(f"**Recomendación:** {f['recommendation']}")

        # ── Plagio ────────────────────────────────────────────────────────────
        with tab_plagio:
            if not sims:
                st.info("No se realizó verificación de similitud para este avance.")
            else:
                max_sim = max(s["similarity"] for s in sims)
                risk = "Alto" if max_sim > 35 else "Moderado" if max_sim > 20 else "Bajo"
                risk_color = "#f44336" if max_sim > 35 else "#ff9800" if max_sim > 20 else "#4caf50"
                r1, r2 = st.columns(2)
                r1.metric("Similitud máxima detectada", f"{max_sim:.1f}%")
                r2.markdown(
                    f'<span style="background:{risk_color};color:#fff;padding:6px 16px;'
                    f'border-radius:20px;font-size:14px;font-weight:bold">'
                    f'Riesgo {risk}</span>',
                    unsafe_allow_html=True,
                )
                st.progress(max_sim / 100)
                st.markdown("---")
                st.markdown(f"**Coincidencias detectadas ({len(sims)})**")
                for s in sims:
                    sim_val = s["similarity"]
                    s_risk = "Alto" if sim_val > 35 else "Moderado" if sim_val > 20 else "Bajo"
                    s_color = "#f44336" if sim_val > 35 else "#ff9800" if sim_val > 20 else "#4caf50"
                    source_label = s["compared_title"] or s["section_ref"] or "Fuente externa"
                    with st.expander(f"Similitud {sim_val:.1f}% — {source_label}"):
                        c1, c2 = st.columns(2)
                        c1.markdown(f"**Nivel de riesgo:** {s_risk}")
                        c2.markdown(f"**Fuente:** {s['status'] or '—'}")
                        st.markdown(
                            f'<div style="background:{s_color}22;border-left:4px solid {s_color};'
                            f'padding:8px 12px;border-radius:4px">'
                            f'Similitud: <strong>{sim_val:.1f}%</strong> con '
                            f'<em>{source_label}</em>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.caption(f"Registrado: {s['created_at']}")

        # ── Referencias ───────────────────────────────────────────────────────
        with tab_refs:
            if not cites:
                st.info("No se validaron referencias para este avance.")
            else:
                verified = sum(1 for c in cites if c["status"] in ("Con DOI", "Pendiente"))
                not_found = sum(1 for c in cites if c["status"] == "No encontrada")
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("Total referencias", len(cites))
                rc2.metric("Verificadas / Con DOI", verified)
                rc3.metric("No encontradas", not_found)
                st.markdown("---")
                for c in cites:
                    if c["status"] in ("Con DOI",):
                        icon, color = "✅", "#4caf50"
                    elif c["status"] == "No encontrada":
                        icon, color = "❌", "#f44336"
                    else:
                        icon, color = "⚠️", "#ff9800"
                    with st.expander(f"{icon} {(c['raw_reference'] or '')[:90]}…"):
                        st.markdown(
                            f'<span style="background:{color};color:#fff;padding:3px 10px;'
                            f'border-radius:12px;font-size:12px">{c["status"]}</span>',
                            unsafe_allow_html=True,
                        )
                        if c["authors"]:
                            st.markdown(f"**Autor(es):** {c['authors']}")
                        if c["year"]:
                            st.markdown(f"**Año:** {c['year']}")
                        if c["doi"]:
                            st.markdown(f"**DOI:** `{c['doi']}`")
                        if c["suggestion"]:
                            st.markdown(f"**Sugerencia:** {c['suggestion']}")
                        st.caption(f"Fuente: {c['source'] or '—'}")


if auth():
    page = sidebar()
    if page == "Dashboard":            dashboard()
    elif page == "Avances de Tesis":   avances_tesis()
    elif page == "Cargar avance":      cargar_avance()
    elif page == "Revisión IA":        revision_ia()
    elif page == "Revisión humana":    revision_humana()
    elif page == "Revisión por lotes": revision_lotes()
    elif page == "Plantillas":         plantillas()
    elif page == "Usuarios y ORCID":   usuarios_orcid()
    elif page == "Estadísticas":       estadisticas()
    elif page == "Reportes":           reportes()
    elif page == "App móvil":          app_movil()
    elif page == "Auditoría":          auditoria()
    elif page == "Configuración":      configuracion()

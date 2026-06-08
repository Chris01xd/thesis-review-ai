import json
import os
from datetime import datetime
import bcrypt
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = os.getenv("DB_PATH", os.path.join("data", "thesis_review.db"))
USE_PG = bool(DATABASE_URL)

# Flag de fallback: se activa si PostgreSQL falla al primer intento
_PG_FAILED = False


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def _sqlite_connect():
    import sqlite3
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def connect():
    global _PG_FAILED

    if USE_PG and not _PG_FAILED:
        try:
            import psycopg2
            import psycopg2.extras
            url = DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            conn = psycopg2.connect(
                url,
                cursor_factory=psycopg2.extras.RealDictCursor,
                connect_timeout=5,
            )
            conn.autocommit = False
            return conn
        except Exception as e:
            print(f"[database] PostgreSQL no disponible ({e}), usando SQLite como fallback.")
            _PG_FAILED = True

    return _sqlite_connect()


def _to_pg(sql: str) -> str:
    return sql.replace("?", "%s")


def query(sql, params=()):
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(_to_pg(sql) if USE_PG else sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def execute(sql, params=()):
    conn = connect()
    try:
        cur = conn.cursor()

        if USE_PG:
            pg_sql = _to_pg(sql)

            if sql.strip().upper().startswith("INSERT") and "RETURNING" not in sql.upper():
                pg_sql = pg_sql.rstrip().rstrip(";") + " RETURNING id"

            cur.execute(pg_sql, params)

            if sql.strip().upper().startswith("INSERT"):
                result = cur.fetchone()
                last = result["id"] if result else None
            else:
                last = None

        else:
            cur.execute(sql, params)
            last = cur.lastrowid

        conn.commit()
        return last

    finally:
        conn.close()


def log(user_id, action, entity=None, entity_id=None, metadata=None):
    execute(
        "INSERT INTO audit_logs(user_id,action,entity,entity_id,metadata,created_at) VALUES (?,?,?,?,?,?)",
        (
            user_id,
            action,
            entity,
            entity_id,
            json.dumps(metadata or {}, ensure_ascii=False),
            now(),
        ),
    )


_TABLES_SQLITE = """
CREATE TABLE IF NOT EXISTS programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    program_id INTEGER,
    advisor_id INTEGER,
    orcid_id TEXT,
    affiliation TEXT,
    expertise TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(program_id) REFERENCES programs(id),
    FOREIGN KEY(advisor_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    content TEXT NOT NULL,
    expected_sections TEXT NOT NULL,
    rubric_json TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(program_id) REFERENCES programs(id)
);

CREATE TABLE IF NOT EXISTS advances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    advisor_id INTEGER,
    program_id INTEGER NOT NULL,
    template_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    advance_type TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    filename TEXT,
    file_path TEXT,
    file_type TEXT,
    text_content TEXT,
    page_count INTEGER,
    status TEXT DEFAULT 'Pendiente',
    created_at TEXT NOT NULL,
    FOREIGN KEY(student_id) REFERENCES users(id),
    FOREIGN KEY(advisor_id) REFERENCES users(id),
    FOREIGN KEY(program_id) REFERENCES programs(id),
    FOREIGN KEY(template_id) REFERENCES templates(id)
);

CREATE TABLE IF NOT EXISTS ai_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advance_id INTEGER NOT NULL UNIQUE,
    structure_score REAL,
    content_score REAL,
    form_score REAL,
    originality_score REAL,
    overall_score REAL,
    grade REAL,
    executive_summary TEXT,
    section_comparison TEXT,
    model_used TEXT,
    processing_ms INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(advance_id) REFERENCES advances(id)
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    type TEXT,
    section_ref TEXT,
    page_ref INTEGER,
    severity TEXT,
    description TEXT,
    correction_steps TEXT,
    example_improvement TEXT,
    recommendation TEXT,
    human_action TEXT DEFAULT 'Pendiente',
    human_comment TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(analysis_id) REFERENCES ai_analyses(id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advance_id INTEGER NOT NULL UNIQUE,
    reviewer_id INTEGER NOT NULL,
    final_grade REAL,
    human_comment TEXT,
    status TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plagiarism_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advance_id INTEGER NOT NULL,
    compared_advance_id INTEGER,
    similarity REAL,
    section_ref TEXT,
    status TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advance_id INTEGER NOT NULL,
    raw_reference TEXT,
    title TEXT,
    authors TEXT,
    year TEXT,
    doi TEXT,
    status TEXT,
    source TEXT,
    suggestion TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    read_status INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id INTEGER,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    advance_id INTEGER,
    status TEXT NOT NULL,
    result TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT
);
"""


_TABLES_PG = [
    """
    CREATE TABLE IF NOT EXISTS programs (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        program_id INTEGER,
        advisor_id INTEGER,
        orcid_id TEXT,
        affiliation TEXT,
        expertise TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS templates (
        id SERIAL PRIMARY KEY,
        program_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        version TEXT NOT NULL,
        content TEXT NOT NULL,
        expected_sections TEXT NOT NULL,
        rubric_json TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS advances (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL,
        advisor_id INTEGER,
        program_id INTEGER NOT NULL,
        template_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        advance_type TEXT NOT NULL,
        version INTEGER DEFAULT 1,
        filename TEXT,
        file_path TEXT,
        file_type TEXT,
        text_content TEXT,
        page_count INTEGER,
        status TEXT DEFAULT 'Pendiente',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_analyses (
        id SERIAL PRIMARY KEY,
        advance_id INTEGER NOT NULL UNIQUE,
        structure_score FLOAT,
        content_score FLOAT,
        form_score FLOAT,
        originality_score FLOAT,
        overall_score FLOAT,
        grade FLOAT,
        executive_summary TEXT,
        section_comparison TEXT,
        model_used TEXT,
        processing_ms INTEGER,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS findings (
        id SERIAL PRIMARY KEY,
        analysis_id INTEGER NOT NULL,
        type TEXT,
        section_ref TEXT,
        page_ref INTEGER,
        severity TEXT,
        description TEXT,
        correction_steps TEXT,
        example_improvement TEXT,
        recommendation TEXT,
        human_action TEXT DEFAULT 'Pendiente',
        human_comment TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reviews (
        id SERIAL PRIMARY KEY,
        advance_id INTEGER NOT NULL UNIQUE,
        reviewer_id INTEGER NOT NULL,
        final_grade FLOAT,
        human_comment TEXT,
        status TEXT,
        reviewed_at TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plagiarism_results (
        id SERIAL PRIMARY KEY,
        advance_id INTEGER NOT NULL,
        compared_advance_id INTEGER,
        similarity FLOAT,
        section_ref TEXT,
        status TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS citations (
        id SERIAL PRIMARY KEY,
        advance_id INTEGER NOT NULL,
        raw_reference TEXT,
        title TEXT,
        authors TEXT,
        year TEXT,
        doi TEXT,
        status TEXT,
        source TEXT,
        suggestion TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        read_status INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity TEXT,
        entity_id INTEGER,
        metadata TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_jobs (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        advance_id INTEGER,
        status TEXT NOT NULL,
        result TEXT,
        created_at TEXT NOT NULL,
        finished_at TEXT
    )
    """,
]


def init_db():
    conn = connect()

    try:
        cur = conn.cursor()

        if USE_PG:
            for stmt in _TABLES_PG:
                cur.execute(stmt)

            conn.commit()

            try:
                cur.execute("ALTER TABLE ai_analyses ADD COLUMN section_comparison TEXT")
                conn.commit()
            except Exception:
                conn.rollback()

        else:
            conn.executescript(_TABLES_SQLITE)
            conn.commit()

            try:
                conn.execute("ALTER TABLE ai_analyses ADD COLUMN section_comparison TEXT")
                conn.commit()
            except Exception:
                pass

    finally:
        conn.close()

    seed_data()


def seed_data():
    rows = query("SELECT COUNT(*) AS c FROM programs")

    if rows and rows[0]["c"] > 0:
        return

    execute(
        "INSERT INTO programs(name, created_at) VALUES (?,?)",
        ("Maestría en Educación", now()),
    )

    execute(
        "INSERT INTO programs(name, created_at) VALUES (?,?)",
        ("Maestría en Ingeniería", now()),
    )

    hp = hash_password("123456")

    users = [
        (
            "Administrador General",
            "admin@tesis.edu",
            "ADMIN",
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "María Castillo",
            "coordinador@tesis.edu",
            "COORDINATOR",
            1,
            None,
            None,
            None,
            None,
        ),
        (
            "Dr. Pérez",
            "asesor@tesis.edu",
            "ADVISOR",
            1,
            None,
            "0000-0002-1825-0097",
            "Universidad Demo",
            "educación, metodología de investigación, evaluación",
        ),
        (
            "Torres Kevin",
            "estudiante@tesis.edu",
            "STUDENT",
            1,
            3,
            None,
            None,
            None,
        ),
    ]

    for name, email, role, program_id, advisor_id, orcid, aff, exp in users:
        execute(
            """
            INSERT INTO users(
                name,email,password_hash,role,program_id,advisor_id,
                orcid_id,affiliation,expertise,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                name,
                email,
                hp,
                role,
                program_id,
                advisor_id,
                orcid,
                aff,
                exp,
                now(),
            ),
        )

    expected = "|".join(
        [
            "Carátula",
            "Índice",
            "Resumen",
            "Introducción",
            "Planteamiento del problema",
            "Objetivos",
            "Justificación",
            "Marco teórico",
            "Antecedentes",
            "Hipótesis",
            "Metodología",
            "Resultados",
            "Discusión",
            "Conclusiones",
            "Referencias",
        ]
    )

    rubric = json.dumps(
        {
            "estructura": 30,
            "contenido": 40,
            "forma": 20,
            "originalidad": 10,
            "nota_maxima": 20,
            "umbral_alerta": 65,
        },
        ensure_ascii=False,
    )

    template_text = (
        "Documento patrón institucional de tesis. Estructura obligatoria: "
        "Carátula, Índice, Resumen, Introducción, Planteamiento del problema, "
        "Objetivos, Justificación, Marco teórico, Antecedentes, Hipótesis, "
        "Metodología, Resultados, Discusión, Conclusiones y Referencias. "
        "Criterios: lenguaje académico, coherencia, citas APA 7ma edición."
    )

    for pid, name in [
        (1, "Patrón Maestría Educación"),
        (2, "Patrón Maestría Ingeniería"),
    ]:
        execute(
            """
            INSERT INTO templates(
                program_id,name,version,content,expected_sections,
                rubric_json,active,created_at
            ) VALUES (?,?,?,?,?,?,1,?)
            """,
            (
                pid,
                name,
                "v1.0",
                template_text,
                expected,
                rubric,
                now(),
            ),
        )

    expected_proj = "|".join(
        [
            "Carátula",
            "Jurado dictaminador",
            "Dedicatoria",
            "Agradecimiento",
            "Índice",
            "Lista de figuras",
            "Lista de tablas",
            "Presentación",
            "Resumen",
            "Abstract",
            "Introducción",
            "Planteamiento del problema",
            "Antecedentes",
            "Marco teórico",
            "Justificación",
            "Formulación del problema",
            "Hipótesis",
            "Objetivos",
            "Limitaciones",
            "Referencias",
            "Matriz de consistencia",
            "Matriz de operacionalización",
            "Anexos",
        ]
    )

    execute(
        """
        INSERT INTO templates(
            program_id,name,version,content,expected_sections,
            rubric_json,active,created_at
        ) VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            2,
            "Patrón Proyecto de Tesis Pregrado / Capítulo I",
            "v1.0",
            "Plantilla para proyecto de tesis o avance de Capítulo I.",
            expected_proj,
            rubric,
            1,
            now(),
        ),
    )
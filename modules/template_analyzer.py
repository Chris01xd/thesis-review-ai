"""
modules/template_analyzer.py
Analiza plantillas DOCX/PDF para extraer su estructura y usarla como modelo.
"""
import re

# ── Detección de tipo de tabla ────────────────────────────────────────────────

_TABLE_TYPE_KEYWORDS = {
    "consistencia": ["problema", "objetivo", "hipotesis", "variable", "indicador",
                     "instrumento", "fuente", "metodologia", "diseño", "tipo"],
    "operacionalizacion": ["variable", "definicion", "dimension", "indicador",
                           "escala", "medicion", "items", "item", "instrumento"],
    "cronograma": ["actividad", "mes", "semana", "enero", "febrero", "marzo",
                   "abril", "mayo", "junio", "julio", "agosto", "setiembre",
                   "octubre", "noviembre", "diciembre", "periodo", "plazo"],
    "presupuesto": ["descripcion", "cantidad", "precio", "costo", "total",
                    "subtotal", "unidad", "monto", "inversion", "recurso"],
    "poblacion": ["institucion", "grado", "total", "poblacion", "muestra",
                  "seccion", "nivel", "numero", "estrato"],
    "estadisticos": ["media", "desviacion", "porcentaje", "frecuencia",
                     "n", "min", "max", "p-valor", "valor"],
}

# Secciones de portada que NO deben aparecer como contenido
_COVER_KEYWORDS = {
    'universidad', 'facultad', 'escuela', 'carrera', 'departamento',
    'proyecto de tesis', 'tesis para optar', 'trabajo de investigacion',
    'autor(es)', 'autores', 'asesor:', 'asesor :', 'linea de investigacion',
    'jurado dictaminador', 'jurado:', 'tribunal', 'ciudad', '— peru', '- peru',
    'titulo:', 'proyecto de investigacion cientifica', 'proyecto de tesis pregrado',
    'formato:', '(nombre de la', 'organización sincrónica', 'organización diacronica',
    'nombre de la institucion',
}

# Secciones que deben existir en la lista pero sin cuerpo de texto generado
_SKIP_CONTENT_KEYWORDS = {
    'indice general', 'tabla de contenido', 'contenido', 'indice de figuras',
    'lista de figuras', 'lista de tablas', 'indice de tablas',
    'referencias bibliograficas', 'referencias:', 'referencias',
    'anexos', 'anexo',  # el builder de anexos los maneja individualmente
}


def _normalize(text: str) -> str:
    text = text.lower()
    for src, dst in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n')]:
        text = text.replace(src, dst)
    return text


def _is_cover_section(text: str) -> bool:
    n = _normalize(text.strip())
    return any(kw in n for kw in _COVER_KEYWORDS)


def _detect_table_type(headers: list, title: str = "") -> str:
    text = _normalize(" ".join(headers + [title]))
    scores = {}
    for ttype, keywords in _TABLE_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[ttype] = score
    if scores:
        return max(scores, key=scores.get)
    return "generic"


# ── Análisis DOCX ─────────────────────────────────────────────────────────────

def _analyze_docx(file_path: str) -> dict:
    from docx import Document
    doc = Document(file_path)

    sections = []
    tables_info = []
    last_real_section_idx = -1   # índice del último heading real añadido

    # Patrones de texto que indican heading aunque el estilo no lo sea
    _CHAPTER_PAT = re.compile(
        r'^(cap[ií]tulo\s+[ivxIVX\d]+[\.:].{0,80}|'
        r'anexo\s+\d+[\.:].{0,80}|'
        r'\d+\.?\s{1,4}[A-ZÁÉÍÓÚÑ\w].{3,80}|'
        r'[IVX]+\.\s+[A-ZÁÉÍÓÚÑ].{3,60})$',
        re.IGNORECASE | re.UNICODE,
    )

    def _is_heading_style(style_name: str) -> tuple:
        """Devuelve (True, level) si el estilo es de tipo heading."""
        sn = style_name.lower()
        for key in ('heading 1', 'título 1', 'titulo 1', 'heading1'):
            if key in sn: return True, 1
        for key in ('heading 2', 'título 2', 'titulo 2', 'heading2'):
            if key in sn: return True, 2
        for key in ('heading 3', 'título 3', 'titulo 3', 'heading3'):
            if key in sn: return True, 3
        return False, 0

    def _infer_level(text: str) -> int:
        n = _normalize(text.strip())
        if re.match(r'^(cap[ií]tulo|anexo)\s+', n):
            return 1
        if re.match(r'^\d+\s{2,}', text):   # "1    Introducción"
            return 1
        if re.match(r'^\d+\.\d+\s+', text): # "2.1 Algo"
            return 2
        if re.match(r'^\d+\.\d+\.\d+\s+', text): # "2.1.1 Algo"
            return 3
        if re.match(r'^[IVX]+\.\s+', text):
            return 1
        return 2

    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        text = para.text.strip()
        if not text:
            continue

        is_heading, level = _is_heading_style(style_name)

        if is_heading:
            if not _is_cover_section(text):
                sections.append({"level": level, "title": text, "content_preview": ""})
                last_real_section_idx = len(sections) - 1
            continue

        # Detectar por texto: ALL CAPS corto
        if text.isupper() and 5 < len(text) < 140:
            if _is_cover_section(text):
                continue
            level = _infer_level(text)
            sections.append({"level": level, "title": text, "content_preview": ""})
            last_real_section_idx = len(sections) - 1
            continue

        # Detectar por patrón: "CAPÍTULO I:", "ANEXO 2:", "1  Introducción", etc.
        if _CHAPTER_PAT.match(text) and len(text) < 140:
            if _is_cover_section(text):
                continue
            level = _infer_level(text)
            # Evitar duplicados con lo ya capturado
            if not sections or _normalize(sections[-1]['title']) != _normalize(text):
                sections.append({"level": level, "title": text, "content_preview": ""})
                last_real_section_idx = len(sections) - 1
            continue

        # Detectar por formato: bold y corto (sub-heading probable)
        is_bold_short = (
            len(text) < 100 and
            para.runs and
            all(r.bold for r in para.runs if r.text.strip())
        )
        if is_bold_short and not _is_cover_section(text):
            sections.append({"level": 3, "title": text, "content_preview": ""})
            last_real_section_idx = len(sections) - 1
            continue

        # Párrafo de contenido → asignar como preview del último heading
        if last_real_section_idx >= 0 and not sections[last_real_section_idx]["content_preview"]:
            sections[last_real_section_idx]["content_preview"] = text[:200]

    for table in doc.tables:
        rows_count = len(table.rows)
        headers = []
        if rows_count > 0:
            for cell in table.rows[0].cells:
                headers.append(cell.text.strip())
        table_type = _detect_table_type(headers)
        tables_info.append({
            "title": "",
            "headers": [h for h in headers if h],
            "rows": rows_count,
            "cols": len(table.columns),
            "type": table_type,
        })

    return {
        "sections": sections,
        "tables": tables_info,
        "has_cover": _has_cover(doc),
        "has_abstract": _has_section(sections, ["resumen", "abstract"]),
        "doc_type_hint": _detect_doc_type(sections, tables_info),
    }


def _has_cover(doc) -> bool:
    """Detecta si el DOCX tiene portada revisando los primeros 15 párrafos."""
    cover_kw = {'universidad', 'facultad', 'escuela', 'proyecto de tesis',
                'trabajo de investigacion', 'tesis para optar'}
    count = 0
    for para in list(doc.paragraphs)[:15]:
        n = _normalize(para.text)
        if any(k in n for k in cover_kw):
            count += 1
    return count >= 2


# ── Análisis PDF ──────────────────────────────────────────────────────────────

def _analyze_pdf(file_path: str) -> dict:
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)

    all_text = ""
    for page in reader.pages:
        all_text += (page.extract_text() or "") + "\n"

    sections = _extract_headings_from_text(all_text)

    return {
        "sections": sections,
        "tables": [],
        "has_cover": False,
        "has_abstract": _has_section(sections, ["resumen", "abstract"]),
        "doc_type_hint": _detect_doc_type(sections, []),
    }


def _extract_headings_from_text(text: str) -> list:
    lines = text.split('\n')
    sections = []

    heading_patterns = [
        (1, r'^(CAP[IÍ]TULO\s+[IVX\d]+.{0,60})$'),
        (1, r'^(ANEXO\s+\d+.{0,60})$'),
        (1, r'^([IVX]+\.\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,50})$'),
        (1, r'^(\d+\s{2,}[A-ZÁÉÍÓÚÑ].{5,60})$'),
        (2, r'^(\d+\.\d+\s+.{5,80})$'),
        (3, r'^(\d+\.\d+\.\d+\s+.{5,80})$'),
    ]

    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 5 or _is_cover_section(line):
            continue
        for level, pattern in heading_patterns:
            if re.match(pattern, line, re.UNICODE):
                preview = " ".join(lines[i+1:i+4]).strip()[:200]
                sections.append({"level": level, "title": line, "content_preview": preview})
                break
        else:
            if line.isupper() and 5 < len(line) < 120 and not _is_cover_section(line):
                preview = " ".join(lines[i+1:i+4]).strip()[:200]
                sections.append({"level": 2, "title": line, "content_preview": preview})

    return sections


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_section(sections: list, keywords: list) -> bool:
    for s in sections:
        norm = _normalize(s["title"])
        if any(kw in norm for kw in keywords):
            return True
    return False


def _detect_doc_type(sections: list, tables: list) -> str:
    all_titles = " ".join(_normalize(s["title"]) for s in sections)
    table_types = {t.get("type", "") for t in tables}

    # Señales fuertes de tesis/proyecto (capítulos numerados, anexos)
    has_chapters = any(kw in all_titles for kw in ["capitulo i", "capitulo ii", "capitulo iii",
                                                     "capitulo iv", "capitulo v"])
    has_annexes  = "anexo" in all_titles

    # Señales fuertes de artículo (sin capítulos, con secciones propias de artículo)
    article_exclusive = any(kw in all_titles for kw in [
        "materiales y metodo", "resultados y discusion", "resultados de la revision",
        "conflicto de interes", "contribucion de autoria",
    ])

    if article_exclusive and not has_chapters:
        return "articulo"

    if has_chapters or has_annexes:
        # Distinguir tesis (5 caps) de proyecto (3 caps + admin)
        if any(kw in all_titles for kw in ["aspectos administrativos", "cronograma",
                                            "presupuesto", "planteamiento"]):
            return "proyecto_tesis"
        if "presupuesto" in table_types or "cronograma" in table_types:
            return "proyecto_tesis"
        if any(kw in all_titles for kw in ["resultado", "discusion", "hallazgo", "capitulo iv"]):
            return "tesis"
        return "proyecto_tesis"

    # Sin capítulos y sin señales de artículo → inferir por tablas
    if "presupuesto" in table_types or "cronograma" in table_types:
        return "proyecto_tesis"

    # Abstract/keywords solos (sin capítulos) → artículo
    if any(kw in all_titles for kw in ["abstract", "keywords", "palabras clave"]):
        return "articulo"

    return "proyecto_tesis"


def _empty_structure() -> dict:
    return {
        "sections": [],
        "tables": [],
        "has_cover": False,
        "has_abstract": False,
        "doc_type_hint": "proyecto_tesis",
    }


# ── Punto de entrada público ──────────────────────────────────────────────────

def analyze_template(file_path: str, file_type: str) -> dict:
    """
    Analiza una plantilla DOCX o PDF y devuelve su estructura.

    Returns dict con:
        sections      — lista de {level, title, content_preview}
        tables        — lista de {title, headers, rows, cols, type}
        has_cover     — bool
        has_abstract  — bool
        doc_type_hint — "tesis" | "proyecto_tesis" | "articulo"
    """
    file_type = file_type.lower().replace(".", "")
    try:
        if file_type == "docx":
            return _analyze_docx(file_path)
        elif file_type == "pdf":
            return _analyze_pdf(file_path)
    except Exception as e:
        print(f"[template_analyzer] Error analizando plantilla: {e}")
    return _empty_structure()

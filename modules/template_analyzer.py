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


def _normalize(text: str) -> str:
    text = text.lower()
    for src, dst in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n')]:
        text = text.replace(src, dst)
    return text


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

    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        text = para.text.strip()
        if not text:
            continue

        if "Heading 1" in style_name:
            sections.append({"level": 1, "title": text, "content_preview": ""})
        elif "Heading 2" in style_name:
            sections.append({"level": 2, "title": text, "content_preview": ""})
        elif "Heading 3" in style_name:
            sections.append({"level": 3, "title": text, "content_preview": ""})
        else:
            is_bold_short = (
                len(text) < 100 and
                para.runs and
                all(r.bold for r in para.runs if r.text.strip())
            )
            if text.isupper() and 5 < len(text) < 120:
                sections.append({"level": 2, "title": text, "content_preview": ""})
            elif is_bold_short:
                sections.append({"level": 3, "title": text, "content_preview": ""})
            elif sections and not sections[-1]["content_preview"]:
                sections[-1]["content_preview"] = text[:200]

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
        "has_cover": _has_section(sections, ["caratula", "portada", "titulo", "cover"]),
        "has_abstract": _has_section(sections, ["resumen", "abstract"]),
        "doc_type_hint": _detect_doc_type(sections, tables_info),
    }


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
        "has_cover": _has_section(sections, ["caratula", "portada", "titulo"]),
        "has_abstract": _has_section(sections, ["resumen", "abstract"]),
        "doc_type_hint": _detect_doc_type(sections, []),
    }


def _extract_headings_from_text(text: str) -> list:
    lines = text.split('\n')
    sections = []

    heading_patterns = [
        (1, r'^(CAP[IÍ]TULO\s+[IVX\d]+.{0,60})$'),
        (1, r'^([IVX]+\.\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,50})$'),
        (2, r'^(\d+\.\d+\s+.{5,80})$'),
        (3, r'^(\d+\.\d+\.\d+\s+.{5,80})$'),
    ]

    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 5:
            continue
        for level, pattern in heading_patterns:
            if re.match(pattern, line, re.UNICODE):
                preview = " ".join(lines[i+1:i+4]).strip()[:200]
                sections.append({"level": level, "title": line, "content_preview": preview})
                break
        else:
            if line.isupper() and 5 < len(line) < 120:
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

    if "presupuesto" in table_types or "cronograma" in table_types:
        if "resultado" not in all_titles and "discusion" not in all_titles:
            return "proyecto_tesis"

    if any(kw in all_titles for kw in ["resultado", "discusion", "hallazgo"]):
        return "tesis"
    if any(kw in all_titles for kw in ["proyecto", "aspectos admin"]):
        return "proyecto_tesis"
    if any(kw in all_titles for kw in ["abstract", "keywords", "materiales", "palabras clave"]):
        return "articulo"
    return "tesis"


def _empty_structure() -> dict:
    return {
        "sections": [],
        "tables": [],
        "has_cover": False,
        "has_abstract": False,
        "doc_type_hint": "tesis",
    }


# ── Punto de entrada público ──────────────────────────────────────────────────

def analyze_template(file_path: str, file_type: str) -> dict:
    """
    Analiza una plantilla DOCX o PDF y devuelve su estructura.

    Returns dict con:
        sections  — lista de {level, title, content_preview}
        tables    — lista de {title, headers, rows, cols, type}
        has_cover — bool
        has_abstract — bool
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


import re, time, json, os
from typing import Dict, List
from dotenv import load_dotenv
from .document_processing import detect_sections, estimate_academic_style, extract_references

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# OpenAI integration (opcional — fallback automático al motor local)
# ─────────────────────────────────────────────────────────────────────────────
def _try_openai_analysis(text: str, expected_sections: List[str], rubric: Dict, advance_type: str):
    """
    Intenta análisis con OpenAI GPT.
    Retorna el resultado en el mismo formato que el motor local, o None si falla.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import openai
    except ImportError:
        print("[ai_engine] Paquete 'openai' no instalado — usando motor local.")
        return None
    try:
        client = openai.OpenAI(api_key=api_key)
        model  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        text_trunc   = (text or "")[:7500]
        sections_str = ", ".join(expected_sections)
        max_grade    = rubric.get("nota_maxima", 20)

        system = (
            "Eres un evaluador académico experto en tesis universitarias latinoamericanas. "
            "Devuelve SIEMPRE un JSON válido con la estructura exacta solicitada, sin texto adicional."
        )
        user = f"""Evalúa el siguiente avance de tesis y devuelve ÚNICAMENTE este JSON:
{{
  "scores": {{"structure":<0-100>,"content":<0-100>,"form":<0-100>,"originality":<0-100>,"overall":<0-100>}},
  "grade": <0.0-{max_grade}>,
  "executiveSummary": "<resumen ejecutivo ≤ 300 palabras en español>",
  "findings": [
    {{"type":"<Estructura|Contenido|Forma|Citas|Sugerencia>","section_ref":"<sección>",
      "page_ref":null,"severity":"<Crítico|Mayor|Menor|Sugerencia>",
      "description":"<descripción>","correction_steps":"<pasos>",
      "example_improvement":"<ejemplo>","recommendation":"<recomendación>"}}
  ]
}}

Tipo de avance: {advance_type}
Secciones esperadas: {sections_str}
Rúbrica: estructura={rubric.get('estructura',30)}%, contenido={rubric.get('contenido',40)}%, \
forma={rubric.get('forma',20)}%, originalidad={rubric.get('originalidad',10)}%
overall = promedio ponderado | grade = (overall/100)×{max_grade}
Incluir entre 2 y 6 hallazgos accionables.

Documento:
{text_trunc}"""

        t0 = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2000,
        )
        result = json.loads(resp.choices[0].message.content)

        # Validar estructura mínima
        if not {"scores", "grade", "executiveSummary", "findings"}.issubset(result):
            return None

        result["processingMs"] = int((time.time() - t0) * 1000)
        result["modelUsed"]    = f"OpenAI {model}"

        # Compute section comparison locally (reliable, template-based)
        norm_text_local = normalize_text(text or "")
        advance_norm_local = normalize_text(advance_type)
        sc = []
        for sec in expected_sections:
            ok = section_present(sec, text or "", norm_text_local, advance_type)
            sec_key = normalize_text(sec)
            optional = (not ok
                        and ("capitulo 1" in advance_norm_local or "proyecto" in advance_norm_local or "avance" in advance_norm_local)
                        and sec_key in {normalize_text(s) for s in OPTIONAL_FOR_PROJECT})
            sc.append({"section": sec, "present": ok or optional, "optional": optional})
        result["sectionComparison"] = sc
        return result

    except Exception as exc:
        print(f"[ai_engine] OpenAI falló, usando motor local: {exc}")
        return None


def clamp(x, a=0, b=100):
    return max(a, min(b, x))

def normalize_text(s: str) -> str:
    s = (s or "").lower()
    trans = str.maketrans("áéíóúüñ", "aeiouun")
    s = s.translate(trans)
    s = re.sub(r"\s+", " ", s)
    return s

SECTION_ALIASES = {
    "carátula": ["universidad", "facultad", "escuela profesional", "proyecto de tesis", "autor", "asesor", "linea de investigacion"],
    "caratula": ["universidad", "facultad", "escuela profesional", "proyecto de tesis", "autor", "asesor", "linea de investigacion"],
    "índice": ["indice general", "indice", "lista de figuras", "lista de tablas"],
    "indice": ["indice general", "indice", "lista de figuras", "lista de tablas"],
    "resumen": ["resumen", "palabras clave"],
    "abstract": ["abstract", "keywords"],
    "introducción": ["capitulo i introduccion", "introduccion"],
    "introduccion": ["capitulo i introduccion", "introduccion"],
    "planteamiento del problema": ["planteamiento del problema", "problema central", "formulacion del problema", "problema que sirve de guia", "alto indice de desperdicio", "analisis causal identifica como problema"],
    "antecedentes": ["antecedentes", "ambito internacional", "a nivel nacional", "sharma", "chen y liu", "mamani y quispe", "torres y rios"],
    "marco teórico": ["marco teorico", "bases teoricas", "perspectiva conceptual", "teoria de", "lean supply chain", "economia circular", "sistemas de apoyo a la toma de decisiones"],
    "marco teorico": ["marco teorico", "bases teoricas", "perspectiva conceptual", "teoria de", "lean supply chain", "economia circular", "sistemas de apoyo a la toma de decisiones"],
    "objetivos": ["objetivo general", "objetivos especificos", "el objetivo general es", "los objetivos especificos son"],
    "objetivo general": ["objetivo general", "el objetivo general es"],
    "objetivos específicos": ["objetivos especificos", "los objetivos especificos son"],
    "objetivos especificos": ["objetivos especificos", "los objetivos especificos son"],
    "justificación": ["justificacion", "justificacion teorica", "justificacion practica", "justificacion metodologica"],
    "justificacion": ["justificacion", "justificacion teorica", "justificacion practica", "justificacion metodologica"],
    "hipótesis": ["hipotesis", "ha:", "h0:", "como respuesta provisional"],
    "hipotesis": ["hipotesis", "ha:", "h0:", "como respuesta provisional"],
    "metodología": ["metodologia", "diseno preexperimental", "preexperimental", "poblacion", "muestra", "instrumentos", "tecnicas", "kimball", "crisp-dm"],
    "metodologia": ["metodologia", "diseno preexperimental", "preexperimental", "poblacion", "muestra", "instrumentos", "tecnicas", "kimball", "crisp-dm"],
    "resultados": ["resultados", "se espera", "resultado esperado", "impacto"],
    "discusión": ["discusion"],
    "discusion": ["discusion"],
    "conclusiones": ["conclusiones"],
    "referencias": ["referencias bibliograficas", "referencias", "bibliografia", "doi.org"],
    "referencias bibliográficas": ["referencias bibliograficas", "referencias", "bibliografia", "doi.org"],
    "matriz de consistencia": ["matriz de consistencia"],
    "matriz de operacionalización": ["matriz de operacionalizacion", "operacionalizacion de variables"],
    "anexos": ["anexo", "matriz de consistencia", "arbol de problemas", "arbol de objetivos"]
}

OPTIONAL_FOR_PROJECT = {"resultados", "discusión", "discusion", "conclusiones"}

def section_present(section: str, raw_text: str, norm_text: str, advance_type: str):
    sec_norm = normalize_text(section)
    aliases = SECTION_ALIASES.get(section.lower(), []) + SECTION_ALIASES.get(sec_norm, [])
    aliases = list(dict.fromkeys([section, sec_norm] + aliases))
    for alias in aliases:
        if normalize_text(alias) in norm_text:
            return True

    # Para carátula, validar por combinación de metadatos aunque no exista la palabra literal.
    if sec_norm in ["caratula"]:
        signals = ["universidad", "facultad", "escuela profesional", "autor", "asesor"]
        return sum(1 for s in signals if s in norm_text) >= 3

    return False

def local_agentic_analysis(text: str, expected_sections: List[str], rubric: Dict, advance_type: str):
    """
    Motor IA: intenta OpenAI primero si está configurado; si no, usa reglas locales v4.
    """
    openai_result = _try_openai_analysis(text, expected_sections, rubric, advance_type)
    if openai_result:
        return openai_result

    # ── Motor local v4 ────────────────────────────────────────────────────────
    start = time.time()
    raw_text = text or ""
    norm_text = normalize_text(raw_text)
    advance_norm = normalize_text(advance_type)

    missing = []
    present = []
    optional_not_penalized = []

    for sec in expected_sections:
        sec_key = normalize_text(sec)
        ok = section_present(sec, raw_text, norm_text, advance_type)

        # En proyectos/avances de tesis, resultados, discusión y conclusiones pueden no exigirse todavía.
        if not ok and ("capitulo 1" in advance_norm or "proyecto" in advance_norm or "avance" in advance_norm):
            if sec_key in {normalize_text(s) for s in OPTIONAL_FOR_PROJECT}:
                optional_not_penalized.append(sec.lower())
                ok = True

        if ok:
            present.append(sec.lower())
        else:
            missing.append(sec.lower())

    structure_score = clamp((len(present) / max(1, len(expected_sections))) * 100)

    length_score = clamp(len(re.findall(r"\w+", raw_text)) / 18)
    academic_score = estimate_academic_style(raw_text)
    refs = extract_references(raw_text)
    citation_score = clamp(len(refs) * 12)
    coherence_terms = ["problema", "objetivo", "metodologia", "resultado", "conclusion", "variable"]
    coherence_score = clamp(sum(1 for t in coherence_terms if t in norm_text) / len(coherence_terms) * 100)
    content_score = clamp(length_score*0.25 + academic_score*0.25 + citation_score*0.25 + coherence_score*0.25)

    form_penalties = 0
    if not refs: form_penalties += 25
    if len(raw_text) < 1500: form_penalties += 25
    if not re.search(r"\(\w+.*?,\s*(19|20)\d{2}\)", raw_text): form_penalties += 20
    if len(re.findall(r"[.!?]", raw_text)) < 15: form_penalties += 10
    form_score = clamp(100 - form_penalties)

    # Calidad interna, no IA.
    repeated = 0
    sentences = [s.strip().lower() for s in re.split(r"[.!?]", raw_text) if len(s.strip()) > 50]
    seen = set()
    for s in sentences:
        key = re.sub(r"\W+", " ", s)[:120]
        if key in seen:
            repeated += 1
        seen.add(key)
    originality_score = clamp(100 - repeated*4)

    overall = clamp(
        structure_score * rubric.get("estructura", 30)/100 +
        content_score * rubric.get("contenido", 40)/100 +
        form_score * rubric.get("forma", 20)/100 +
        originality_score * rubric.get("originalidad", 10)/100
    )
    grade = round((overall/100) * rubric.get("nota_maxima", 20), 2)

    findings = []
    for sec in missing[:8]:
        findings.append({
            "type": "Estructura",
            "section_ref": sec.title(),
            "page_ref": None,
            "severity": "Crítico" if normalize_text(sec) in ["objetivos","metodologia","referencias"] else "Mayor",
            "description": f"No se identificó la sección obligatoria o su equivalente académico '{sec.title()}' según el documento patrón.",
            "correction_steps": f"Verificar si '{sec.title()}' debe aparecer como encabezado independiente o si la plantilla permite desarrollarlo dentro de otra sección.",
            "example_improvement": f"{sec.title()}: incluir un subtítulo explícito o desarrollar el contenido con denominación equivalente para que el sistema y el asesor lo identifiquen con claridad.",
            "recommendation": "Si se trata de proyecto de tesis o Capítulo I, usar una plantilla de evaluación específica y no una plantilla de tesis completa."
        })

    if optional_not_penalized:
        findings.append({
            "type": "Alcance",
            "section_ref": "Tipo de avance",
            "page_ref": None,
            "severity": "Sugerencia",
            "description": "Algunas secciones como resultados, discusión o conclusiones se consideran opcionales para proyecto de tesis o Capítulo I.",
            "correction_steps": "Configurar el tipo de avance como 'Proyecto de tesis' o usar una plantilla institucional específica.",
            "example_improvement": "Para Capítulo I, priorizar introducción, problema, antecedentes, bases teóricas, justificación, hipótesis, objetivos y limitaciones.",
            "recommendation": "No evaluar un proyecto de tesis con una rúbrica de tesis completa."
        })

    if not refs:
        findings.append({
            "type": "Citas",
            "section_ref": "Referencias",
            "page_ref": None,
            "severity": "Mayor",
            "description": "No se detectaron referencias bibliográficas suficientes o reconocibles.",
            "correction_steps": "Incorporar citas en el cuerpo del texto y una lista de referencias en formato APA 7.ª edición.",
            "example_improvement": "Apellido, A. A. (2022). Título del artículo. Nombre de la Revista, 10(2), 15-30. https://doi.org/...",
            "recommendation": "Usar fuentes académicas verificables y recientes."
        })

    if content_score < 65:
        findings.append({
            "type": "Contenido",
            "section_ref": "Coherencia general",
            "page_ref": None,
            "severity": "Mayor",
            "description": "El desarrollo del contenido parece insuficiente o poco articulado con los criterios académicos esperados.",
            "correction_steps": "Fortalecer la relación entre problema, objetivos, hipótesis, metodología y resultados esperados.",
            "example_improvement": "El objetivo general debe derivarse directamente del problema principal y orientar la selección del diseño metodológico.",
            "recommendation": "Ampliar la argumentación y vincular cada sección con evidencia bibliográfica."
        })

    if form_score < 75:
        findings.append({
            "type": "Forma",
            "section_ref": "Redacción y formato",
            "page_ref": None,
            "severity": "Menor",
            "description": "Se identifican posibles debilidades de formato académico, extensión o citación.",
            "correction_steps": "Revisar normas APA, numeración, títulos, subtítulos, citas y consistencia de redacción.",
            "example_improvement": "Según autores recientes (2021), la redacción académica debe sostener una secuencia lógica y verificable.",
            "recommendation": "Realizar una revisión final de estilo antes de la evaluación humana."
        })

    if not findings:
        findings.append({
            "type": "Sugerencia",
            "section_ref": "Documento completo",
            "page_ref": None,
            "severity": "Sugerencia",
            "description": "El documento presenta cumplimiento general adecuado frente al patrón institucional.",
            "correction_steps": "Realizar una lectura final para mejorar precisión conceptual y consistencia de citas.",
            "example_improvement": "Profundizar la discusión contrastando los hallazgos con antecedentes nacionales e internacionales.",
            "recommendation": "Mantener la trazabilidad entre objetivos, resultados y conclusiones."
        })

    section_comparison = []
    for sec in expected_sections:
        sec_key = normalize_text(sec)
        is_optional = sec_key in {normalize_text(s) for s in optional_not_penalized}
        is_present = sec.lower() in present or is_optional
        section_comparison.append({"section": sec, "present": is_present, "optional": is_optional})

    summary = (
        f"El avance presenta un cumplimiento estimado de {overall:.1f}%. "
        f"La estructura alcanza {structure_score:.1f}%, el contenido {content_score:.1f}%, "
        f"la forma {form_score:.1f}% y la calidad interna {originality_score:.1f}%. "
        f"Se detectaron {len(missing)} secciones faltantes obligatorias y {len(findings)} hallazgos principales. "
        "La prioridad es revisar si el documento fue evaluado con la plantilla correcta según su tipo de avance."
    )
    return {
        "scores": {
            "structure": round(structure_score, 2),
            "content": round(content_score, 2),
            "form": round(form_score, 2),
            "originality": round(originality_score, 2),
            "overall": round(overall, 2)
        },
        "grade": grade,
        "executiveSummary": summary,
        "findings": findings,
        "sectionComparison": section_comparison,
        "processingMs": int((time.time()-start)*1000),
        "modelUsed": "Agente local académico v4 + detección tolerante por equivalencias"
    }

def agent_plan_for_document(text: str):
    return [
        "1. Extraer texto del documento.",
        "2. Detectar secciones y compararlas con el patrón institucional.",
        "3. Evaluar estructura, contenido, forma y originalidad.",
        "4. Extraer referencias bibliográficas.",
        "5. Comparar similitud con avances previos.",
        "6. Generar hallazgos accionables.",
        "7. Enviar resultados a revisión humana."
    ]

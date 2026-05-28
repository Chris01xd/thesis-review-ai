"""
modules/open_similarity.py
Verificación de similitud académica contra repositorios abiertos y documentos internos.

Fuentes consultadas:
  - OpenAlex API  (openalex.org)        — gratuita, sin clave
  - Crossref API  (crossref.org)        — gratuita, sin clave
  - arXiv API     (arxiv.org)           — gratuita, sin clave
  - CORE API      (core.ac.uk)          — gratuita con clave en .env: CORE_API_KEY
  - Documentos internos del sistema     — comparación full-text con TF-IDF

IMPORTANTE: Este análisis NO es equivalente a Turnitin ni a herramientas comerciales.
Compara exclusivamente contra fuentes de acceso abierto y documentos internos cargados
en el sistema. No accede a bases privadas, revistas cerradas ni trabajos no publicados.
"""

import os, re, time, xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .database import query as db_query

# ── Configuración ─────────────────────────────────────────────────────────────
OPENALEX_EMAIL    = os.getenv("OPENALEX_EMAIL", "admin@tesis.edu")
CORE_API_KEY      = os.getenv("CORE_API_KEY", "")
REQUEST_TIMEOUT   = 12          # segundos por llamada API
API_DELAY         = 0.4         # pausa entre llamadas (respeto rate-limit)
MAX_DOC_CHARS     = 6000        # máx. caracteres a comparar del doc
MAX_SRC_CHARS     = 2000        # máx. caracteres del abstract/fuente
MIN_SIM_INCLUDE   = 5.0         # % mínimo para incluir fuente en el reporte
FRAGMENT_MIN_WORDS= 7           # min. palabras para considerar una frase
FRAGMENT_THRESHOLD= 0.28        # Jaccard mínimo para marcar un fragmento


# ── Normalización de texto ─────────────────────────────────────────────────────
_STOPWORDS = {
    'el','la','los','las','un','una','unos','unas','de','del','al','en',
    'con','por','para','que','es','son','se','su','sus','lo','le','les',
    'y','o','a','e','ni','pero','si','no','ya','más','muy','bien','the',
    'and','or','of','in','to','a','an','is','are','was','were','be',
    'been','for','on','at','by','as','from','this','that','with','it',
}

def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = [t for t in text.split() if t not in _STOPWORDS and len(t) > 1]
    return " ".join(tokens)


def _tfidf_sim(text1: str, text2: str) -> float:
    """Similitud coseno TF-IDF (1-2-gramas). Retorna 0.0-1.0."""
    t1 = _norm(text1[:MAX_DOC_CHARS])
    t2 = _norm(text2[:MAX_SRC_CHARS])
    if not t1 or not t2:
        return 0.0
    try:
        vec  = TfidfVectorizer(ngram_range=(1, 2), max_features=10000, min_df=1)
        mat  = vec.fit_transform([t1, t2])
        return float(cosine_similarity(mat[0:1], mat[1:2])[0][0])
    except Exception:
        return 0.0


def _jaccard(s1: str, s2: str) -> float:
    w1, w2 = set(s1.lower().split()), set(s2.lower().split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def _find_fragments(doc_text: str, source_text: str) -> list:
    """
    Detecta fragmentos del documento similares al texto fuente.
    Retorna lista de {doc_fragment, source_fragment, similarity}.
    """
    if not source_text.strip():
        return []

    # Dividir doc en oraciones
    sents = re.split(r'(?<=[.!?])\s+', doc_text)
    sents = [s.strip() for s in sents
             if len(s.split()) >= FRAGMENT_MIN_WORDS][:60]

    # Dividir fuente en oraciones
    src_sents = re.split(r'(?<=[.!?])\s+', source_text)
    src_sents = [s.strip() for s in src_sents if s.strip()]

    matches = []
    seen = set()
    for sent in sents:
        src_all_words = set(source_text.lower().split())
        sent_words    = set(sent.lower().split())
        # Jaccard contra todo el abstract
        jac_total = len(sent_words & src_all_words) / len(sent_words | src_all_words) if (sent_words | src_all_words) else 0
        if jac_total < FRAGMENT_THRESHOLD:
            continue
        # Mejor oración de la fuente
        best_src = ""
        best_j   = 0.0
        for ss in src_sents:
            j = _jaccard(sent, ss)
            if j > best_j:
                best_j, best_src = j, ss
        key = sent[:50]
        if key not in seen:
            seen.add(key)
            matches.append({
                "doc_fragment":    sent,
                "source_fragment": best_src or source_text[:600],
                "similarity":      round(jac_total * 100, 1),
            })

    return sorted(matches, key=lambda x: x["similarity"], reverse=True)[:5]


# ── Extracción de metadatos del documento ─────────────────────────────────────
def extract_doc_metadata(text: str) -> dict:
    """Extrae título, resumen, palabras clave y genera query para APIs."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    text_lower = text.lower()

    # Título: primera línea entre 3 y 25 palabras
    title = ""
    for line in lines[:20]:
        wc = len(line.split())
        if 3 <= wc <= 25 and not line.endswith(':'):
            title = line
            break

    # Resumen/abstract
    abstract = ""
    for marker in ['abstract', 'resumen', 'summary']:
        idx = text_lower.find(marker)
        if idx != -1 and idx < len(text) * 0.3:
            raw = text[idx: idx + 1200]
            raw = re.sub(rf'^{marker}[:\s]*', '', raw, flags=re.IGNORECASE)
            abstract = raw.split('\n\n')[0].strip()
            break

    # Palabras clave
    keywords = []
    for kp in ['keywords', 'palabras clave', 'key words']:
        idx = text_lower.find(kp)
        if idx != -1:
            kw_line = text[idx: idx + 400].split('\n')[0]
            kw_line = re.sub(rf'^{kp}[:\s]*', '', kw_line, flags=re.IGNORECASE)
            keywords = [k.strip() for k in re.split(r'[;,·]', kw_line)
                        if k.strip() and len(k.strip()) < 50][:6]
            break

    # Query para APIs
    query_parts = []
    if title:
        query_parts.append(title)
    elif lines:
        query_parts.append(' '.join(lines[0].split()[:12]))
    if keywords:
        query_parts.extend(keywords[:3])
    elif abstract:
        query_parts.append(' '.join(abstract.split()[:15]))

    query = " ".join(query_parts)[:220]

    return {
        "title":    title,
        "abstract": abstract[:500] if abstract else "",
        "keywords": keywords,
        "query":    query,
    }


# ── Reconstruir abstract de OpenAlex (inverted index) ─────────────────────────
def _rebuild_abstract(inv: dict) -> str:
    if not inv:
        return ""
    try:
        max_pos = max(p for positions in inv.values() for p in positions)
        words = [""] * (max_pos + 1)
        for word, positions in inv.items():
            for p in positions:
                if p < len(words):
                    words[p] = word
        return " ".join(w for w in words if w)
    except Exception:
        return ""


# ── Búsquedas en APIs públicas ────────────────────────────────────────────────

def _search_openalex(query: str) -> list:
    url = "https://api.openalex.org/works"
    params = {
        "search":   query,
        "per-page": 7,
        "mailto":   OPENALEX_EMAIL,
        "select":   "id,title,abstract_inverted_index,authorships,publication_year,doi,primary_location",
    }
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT,
                         headers={"User-Agent": f"ThesisReviewAI/1.0 mailto:{OPENALEX_EMAIL}"})
        r.raise_for_status()
        results = []
        for w in r.json().get("results", []):
            abstract = _rebuild_abstract(w.get("abstract_inverted_index") or {})
            authors  = [a.get("author", {}).get("display_name", "")
                        for a in w.get("authorships", [])[:3]]
            loc      = (w.get("primary_location") or {})
            journal  = (loc.get("source") or {}).get("display_name", "")
            doi      = (w.get("doi") or "").replace("https://doi.org/", "")
            results.append({
                "title":       w.get("title", ""),
                "authors":     authors,
                "year":        w.get("publication_year"),
                "doi":         doi,
                "url":         f"https://doi.org/{doi}" if doi else w.get("id", ""),
                "abstract":    abstract,
                "source_name": journal,
                "api":         "OpenAlex",
            })
        return results
    except Exception as e:
        print(f"[open_sim] OpenAlex: {e}")
        return []


def _search_crossref(query: str) -> list:
    url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows":  7,
        "select":"title,author,published,DOI,abstract,container-title",
    }
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT,
                         headers={"User-Agent": "ThesisReviewAI/1.0"})
        r.raise_for_status()
        results = []
        for item in r.json().get("message", {}).get("items", []):
            title   = " ".join(item.get("title", []))
            authors = [f"{a.get('given','')} {a.get('family','')}".strip()
                       for a in item.get("author", [])[:3]]
            pub     = item.get("published", {})
            year    = ((pub.get("date-parts") or [[None]])[0] or [None])[0]
            abstract= re.sub(r'<[^>]+>', '', item.get("abstract", ""))
            doi     = item.get("DOI", "")
            journal = " ".join(item.get("container-title", []))
            results.append({
                "title":       title,
                "authors":     authors,
                "year":        year,
                "doi":         doi,
                "url":         f"https://doi.org/{doi}" if doi else "",
                "abstract":    abstract,
                "source_name": journal,
                "api":         "Crossref",
            })
        return results
    except Exception as e:
        print(f"[open_sim] Crossref: {e}")
        return []


def _search_arxiv(query: str) -> list:
    url = "http://export.arxiv.org/api/query"
    params = {"search_query": f"all:{query[:150]}", "max_results": 5, "sortBy": "relevance"}
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        results = []
        for entry in root.findall("atom:entry", ns):
            title    = (entry.find("atom:title",   ns).text or "").strip().replace('\n', ' ')
            abstract = (entry.find("atom:summary", ns).text or "").strip()
            authors  = [a.find("atom:name", ns).text or ""
                        for a in entry.findall("atom:author", ns)[:3]]
            pub      = (entry.find("atom:published", ns).text or "")[:4]
            arxiv_id = (entry.find("atom:id", ns).text or "").strip()
            results.append({
                "title":       title,
                "authors":     authors,
                "year":        int(pub) if pub.isdigit() else None,
                "doi":         "",
                "url":         arxiv_id,
                "abstract":    abstract,
                "source_name": "arXiv",
                "api":         "arXiv",
            })
        return results
    except Exception as e:
        print(f"[open_sim] arXiv: {e}")
        return []


def _search_core(query: str) -> list:
    if not CORE_API_KEY:
        return []
    url = "https://api.core.ac.uk/v3/search/works"
    headers = {"Authorization": f"Bearer {CORE_API_KEY}"}
    try:
        r = requests.post(url, json={"q": query[:200], "limit": 5},
                          headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        results = []
        for item in r.json().get("results", []):
            dl_url = item.get("downloadUrl") or ""
            src_urls = item.get("sourceFulltextUrls") or []
            link = dl_url or (src_urls[0] if src_urls else "")
            doi  = item.get("doi", "")
            results.append({
                "title":       item.get("title", ""),
                "authors":     [a.get("name","") for a in (item.get("authors") or [])[:3]],
                "year":        item.get("yearPublished"),
                "doi":         doi,
                "url":         link or (f"https://doi.org/{doi}" if doi else ""),
                "abstract":    item.get("abstract", ""),
                "source_name": item.get("publisher", "CORE"),
                "api":         "CORE",
            })
        return results
    except Exception as e:
        print(f"[open_sim] CORE: {e}")
        return []


# ── Comparación con documentos internos ──────────────────────────────────────
def _compare_internal(text: str) -> list:
    """Compara el texto contra todos los avances con texto en la BD."""
    try:
        advances = db_query(
            """SELECT a.id, a.title, a.advance_type, a.created_at,
                      u.name AS student, a.text_content
               FROM advances a
               JOIN users u ON u.id = a.student_id
               WHERE a.text_content IS NOT NULL
                 AND LENGTH(a.text_content) > 100"""
        )
    except Exception:
        return []

    results = []
    for adv in advances:
        adv_text = adv.get("text_content") or ""
        if not adv_text.strip():
            continue
        sim = _tfidf_sim(text, adv_text)
        if sim * 100 < MIN_SIM_INCLUDE:
            continue
        fragments = _find_fragments(text, adv_text)
        year_str  = (adv.get("created_at") or "")[:4]
        results.append({
            "title":             adv.get("title", "Sin título"),
            "authors":           [adv.get("student", "")],
            "year":              int(year_str) if year_str.isdigit() else None,
            "doi":               "",
            "url":               f"/advances/{adv['id']}",
            "abstract":          adv_text[:300] + "…",
            "source_name":       f"Documento interno — {adv.get('advance_type','')}",
            "api":               "Interno",
            "similarity_score":  round(sim * 100, 1),
            "matching_fragments":fragments,
        })

    return sorted(results, key=lambda x: x["similarity_score"], reverse=True)[:5]


# ── Función principal ─────────────────────────────────────────────────────────
def run_open_similarity(text: str, filename: str = "") -> dict:
    """
    Analiza la similitud del texto contra repositorios abiertos y documentos internos.

    Returns dict con el reporte completo:
      overall_similarity, risk_level, sources, fragments, limitations, ...
    """
    text = (text or "").strip()
    if not text:
        return {"error": "No se pudo extraer texto del documento."}

    meta  = extract_doc_metadata(text)
    query = meta.get("query") or text[:200]

    # ── Consultar APIs en secuencia (respetando rate limits) ──────────────────
    print(f"[open_sim] Query: {query[:80]}...")
    raw_sources: list[dict] = []

    search_fns = [
        ("OpenAlex",  lambda: _search_openalex(query)),
        ("Crossref",  lambda: _search_crossref(query)),
        ("arXiv",     lambda: _search_arxiv(query)),
        ("CORE",      lambda: _search_core(query)),
    ]

    for api_name, fn in search_fns:
        try:
            results = fn()
            raw_sources.extend(results)
            print(f"[open_sim] {api_name}: {len(results)} resultados")
        except Exception as e:
            print(f"[open_sim] {api_name} error: {e}")
        time.sleep(API_DELAY)

    # ── Calcular similitud para cada fuente ───────────────────────────────────
    scored_sources: list[dict] = []
    for src in raw_sources:
        src_text = ((src.get("abstract") or "") + " " + (src.get("title") or "")).strip()
        if not src_text:
            continue
        sim  = _tfidf_sim(text, src_text)
        pct  = round(sim * 100, 1)
        if pct < MIN_SIM_INCLUDE:
            continue
        frags = _find_fragments(text, src_text) if pct >= 10 else []
        scored_sources.append({
            **src,
            "similarity_score":   pct,
            "matching_fragments": frags,
        })

    # ── Documentos internos ───────────────────────────────────────────────────
    internal = _compare_internal(text)

    # ── Combinar, deduplicar por título y ordenar ─────────────────────────────
    all_results = scored_sources + internal
    seen_titles: set[str] = set()
    unique: list[dict] = []
    for r in sorted(all_results, key=lambda x: x["similarity_score"], reverse=True):
        t_key = (r.get("title") or "")[:60].lower()
        if t_key and t_key not in seen_titles:
            seen_titles.add(t_key)
            unique.append(r)

    top_results = unique[:12]

    # ── Similitud global ──────────────────────────────────────────────────────
    overall = max((r["similarity_score"] for r in top_results), default=0.0)

    # ── Nivel de riesgo ───────────────────────────────────────────────────────
    if overall < 10:
        risk, risk_color = "Bajo",      "green"
    elif overall < 20:
        risk, risk_color = "Moderado",  "yellow"
    elif overall < 35:
        risk, risk_color = "Alto",      "orange"
    else:
        risk, risk_color = "Muy alto",  "red"

    # ── Fragmentos totales del documento con más coincidencias ────────────────
    top_fragments = []
    for r in top_results[:3]:
        for frag in r.get("matching_fragments", [])[:2]:
            top_fragments.append({**frag, "source_title": r.get("title","")})

    return {
        "overall_similarity":   round(overall, 1),
        "risk_level":           risk,
        "risk_color":           risk_color,
        "total_sources_checked": len(raw_sources),
        "internal_docs_checked": len([a for a in db_query(
            "SELECT COUNT(*) AS c FROM advances WHERE text_content IS NOT NULL")[0].items()]),
        "matching_sources":     len(top_results),
        "sources":              top_results,
        "top_fragments":        top_fragments,
        "document_metadata":    meta,
        "filename":             filename,
        "analyzed_at":          datetime.now().isoformat(),
        "apis_consulted":       ["OpenAlex", "Crossref", "arXiv"] +
                                (["CORE"] if CORE_API_KEY else []) +
                                ["Documentos internos"],
        "limitations": [
            "Este análisis compara exclusivamente contra fuentes de acceso abierto "
            "(OpenAlex, Crossref, arXiv, CORE) y documentos internos del sistema.",
            "No tiene acceso a Scopus, Web of Science, EBSCO, IEEE Xplore de pago "
            "ni a ninguna revista de acceso cerrado.",
            "Trabajos estudiantiles no publicados en repositorios abiertos NO son detectados.",
            "La similitud se calcula sobre resúmenes (abstracts) de los artículos recuperados, "
            "no sobre sus textos completos. Esto puede subestimar la similitud real.",
            "Un porcentaje bajo NO garantiza originalidad absoluta frente a fuentes no indexadas.",
            "Un porcentaje alto requiere revisión humana: puede reflejar terminología "
            "técnica compartida, no necesariamente plagio.",
            "Este sistema NO reemplaza herramientas certificadas como Turnitin o iThenticate. "
            "Su propósito es académico-referencial y de apoyo.",
        ],
    }

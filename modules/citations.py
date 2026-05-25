
import re, requests, time, os
from dotenv import load_dotenv
from .document_processing import extract_references
from .database import execute, now

load_dotenv()

def parse_ref(ref):
    year = ""
    m = re.search(r"(19|20)\d{2}", ref)
    if m: year = m.group(0)
    doi = ""
    dm = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", ref, flags=re.I)
    if dm: doi = dm.group(0)
    title = ref
    parts = re.split(r"\(\d{4}\)|\b(19|20)\d{2}\b", ref, maxsplit=1)
    if len(parts) > 1:
        title = parts[-1].strip(" .:-")
    return {"raw": ref, "title": title[:250], "year": year, "doi": doi}

def validate_citations(advance_id: int, text: str, online=None):
    # Si no se especifica, leer CROSSREF_ENABLED del .env
    if online is None:
        online = os.getenv("CROSSREF_ENABLED", "false").lower() == "true"
    refs = extract_references(text)
    out = []
    for ref in refs:
        p = parse_ref(ref)
        status = "Pendiente"
        suggestion = "Verificar manualmente los datos de autor, año, título y DOI."
        source = "Local"
        if p["doi"]:
            status = "Con DOI"
            suggestion = "La referencia incluye DOI; verificar que corresponda exactamente al título citado."
        elif online:
            try:
                time.sleep(1)
                r = requests.get("https://api.crossref.org/works", params={"query.title": p["title"], "rows": 1}, timeout=8)
                if r.ok and r.json().get("message", {}).get("items"):
                    item = r.json()["message"]["items"][0]
                    status = "Parcial"
                    source = "CrossRef"
                    suggestion = item.get("title", ["Referencia similar encontrada"])[0]
                else:
                    status = "No encontrada"
            except Exception:
                status = "Sin conexión"
        cid = execute("""INSERT INTO citations(advance_id,raw_reference,title,authors,year,doi,status,source,suggestion,created_at)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (advance_id, ref, p["title"], "", p["year"], p["doi"], status, source, suggestion, now()))
        out.append({**p, "id": cid, "status": status, "suggestion": suggestion})
    if not refs:
        cid = execute("""INSERT INTO citations(advance_id,raw_reference,title,authors,year,doi,status,source,suggestion,created_at)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (advance_id, "No se detectaron referencias", "", "", "", "", "No encontrada", "Local", "Agregar referencias en formato APA.", now()))
        out.append({"id": cid, "raw": "No se detectaron referencias", "status": "No encontrada"})
    return out

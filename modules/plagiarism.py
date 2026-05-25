
import re, math, os, uuid, base64, time
from collections import Counter
from dotenv import load_dotenv
from .database import query, execute, now

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Copyleaks integration (opcional — fallback automático al motor local)
# ─────────────────────────────────────────────────────────────────────────────
def _try_copyleaks(advance_id: int, text: str):
    """
    Envía el documento a la API de Copyleaks y retorna lista de coincidencias.
    Retorna None si no está configurado o si ocurre cualquier error.
    """
    api_key = os.getenv("COPYLEAKS_API_KEY", "").strip()
    email   = os.getenv("COPYLEAKS_EMAIL",   "").strip()
    if not api_key or not email:
        return None

    try:
        import requests

        # 1 ── Autenticación ──────────────────────────────────────────────────
        auth = requests.post(
            "https://id.copyleaks.com/v3/account/login/api",
            json={"email": email, "key": api_key},
            timeout=15,
        )
        if not auth.ok:
            print(f"[Copyleaks] Auth falló: {auth.status_code} {auth.text[:120]}")
            return None
        token = auth.json().get("access_token", "")
        if not token:
            return None
        hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 2 ── Enviar documento ───────────────────────────────────────────────
        scan_id    = uuid.uuid4().hex[:20]
        content_b64 = base64.b64encode((text or "").encode("utf-8")).decode()
        sub = requests.put(
            f"https://api.copyleaks.com/v3/scans/submit/file/{scan_id}",
            headers=hdrs,
            json={
                "base64": content_b64,
                "filename": f"avance_{advance_id}.txt",
                "properties": {"sensitiveDataProtection": {"enabled": False}},
            },
            timeout=25,
        )
        if not sub.ok:
            print(f"[Copyleaks] Submit falló: {sub.status_code} {sub.text[:120]}")
            return None

        # 3 ── Iniciar escaneo ────────────────────────────────────────────────
        requests.post(
            "https://api.copyleaks.com/v2/scans/start",
            headers=hdrs,
            json={scan_id: {"sandbox": False}},
            timeout=12,
        )

        # 4 ── Polling (máx 4 × 20s = 80s) ───────────────────────────────────
        completed = False
        for _ in range(4):
            time.sleep(20)
            try:
                st_r = requests.get(
                    f"https://api.copyleaks.com/v3/scans/{scan_id}/status",
                    headers=hdrs, timeout=10,
                )
                if st_r.ok and st_r.json().get("status") == "Completed":
                    completed = True
                    break
            except Exception:
                continue
        if not completed:
            print("[Copyleaks] Timeout — usando motor local.")
            return None

        # 5 ── Obtener resultados ─────────────────────────────────────────────
        res_r = requests.get(
            f"https://api.copyleaks.com/v3/downloads/{scan_id}/results",
            headers=hdrs, timeout=15,
        )
        if not res_r.ok:
            return None

        data  = res_r.json()
        out   = []
        fuentes = (data.get("internet", []) + data.get("database", []))[:8]
        for src in fuentes:
            words_matched = src.get("matchedWords", 0)
            words_total   = max(1, src.get("totalWords", 1))
            sim           = round(words_matched / words_total * 100, 2)
            source_label  = src.get("url") or src.get("title") or "Fuente externa"

            rid = execute(
                """INSERT INTO plagiarism_results
                   (advance_id, compared_advance_id, similarity, section_ref, status, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (advance_id, None, sim, source_label[:250], "Copyleaks", now()),
            )
            out.append({
                "id": rid,
                "compared_title": None,
                "compared_id": None,
                "similarity": sim,
                "section_ref": source_label,
            })
        return out

    except Exception as exc:
        print(f"[Copyleaks] Error: {exc}")
        return None

SPANISH_STOPWORDS = {
    "de","la","el","los","las","y","o","en","del","un","una","por","para","con","se","que",
    "es","al","a","su","sus","como","más","mas","entre","sobre","este","esta","estos","estas",
    "lo","le","ha","han","fue","son","ser","sin","no","si","también","tambien"
}

def tokenize(text):
    words = re.findall(r"[a-záéíóúñü]{3,}", (text or "").lower())
    return [w for w in words if w not in SPANISH_STOPWORDS]

def cosine_counter(c1, c2):
    if not c1 or not c2:
        return 0.0
    common = set(c1) & set(c2)
    numerator = sum(c1[w] * c2[w] for w in common)
    norm1 = math.sqrt(sum(v*v for v in c1.values()))
    norm2 = math.sqrt(sum(v*v for v in c2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return numerator / (norm1 * norm2)

def chunk_text(text, size=900):
    tokens = tokenize(text)
    if not tokens:
        return []
    chunks = []
    for i in range(0, len(tokens), size):
        chunks.append(" ".join(tokens[i:i+size]))
    return chunks or [" ".join(tokens)]

def run_similarity_check(advance_id: int, text: str, program_id: int):
    """
    Detección de similitud: intenta Copyleaks primero si está configurado;
    si no, usa similitud coseno interna.
    """
    copyleaks_results = _try_copyleaks(advance_id, text)
    if copyleaks_results is not None:
        return copyleaks_results
    others = query(
        "SELECT id,title,text_content FROM advances WHERE program_id=? AND id<>? AND text_content IS NOT NULL",
        (program_id, advance_id)
    )
    results = []
    if not others or not (text or "").strip():
        return results

    base_chunks = [Counter(tokenize(c)) for c in chunk_text(text)]
    for other in others:
        other_chunks = [Counter(tokenize(c)) for c in chunk_text(other["text_content"] or "")]
        best = 0.0
        for bc in base_chunks:
            for oc in other_chunks:
                best = max(best, cosine_counter(bc, oc))
        sim_pct = round(best * 100, 2)

        # Umbral bajo para demostración. En producción usar 85% por embeddings.
        if sim_pct >= 35:
            rid = execute(
                """INSERT INTO plagiarism_results(advance_id,compared_advance_id,similarity,section_ref,status,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (advance_id, other["id"], sim_pct, "Documento completo", "Requiere validación humana", now())
            )
            results.append({
                "id": rid,
                "compared_title": other["title"],
                "compared_id": other["id"],
                "similarity": sim_pct
            })
    return results

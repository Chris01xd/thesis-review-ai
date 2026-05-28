"""
Detector de contenido generado por IA.
Estimación probabilística basada en análisis lingüístico estadístico y,
opcionalmente, un modelo de clasificación de HuggingFace (gratuito/local).

AVISO: Es una estimación técnica. No constituye prueba definitiva.
"""
import re
import math
import time
from collections import Counter
from typing import Optional

try:
    from transformers import pipeline as hf_pipeline
    _HF_AVAILABLE = True
except ImportError:
    _HF_AVAILABLE = False

_HF_MODEL = "Hello-SimpleAI/chatgpt-detector-roberta"
_hf_detector = None
_hf_load_attempted = False


# ── Text utilities ────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _split_sentences(text: str) -> list:
    # Split on . ! ? followed by whitespace + capital letter
    raw = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑÜA-Z])', text)
    return [s.strip() for s in raw if len(s.strip().split()) >= 4]


def _split_paragraphs(text: str) -> list:
    paras = re.split(r'\n{2,}', text)
    if len(paras) < 3:
        paras = re.split(r'\n', text)
    return [p.strip() for p in paras if len(p.strip().split()) >= 15]


def _cv(values: list) -> float:
    """Coefficient of variation = std / mean."""
    if len(values) < 3:
        return 0.40
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var) / mean


# ── Linguistic metrics (each returns a raw value) ────────────────────────────

def _sentence_cv(sentences: list) -> float:
    """CV of sentence word-counts. Low → uniform → AI-like."""
    return _cv([len(s.split()) for s in sentences])


def _ttr_moving(text: str, window: int = 100) -> float:
    """Moving-window Type-Token Ratio. Low → repetitive → AI-like."""
    words = re.findall(r'\b[a-záéíóúñüa-z]+\b', text.lower())
    if not words:
        return 0.65
    window = min(window, max(10, len(words) // 2))
    if len(words) <= window:
        return len(set(words)) / len(words)
    ratios = []
    for i in range(0, len(words) - window + 1, max(1, window // 2)):
        w = words[i:i + window]
        ratios.append(len(set(w)) / window)
    return sum(ratios) / len(ratios) if ratios else 0.65


def _ngram_rep(text: str, n: int = 4) -> float:
    """Fraction of n-grams that appear more than once. High → AI-like."""
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < n * 3:
        return 0.0
    ngrams = [tuple(words[i:i + n]) for i in range(len(words) - n + 1)]
    counts = Counter(ngrams)
    repeated = sum(1 for c in counts.values() if c > 1)
    return repeated / len(ngrams)


def _bigram_entropy(text: str) -> float:
    """Conditional bigram entropy. Low → predictable → AI-like."""
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < 20:
        return 3.0
    bigrams = [(words[i], words[i + 1]) for i in range(len(words) - 1)]
    bg_count = Counter(bigrams)
    ug_count = Counter(words)
    total = len(bigrams)
    entropy = 0.0
    for (w1, _), count in bg_count.items():
        p_bg = count / total
        p_cond = count / ug_count[w1]
        if p_cond > 0:
            entropy -= p_bg * math.log2(p_cond)
    return entropy


def _formal_ratio(text: str) -> float:
    """Density of formal transition words. High → AI-like."""
    formal_es = {
        'adicionalmente', 'asimismo', 'consecuentemente', 'consiguientemente',
        'finalmente', 'fundamentalmente', 'igualmente', 'paralelamente',
        'asimismo', 'cabe destacar', 'cabe mencionar', 'cabe señalar',
        'de acuerdo con', 'de esta manera', 'de este modo', 'en conclusión',
        'en consecuencia', 'en este contexto', 'en este sentido', 'en primer lugar',
        'en resumen', 'en segundo lugar', 'es importante', 'es necesario',
        'es relevante', 'no obstante', 'por consiguiente', 'por lo tanto',
        'por otro lado', 'se puede concluir', 'se puede observar', 'sin embargo',
        'tal como', 'teniendo en cuenta', 'resulta fundamental',
    }
    formal_en = {
        'additionally', 'consequently', 'conversely', 'essentially', 'furthermore',
        'importantly', 'moreover', 'nevertheless', 'notably', 'overall',
        'subsequently', 'therefore', 'thus', 'ultimately', 'comprehensively',
        'fundamentally', 'it is worth noting', 'it should be noted',
        'this suggests that', 'this indicates that', 'in conclusion',
        'in summary', 'in contrast', 'in addition', 'as a result',
    }
    text_lower = text.lower()
    words = text_lower.split()
    if not words:
        return 0.0
    hit = 0
    for w in words:
        if w in formal_es or w in formal_en:
            hit += 1
    # Multi-word phrase check
    all_phrases = {p for p in (formal_es | formal_en) if ' ' in p}
    for phrase in all_phrases:
        hit += text_lower.count(phrase)
    return hit / len(words)


def _avg_sent_len(sentences: list) -> float:
    if not sentences:
        return 0.0
    return sum(len(s.split()) for s in sentences) / len(sentences)


def _para_len_cv(paragraphs: list) -> float:
    return _cv([len(p.split()) for p in paragraphs])


# ── Metric → AI probability mapping (each returns 0-1) ───────────────────────

def _p_cv(v: float) -> float:
    # Human ~0.45-0.75, AI ~0.12-0.30  → 1 at v=0.08, 0 at v=0.60
    return max(0.0, min(1.0, (0.60 - v) / 0.52))


def _p_ttr(v: float) -> float:
    # Human ~0.62-0.75, AI ~0.48-0.60  → 1 at v=0.44, 0 at v=0.72
    return max(0.0, min(1.0, (0.72 - v) / 0.28))


def _p_rep(v: float) -> float:
    # Human ~0.01-0.04, AI ~0.05-0.12  → 0 at v=0.01, 1 at v=0.10
    return max(0.0, min(1.0, (v - 0.01) / 0.09))


def _p_entropy(v: float) -> float:
    # Human ~2.8-4.5, AI ~1.2-2.5  → 1 at v=1.0, 0 at v=3.5
    return max(0.0, min(1.0, (3.5 - v) / 2.5))


def _p_formal(v: float) -> float:
    # Human ~0.01-0.03, AI ~0.04-0.09  → 0 at v=0.01, 1 at v=0.08
    return max(0.0, min(1.0, (v - 0.01) / 0.07))


def _p_avg_len(v: float) -> float:
    # Human ~12-20, AI ~22-35  → 0 at v=14, 1 at v=30
    return max(0.0, min(1.0, (v - 14.0) / 16.0))


def _compute_stat_score(cv, ttr, rep, ent, formal, avg_len) -> float:
    return (
        _p_cv(cv)       * 0.28 +
        _p_ttr(ttr)     * 0.14 +
        _p_rep(rep)     * 0.22 +
        _p_entropy(ent) * 0.22 +
        _p_formal(formal) * 0.09 +
        _p_avg_len(avg_len) * 0.05
    ) * 100


# ── HuggingFace model (optional) ─────────────────────────────────────────────

def _load_hf():
    global _hf_detector, _hf_load_attempted
    if _hf_load_attempted:
        return _hf_detector
    _hf_load_attempted = True
    if not _HF_AVAILABLE:
        print("[ai_detector] transformers no está instalado — usando solo análisis estadístico.")
        return None
    try:
        print(f"[ai_detector] Cargando {_HF_MODEL} (puede tardar en primera ejecución)...")
        _hf_detector = hf_pipeline(
            "text-classification",
            model=_HF_MODEL,
            truncation=True,
            max_length=512,
        )
        print("[ai_detector] Modelo cargado.")
    except Exception as exc:
        print(f"[ai_detector] No se pudo cargar el modelo: {exc}")
        _hf_detector = None
    return _hf_detector


def _hf_score_text(text: str) -> Optional[float]:
    """Return 0-100 AI probability via HF model. None if unavailable."""
    detector = _load_hf()
    if detector is None:
        return None
    try:
        words = text.split()
        chunks = [' '.join(words[i:i + 400]) for i in range(0, min(len(words), 2000), 400)]
        chunks = [c for c in chunks if len(c.split()) >= 20]
        if not chunks:
            return None
        scores = []
        for chunk in chunks:
            res = detector(chunk)[0]
            label = res['label'].lower()
            sc = float(res['score'])
            if 'chatgpt' in label or label in ('label_1', 'fake', 'ai'):
                scores.append(sc * 100.0)
            else:
                scores.append((1.0 - sc) * 100.0)
        return sum(scores) / len(scores)
    except Exception as exc:
        print(f"[ai_detector] Error scoring: {exc}")
        return None


# ── Per-paragraph analysis ───────────────────────────────────────────────────

def _score_paragraph(para: str) -> dict:
    sents = _split_sentences(para)
    if len(sents) < 2:
        sents = [s.strip() for s in para.replace('.', '.\n').splitlines() if s.strip()]
        if not sents:
            sents = [para]

    cv      = _sentence_cv(sents) if len(sents) >= 2 else 0.40
    ttr     = _ttr_moving(para, window=min(60, max(10, len(para.split()) // 2)))
    rep     = _ngram_rep(para, n=3)
    ent     = _bigram_entropy(para)
    formal  = _formal_ratio(para)
    avg_len = _avg_sent_len(sents)

    score = _compute_stat_score(cv, ttr, rep, ent, formal, avg_len)
    wc = len(para.split())
    if wc < 30:
        score *= 0.65
    elif wc < 60:
        score *= 0.85

    return {
        'text':  para,
        'score': round(min(100.0, max(0.0, score)), 1),
        'metrics': {
            'sentence_cv':      round(cv, 3),
            'ttr':              round(ttr, 3),
            'ngram_repetition': round(rep, 4),
            'bigram_entropy':   round(ent, 3),
            'formal_words':     round(formal, 4),
            'avg_sentence_len': round(avg_len, 1),
        },
    }


# ── Main public function ──────────────────────────────────────────────────────

def run_ai_detection(text: str, filename: str = '') -> dict:
    """
    Analyze text for AI-generated content indicators.
    Returns a report dict with probability scores, metrics, and flagged paragraphs.
    """
    t0 = time.time()
    text = _clean(text)
    word_count = len(text.split())

    if word_count < 50:
        return {
            'error': 'Texto demasiado corto (mínimo 50 palabras para analizar).',
            'ai_probability': 0,
            'risk_level': 'Indeterminado',
            'risk_color': 'gray',
        }

    sentences  = _split_sentences(text) or [text]
    paragraphs = _split_paragraphs(text) or [text]

    # Global metrics
    cv      = _sentence_cv(sentences)
    ttr     = _ttr_moving(text)
    rep     = _ngram_rep(text)
    ent     = _bigram_entropy(text)
    formal  = _formal_ratio(text)
    avg_len = _avg_sent_len(sentences)
    para_cv = _para_len_cv(paragraphs)

    stat_score = _compute_stat_score(cv, ttr, rep, ent, formal, avg_len)

    # Optional HuggingFace model
    hf = _hf_score_text(text[:4000])

    if hf is not None:
        final = round(stat_score * 0.40 + hf * 0.60, 1)
    else:
        final = round(stat_score, 1)
    final = min(100.0, max(0.0, final))

    if final < 20:
        risk_level, risk_color = 'Bajo',      'green'
    elif final < 40:
        risk_level, risk_color = 'Moderado',  'yellow'
    elif final < 65:
        risk_level, risk_color = 'Alto',      'orange'
    else:
        risk_level, risk_color = 'Muy alto',  'red'

    # Per-paragraph
    para_scores = []
    for p in paragraphs[:40]:
        if len(p.split()) >= 18:
            para_scores.append(_score_paragraph(p))
    para_scores.sort(key=lambda x: x['score'], reverse=True)
    suspicious = [p for p in para_scores if p['score'] >= 50]

    return {
        'ai_probability':        final,
        'statistical_score':     round(stat_score, 1),
        'hf_score':              round(hf, 1) if hf is not None else None,
        'hf_model_used':         _HF_MODEL if hf is not None else None,
        'risk_level':            risk_level,
        'risk_color':            risk_color,
        'low_confidence':        word_count < 200,
        'total_words':           word_count,
        'total_sentences':       len(sentences),
        'total_paragraphs':      len(paragraphs),
        'suspicious_count':      len(suspicious),
        'suspicious_paragraphs': suspicious[:10],
        'all_paragraphs':        para_scores,
        'global_metrics': {
            'sentence_cv':       round(cv, 3),
            'paragraph_cv':      round(para_cv, 3),
            'type_token_ratio':  round(ttr, 3),
            'ngram_repetition':  round(rep, 4),
            'bigram_entropy':    round(ent, 3),
            'formal_word_ratio': round(formal, 4),
            'avg_sentence_len':  round(avg_len, 1),
        },
        'methods_used': (['statistical', 'hf_model'] if hf is not None else ['statistical']),
        'filename':     filename,
        'analyzed_at':  time.strftime('%Y-%m-%dT%H:%M:%S'),
        'elapsed_s':    round(time.time() - t0, 2),
        'disclaimer': (
            'Este resultado es una estimación técnica y no constituye una prueba definitiva '
            'de uso de inteligencia artificial. Los detectores automáticos pueden producir '
            'falsos positivos (textos humanos clasificados como IA) y falsos negativos '
            '(textos de IA no detectados), especialmente en textos académicos, corregidos, '
            'traducidos o parafraseados.'
        ),
        'limitations': [
            'No detecta IA con certeza absoluta — es una estimación estadística y probabilística.',
            'Textos académicos formales pueden mostrar mayor similitud estilística con IA.',
            'Textos traducidos, parafraseados o corregidos por humanos pueden alterar los indicadores.',
            'Textos cortos (< 200 palabras) producen resultados menos confiables.',
            'El modelo de HuggingFace fue entrenado principalmente con texto en inglés.',
            'No reemplaza el criterio del docente o asesor académico.',
        ],
    }

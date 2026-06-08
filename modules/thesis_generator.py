"""
modules/thesis_generator.py
Generación automática de tesis universitaria (PDF + DOCX) basada en IA/plantillas.
"""
import os, json, uuid, random, re
from datetime import datetime
from typing import Optional

# ── Fuente Arial Narrow ───────────────────────────────────────────────────────
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_F  = 'Helvetica'
_FB = 'Helvetica-Bold'
_FI = 'Helvetica-Oblique'
_fonts_ok = False

def _register_fonts():
    global _F, _FB, _FI, _fonts_ok
    if _fonts_ok:
        return
    font_paths = {
        'ArialNarrow':        'C:/Windows/Fonts/ARIALN.TTF',
        'ArialNarrow-Bold':   'C:/Windows/Fonts/ARIALNB.TTF',
        'ArialNarrow-Italic': 'C:/Windows/Fonts/ARIALNI.TTF',
    }
    for name, path in font_paths.items():
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                if name == 'ArialNarrow':        _F  = name
                elif name == 'ArialNarrow-Bold':  _FB = name
                elif name == 'ArialNarrow-Italic':_FI = name
            except Exception:
                pass
    _fonts_ok = True


# ── ReportLab ─────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.units    import cm
from reportlab.lib.styles   import ParagraphStyle
from reportlab.lib.enums    import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)
from reportlab.lib import colors

# ── python-docx ───────────────────────────────────────────────────────────────
from docx import Document as _DocxDoc
from docx.shared  import Cm as _Cm, Pt as _Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml   import OxmlElement

# ── Constantes de formato ─────────────────────────────────────────────────────
ML, MR, MT, MB = 3*cm, 2.5*cm, 2.5*cm, 2.5*cm
FS  = 12    # font size (pt)
LD  = 20    # leading = 1.5 * 12 * 1.11 ≈ 20
OUTPUT_DIR = 'data/thesis'


# ── Estilos ReportLab ─────────────────────────────────────────────────────────
def _s() -> dict:
    _register_fonts()
    def mk(**kw):
        base = dict(fontName=_F, fontSize=FS, leading=LD, alignment=TA_JUSTIFY, spaceAfter=8)
        base.update(kw)
        return base
    return {
        'n':   ParagraphStyle('N',   **mk()),
        'c':   ParagraphStyle('C',   **mk(alignment=TA_CENTER)),
        'l':   ParagraphStyle('L',   **mk(alignment=TA_LEFT)),
        'h1':  ParagraphStyle('H1',  **mk(fontName=_FB, fontSize=16, alignment=TA_CENTER,
                                          spaceAfter=14, spaceBefore=10, leading=24)),
        'h2':  ParagraphStyle('H2',  **mk(fontName=_FB, fontSize=13, alignment=TA_LEFT,
                                          spaceAfter=8, spaceBefore=10)),
        'h3':  ParagraphStyle('H3',  **mk(fontName=_FB, fontSize=12, alignment=TA_LEFT,
                                          spaceAfter=6, spaceBefore=6)),
        'ref': ParagraphStyle('REF', **mk(leftIndent=28, firstLineIndent=-28)),
        'ind': ParagraphStyle('IND', **mk(leftIndent=18)),
        'ind2':ParagraphStyle('ID2', **mk(leftIndent=36)),
        'sm':  ParagraphStyle('SM',  **mk(fontSize=10, leading=14)),
    }


def _page_num(canvas, doc):
    if doc.page <= 1:
        return
    _register_fonts()
    canvas.saveState()
    canvas.setFont(_F, 10)
    canvas.drawRightString(A4[0] - MR, 1.2*cm, str(doc.page))
    canvas.restoreState()


# ── Datos de referencia para generación ──────────────────────────────────────
_JOURNALS_EN = [
    "IEEE Transactions on Software Engineering",
    "Journal of Systems and Software",
    "Expert Systems with Applications",
    "Information Sciences",
    "Computers & Education",
    "International Journal of Information Management",
    "Decision Support Systems",
    "Knowledge-Based Systems",
    "Future Generation Computer Systems",
    "Applied Soft Computing",
    "IEEE Access",
    "Sustainability",
    "Sensors",
    "Electronics",
    "Technological Forecasting and Social Change",
    "Journal of Business Research",
    "Computers in Human Behavior",
    "Information and Management",
]
_JOURNALS_ES = [
    "Revista de Educación Superior",
    "Contaduría y Administración",
    "Ingeniería Industrial",
    "Ingeniería Electrónica, Automática y Comunicaciones",
    "Acta Colombiana de Psicología",
]
_AUTHORS_EN = [
    ("Smith","J."),("Johnson","M."),("Williams","R."),("Brown","K."),
    ("Jones","D."),("Garcia","A."),("Miller","P."),("Davis","S."),
    ("Wilson","T."),("Anderson","L."),("Taylor","C."),("Thomas","N."),
    ("Jackson","B."),("White","E."),("Harris","G."),("Martin","F."),
    ("Thompson","H."),("Lewis","O."),("Walker","V."),("Hall","U."),
    ("Allen","I."),("Young","W."),("King","X."),("Wright","Z."),
    ("Lee","Y."),("Robinson","Q."),
]
_AUTHORS_ES = [
    ("Ramírez","A."),("Pérez","J."),("González","M."),("López","R."),
    ("Martínez","C."),("García","L."),("Flores","E."),("Vargas","P."),
]


# ── Generador de referencias APA V7 ──────────────────────────────────────────
def _gen_references(title: str, n: int = 25) -> list:
    rng = random.Random(abs(hash(title)) % 99999)
    stopwords = {'de','en','la','el','los','las','para','con','del',
                 'un','una','y','o','a','the','of','in','for','and',
                 'to','an','using','based','approach','system'}
    kws = [w.strip('.,();:') for w in title.split()
           if len(w) > 3 and w.lower() not in stopwords]
    if not kws:
        kws = ['system','management','information','technology']

    refs, n_en, n_5y, n_art = [], 0, 0, 0
    lim_en, lim_5y, lim_art = int(n*0.82), int(n*0.82), int(n*0.82)

    for i in range(n):
        is_en  = n_en  < lim_en  or rng.random() < 0.3
        is_5y  = n_5y  < lim_5y  or rng.random() < 0.2
        is_art = n_art < lim_art or rng.random() < 0.25
        if is_en:  n_en  += 1
        if is_5y:  n_5y  += 1
        if is_art: n_art += 1

        year = rng.randint(2021,2026) if is_5y else rng.randint(2012,2020)
        kw   = rng.choice(kws)
        au_pool = _AUTHORS_EN if is_en else _AUTHORS_ES
        auts    = rng.sample(au_pool, min(rng.randint(1,4), len(au_pool)))
        if len(auts) > 3:
            au_str = ", ".join(f"{a[0]}, {a[1]}." for a in auts[:3]) + ", et al."
        else:
            au_str = ", ".join(f"{a[0]}, {a[1]}." for a in auts)

        if is_art:
            journal = rng.choice(_JOURNALS_EN if is_en else _JOURNALS_ES)
            vol = rng.randint(1,55); iss = rng.randint(1,12)
            p1  = rng.randint(1,300); p2  = p1 + rng.randint(8,22)
            doi = f"https://doi.org/10.{rng.randint(1000,9999)}/{''.join(rng.choices('abcdefghijklmnopqrstuvwxyz0123456789',k=10))}"
            if is_en:
                at = rng.choice([
                    f"A systematic review of {kw} in academic settings",
                    f"Machine learning approaches for {kw} optimization: A survey",
                    f"Deep learning for {kw} — state of the art and future directions",
                    f"Emerging trends in {kw} management: An empirical study",
                    f"Framework for {kw} evaluation in higher education institutions",
                    f"Impact of {kw} on organizational performance: Evidence from Latin America",
                    f"AI-driven {kw}: Challenges and opportunities",
                    f"Blockchain technology for {kw} traceability and transparency",
                    f"An empirical study of {kw} adoption factors in SMEs",
                    f"Towards an integrated model of {kw} in digital transformation",
                ])
            else:
                at = rng.choice([
                    f"Evaluación del impacto de {kw} en instituciones universitarias peruanas",
                    f"Modelo de gestión basado en {kw} para organizaciones de la región",
                    f"Análisis de factores críticos en la implementación de {kw}",
                    f"Revisión sistemática sobre {kw} en el contexto latinoamericano",
                    f"Propuesta metodológica para la evaluación de {kw} en el sector educativo",
                ])
            refs.append(f"{au_str} ({year}). {at}. *{journal}*, *{vol}*({iss}), {p1}–{p2}. {doi}")
        else:
            if rng.random() < 0.6:
                pub = rng.choice(["Springer","Wiley","CRC Press","MIT Press",
                                  "Elsevier","IGI Global","O'Reilly Media"]) if is_en \
                      else rng.choice(["Pearson Educación","McGraw-Hill","Editorial Universitaria"])
                bt = rng.choice([
                    f"Principles of {kw.capitalize()} Engineering",
                    f"Handbook of {kw.capitalize()} Systems",
                    f"Applied {kw.capitalize()} in Organizations",
                    f"Introduction to {kw.capitalize()} Management",
                ]) if is_en else rng.choice([
                    f"Fundamentos de {kw}",
                    f"Gestión de {kw} en organizaciones contemporáneas",
                    f"Manual de {kw} aplicada",
                ])
                city_pub = rng.choice(["New York","London","Cham","Hoboken"]) if is_en \
                           else rng.choice(["Ciudad de México","Madrid","Buenos Aires"])
                refs.append(f"{au_str} ({year}). *{bt}*. {city_pub}: {pub}.")
            else:
                conf = rng.choice([
                    "Proceedings of the International Conference on Information Systems (ICIS)",
                    "IEEE International Conference on Software Engineering (ICSE)",
                    "Proceedings of the Hawaii International Conference on System Sciences (HICSS)",
                    "ACM Conference on Computer-Supported Cooperative Work (CSCW)",
                ]) if is_en else rng.choice([
                    "Congreso Iberoamericano de Informática Educativa",
                    "Conferencia Latinoamericana de Ingeniería de Software",
                ])
                p1 = rng.randint(1,500); p2 = p1+rng.randint(5,15)
                ct = f"{kw.capitalize()} in the digital era: Challenges and opportunities" if is_en \
                     else f"Implementación de {kw} en el contexto universitario peruano"
                refs.append(f"{au_str} ({year}). {ct}. *{conf}* (pp. {p1}–{p2}).")

    refs.sort()
    return refs


# ── Plantillas de contenido ───────────────────────────────────────────────────
def _rp(title: str, rl: str) -> str:
    t = title.lower()
    return (
        f"En el contexto global actual, caracterizado por la acelerada transformación digital y "
        f"la creciente demanda de soluciones innovadoras, el área relacionada con {t} se ha "
        f"convertido en un campo de especial relevancia. Organismos internacionales como la UNESCO "
        f"(2023) y el Banco Mundial (2022) subrayan que la adopción de nuevas metodologías y "
        f"herramientas tecnológicas constituye uno de los principales desafíos del siglo XXI. En "
        f"este escenario, las instituciones que no incorporan estrategias efectivas en torno a {t} "
        f"enfrentan serias dificultades para mantenerse competitivas y ofrecer servicios de calidad.\n\n"
        f"En América Latina, esta problemática adquiere una dimensión particular. Los países de la "
        f"región evidencian brechas significativas en el desarrollo e implementación de soluciones "
        f"vinculadas a {t}. Estudios recientes como los de García et al. (2023) y Rodríguez & López "
        f"(2022) muestran que más del 65% de las organizaciones latinoamericanas reportan dificultades "
        f"para implementar de manera efectiva los procesos asociados a esta temática, generando pérdidas "
        f"en eficiencia y reducción en la calidad de los servicios ofrecidos. La línea de investigación "
        f"de {rl} cobra así una importancia estratégica en la búsqueda de soluciones contextualizadas.\n\n"
        f"En el Perú, el Instituto Nacional de Estadística e Informática — INEI (2022) y el Ministerio "
        f"de Educación (2023) reportan que una proporción significativa de instituciones no cuenta con "
        f"los recursos humanos ni tecnológicos necesarios para abordar adecuadamente los desafíos "
        f"planteados por {t}. Esta carencia impacta directamente en la calidad de los procesos "
        f"institucionales y en la satisfacción de los usuarios finales, evidenciando la necesidad "
        f"urgente de propuestas fundamentadas y adaptadas a la realidad nacional.\n\n"
        f"A nivel local, el diagnóstico situacional realizado en el marco de la presente investigación "
        f"permitió identificar limitaciones concretas en cuanto a la gestión y aplicación de {t} en "
        f"las organizaciones del ámbito de estudio. Las evidencias recogidas a través de encuestas, "
        f"entrevistas y análisis documentales confirman la existencia de una brecha entre las prácticas "
        f"actuales y los estándares internacionales de calidad. Ante este panorama, resulta imprescindible "
        f"desarrollar una propuesta que contribuya a superar estas deficiencias y generar valor sostenible "
        f"para las organizaciones y sus beneficiarios."
    )


def _ant(title: str) -> str:
    t = title.lower()
    return (
        f"Con relación a los antecedentes de la investigación, se han identificado estudios previos "
        f"que abordan temáticas vinculadas a {t}, tanto en el plano internacional como nacional y local.\n\n"
        f"A nivel internacional, Smith & Johnson (2024) desarrollaron una investigación sobre sistemas "
        f"análogos al propuesto, concluyendo que la implementación de soluciones basadas en inteligencia "
        f"artificial y metodologías ágiles incrementa la eficiencia de los procesos en un 42%. En la "
        f"misma línea, Williams et al. (2023) reportaron resultados favorables al aplicar técnicas "
        f"avanzadas de procesamiento de información en contextos académicos e institucionales, logrando "
        f"reducciones del 35% en los tiempos de respuesta. Brown & García (2023) realizaron un estudio "
        f"comparativo en instituciones educativas de Europa y América Latina, concluyendo que la adopción "
        f"de herramientas tecnológicas innovadoras se traduce en mejores indicadores de desempeño y mayor "
        f"satisfacción de los usuarios. Sus recomendaciones enfatizan la importancia de la participación "
        f"activa de los actores involucrados y la adecuación de las soluciones al contexto local.\n\n"
        f"A nivel nacional, Rodríguez Sánchez (2022) investigó la problemática en el contexto peruano, "
        f"identificando factores críticos de éxito para implementaciones similares a la propuesta en la "
        f"presente investigación. Sus hallazgos destacan la relevancia de la capacitación del personal "
        f"y el soporte institucional como variables determinantes del éxito. Pérez & Vargas (2023) "
        f"desarrollaron un modelo conceptual validado en universidades públicas peruanas, cuyos resultados "
        f"estadísticamente significativos sirven de referencia para investigaciones como la presente.\n\n"
        f"A nivel local, Flores Ramírez (2022) condujo un estudio exploratorio en la región La Libertad, "
        f"reportando las principales deficiencias en la gestión de procesos relacionados con el área de "
        f"estudio. Sus recomendaciones constituyen un insumo valioso para el diseño de la propuesta "
        f"desarrollada en la presente investigación, fundamentando la elección metodológica adoptada."
    )


def _mt(title: str, rl: str) -> str:
    t = title.lower()
    return (
        f"El sustento teórico de la presente investigación se apoya en tres metodologías fundamentales "
        f"que proveen el marco conceptual necesario para abordar la problemática de {t}.\n\n"
        f"La primera corresponde al Modelo de Aceptación Tecnológica (TAM), desarrollado por Davis "
        f"(1989) y ampliamente empleado en investigaciones sobre adopción de tecnología. Este modelo "
        f"postula que la utilidad percibida y la facilidad de uso percibida son los principales "
        f"determinantes de la actitud del usuario hacia un sistema. Aplicado al desarrollo de {t}, "
        f"el TAM permite evaluar la disposición de los usuarios finales y los factores que inciden "
        f"en la adopción efectiva de la solución propuesta. Investigaciones recientes de Johnson et "
        f"al. (2023) han extendido el modelo incorporando variables contextuales propias de entornos "
        f"educativos y organizacionales latinoamericanos, consolidando su pertinencia para investigaciones "
        f"en la línea de {rl}.\n\n"
        f"La segunda metodología es SCRUM, framework ágil reconocido internacionalmente como uno de los "
        f"marcos de trabajo más efectivos para el desarrollo de soluciones tecnológicas complejas. SCRUM "
        f"estructura el trabajo en iteraciones cortas denominadas sprints, lo que facilita la adaptación "
        f"continua a los requisitos del usuario y garantiza la entrega incremental de valor. En el "
        f"contexto de {t}, SCRUM proporciona una guía clara para el proceso de desarrollo, validación "
        f"e implementación de los componentes de la solución. Según Schwaber & Sutherland (2020), este "
        f"framework resulta especialmente adecuado para proyectos que requieren flexibilidad, orientación "
        f"al usuario y mejora continua.\n\n"
        f"La tercera metodología es el Proceso Unificado Racional (RUP, por sus siglas en inglés), que "
        f"estructura el ciclo de desarrollo de software en cuatro fases principales: inicio, elaboración, "
        f"construcción y transición. RUP complementa el enfoque ágil de SCRUM al aportar rigor en la "
        f"documentación y trazabilidad de los requisitos, asegurando la calidad del producto final. Su "
        f"aplicación en investigaciones relacionadas con {t} permite gestionar la complejidad del "
        f"proyecto de manera ordenada, facilitando la comunicación entre los distintos actores y la "
        f"evaluación sistemática de los resultados obtenidos en cada fase del desarrollo."
    )


def _just(title: str) -> str:
    t = title.lower()
    return (
        f"La presente investigación se justifica desde múltiples perspectivas que evidencian su "
        f"pertinencia y contribución al conocimiento científico y al desarrollo social.\n\n"
        f"Desde el punto de vista teórico, la investigación enriquece el corpus de conocimiento "
        f"existente sobre {t}, aportando evidencia empírica que complementa y valida los marcos "
        f"conceptuales previos. Los hallazgos permitirán confirmar, refutar o matizar las teorías "
        f"existentes, generando perspectivas de análisis originales para futuras investigaciones.\n\n"
        f"En términos prácticos, la propuesta ofrece una solución concreta y replicable a los "
        f"problemas identificados en el diagnóstico. Su implementación permitirá optimizar los "
        f"procesos involucrados, reducir tiempos de respuesta, mejorar la calidad de los resultados "
        f"y generar ahorros significativos en los recursos empleados, lo que redunda directamente "
        f"en la eficiencia y competitividad de las organizaciones beneficiadas.\n\n"
        f"Desde la perspectiva social, la investigación impacta en la calidad de vida de los "
        f"usuarios y beneficiarios finales, quienes accederán a servicios más eficientes, "
        f"transparentes y accesibles. La propuesta contribuye al logro de los Objetivos de "
        f"Desarrollo Sostenible (ODS 4 y ODS 9) de la Agenda 2030 de las Naciones Unidas.\n\n"
        f"Metodológicamente, la investigación aporta instrumentos y procedimientos validados que "
        f"constituirán un referente para investigaciones similares, contribuyendo al desarrollo "
        f"de la comunidad científica en el área de {t}."
    )


def _intro_text(data: dict, refs: list) -> str:
    """Construye el texto corrido del Capítulo I (sin subtítulos)."""
    t  = data['title'].lower()
    rl = data['research_line']
    oe = data.get('objetivo_especifico', [])
    rp_text = _rp(data['title'], rl)
    ant_text = _ant(data['title'])
    mt_text  = _mt(data['title'], rl)
    just_text= _just(data['title'])
    prob     = f"¿En qué medida el desarrollo e implementación de {t} contribuye a mejorar los procesos y resultados en las organizaciones del ámbito de estudio durante el período 2025-2026?"
    hip      = f"El desarrollo e implementación de {t} mejora significativamente los procesos y resultados en las organizaciones del ámbito de estudio, logrando un incremento mínimo del 30% en los indicadores de eficiencia, calidad y satisfacción de los usuarios durante el período 2025-2026."
    obj_gen  = f"Desarrollar e implementar {t} para mejorar los procesos y resultados en las organizaciones del ámbito de estudio, incrementando la eficiencia operativa y la calidad de los servicios ofrecidos."
    return {
        'rp': rp_text, 'ant': ant_text, 'mt': mt_text,
        'just': just_text, 'prob': prob, 'hip': hip,
        'obj_gen': obj_gen,
        'obj_esp': [
            f"Diagnosticar la situación actual de los procesos relacionados con {t} en las organizaciones del ámbito de estudio, identificando las principales deficiencias y oportunidades de mejora.",
            f"Diseñar e implementar los componentes principales de {t}, aplicando las metodologías y herramientas seleccionadas para garantizar la calidad y funcionalidad de la solución propuesta.",
            f"Evaluar el impacto de la implementación de {t} en los indicadores de eficiencia, calidad y satisfacción de los usuarios mediante instrumentos de medición validados y técnicas estadísticas apropiadas.",
        ],
        'lim': (
            "La presente investigación delimita su alcance geográfico al ámbito de estudio definido en la "
            "problemática, por lo que los resultados no deben generalizarse directamente a otros contextos "
            "sin realizar los ajustes metodológicos correspondientes. La variabilidad de los entornos "
            "organizacionales y culturales puede influir en la replicabilidad de los hallazgos.\n\n"
            "El período de implementación y evaluación está acotado al cronograma académico establecido, "
            "lo cual limita la observación de efectos a largo plazo. Se recomienda la realización de "
            "estudios longitudinales para evaluar la sostenibilidad de los resultados obtenidos.\n\n"
            "La disponibilidad y acceso a información actualizada representa una limitación inherente a "
            "toda investigación de este tipo, especialmente en lo referente a datos estadísticos locales. "
            "Se han adoptado medidas para minimizar su impacto mediante la triangulación de fuentes y "
            "la aplicación de instrumentos primarios de recolección de datos."
        ),
    }


def _arbol_problemas(title: str) -> list:
    """Retorna una representación textual del árbol de problemas."""
    t = title.lower()
    t_cap = title.split()[0].capitalize() if title.split() else "El problema"
    return [
        ("ÁRBOL DE PROBLEMAS", "h2"),
        ("EFECTOS (consecuencias del problema central)", "h3"),
        (f"→ Baja calidad y eficiencia en los procesos relacionados con {t}", "ind"),
        (f"    → Incremento de costos operativos y tiempos de respuesta", "ind2"),
        (f"    → Insatisfacción de los usuarios y beneficiarios del servicio", "ind2"),
        (f"→ Pérdida de competitividad institucional", "ind"),
        (f"    → Dificultad para cumplir estándares de calidad exigidos", "ind2"),
        (f"    → Desventaja frente a organizaciones que sí han adoptado soluciones modernas", "ind2"),
        ("", "sp"),
        ("PROBLEMA CENTRAL", "h3"),
        (f"Deficiencias en la gestión e implementación de {t} en las organizaciones del ámbito de estudio, que limitan la eficiencia operativa y la calidad de los servicios.", "n"),
        ("", "sp"),
        ("CAUSAS (origen del problema central)", "h3"),
        (f"→ Ausencia de un sistema o solución tecnológica adecuada para {t}", "ind"),
        (f"    → Inexistencia de herramientas especializadas adaptadas al contexto", "ind2"),
        (f"    → Falta de inversión en infraestructura tecnológica", "ind2"),
        (f"→ Limitado conocimiento técnico del personal", "ind"),
        (f"    → Escasa capacitación en metodologías y herramientas modernas", "ind2"),
        (f"    → Alta rotación de personal técnico especializado", "ind2"),
        (f"→ Deficiencias en los procesos de planificación y gestión institucional", "ind"),
        (f"    → Ausencia de indicadores de seguimiento y control", "ind2"),
        (f"    → Falta de políticas claras para la adopción de tecnología", "ind2"),
    ]


def _arbol_objetivos(title: str) -> list:
    t = title.lower()
    return [
        ("ÁRBOL DE OBJETIVOS", "h2"),
        ("FINES (situación deseada tras alcanzar los objetivos)", "h3"),
        (f"→ Alta calidad y eficiencia en los procesos relacionados con {t}", "ind"),
        (f"    → Reducción de costos operativos y tiempos de respuesta", "ind2"),
        (f"    → Satisfacción de los usuarios y beneficiarios del servicio", "ind2"),
        (f"→ Mejora de la competitividad institucional", "ind"),
        (f"    → Cumplimiento de estándares internacionales de calidad", "ind2"),
        (f"    → Posicionamiento estratégico frente a organizaciones del sector", "ind2"),
        ("", "sp"),
        ("OBJETIVO CENTRAL", "h3"),
        (f"Desarrollar e implementar {t} para mejorar la eficiencia operativa y la calidad de los servicios en las organizaciones del ámbito de estudio.", "n"),
        ("", "sp"),
        ("MEDIOS (acciones para alcanzar el objetivo central)", "h3"),
        (f"→ Diseño e implementación de una solución tecnológica para {t}", "ind"),
        (f"    → Desarrollo de componentes funcionales adaptados al contexto", "ind2"),
        (f"    → Inversión en infraestructura tecnológica adecuada", "ind2"),
        (f"→ Fortalecimiento de capacidades del personal", "ind"),
        (f"    → Programas de capacitación en metodologías y herramientas modernas", "ind2"),
        (f"    → Implementación de un plan de gestión del conocimiento", "ind2"),
        (f"→ Mejora de los procesos de planificación y gestión institucional", "ind"),
        (f"    → Establecimiento de indicadores de seguimiento y control (KPIs)", "ind2"),
        (f"    → Definición de políticas institucionales para la adopción de tecnología", "ind2"),
    ]


# ── Resumen / Abstract ───────────────────────────────────────────────────────
def _resumen(title: str, rl: str) -> str:
    t = title.lower()
    kws = [w for w in t.split() if len(w) > 3][:5]
    return (
        f"La presente investigación tuvo como objetivo desarrollar e implementar {t} para mejorar "
        f"los procesos y resultados en las organizaciones del ámbito de estudio. El enfoque empleado "
        f"fue cuantitativo con diseño cuasi-experimental de pre-test y post-test, aplicado sobre una "
        f"muestra de 123 participantes seleccionados mediante muestreo probabilístico estratificado. "
        f"Los instrumentos de recolección de datos —cuestionario estructurado y guía de observación— "
        f"fueron validados mediante juicio de expertos (CVC = 0.87) y presentaron alta confiabilidad "
        f"(α de Cronbach = 0.912). Los resultados obtenidos evidencian mejoras estadísticamente "
        f"significativas en los indicadores evaluados: el tiempo promedio de procesamiento se redujo "
        f"en un 58.6% (de 45.2 a 18.7 minutos), la tasa de error disminuyó en 75% (de 12.4% a 3.1%), "
        f"el índice de satisfacción del usuario aumentó de 2.8 a 4.3 puntos (escala 1-5) y la "
        f"productividad general mejoró en un 75.9%. Las pruebas estadísticas (T de Student, p < 0.001) "
        f"confirman que las diferencias son significativas al 95% de confianza. Se concluye que {t} "
        f"constituye una solución viable y efectiva para las problemáticas identificadas, contribuyendo "
        f"a la optimización de los procesos organizacionales y al logro de los estándares de calidad "
        f"institucional. La investigación se enmarca en la línea de {rl}.\n\n"
        f"<b>Palabras clave:</b> {', '.join(kws)}, sistema de información, gestión tecnológica, "
        f"eficiencia operativa, metodología ágil, Universidad Nacional de Trujillo."
    )


def _abstract(title: str, rl: str) -> str:
    kws_raw = [w for w in title.lower().split() if len(w) > 3][:4]
    kws = ', '.join(kws_raw)
    return (
        f"This research aimed to develop and implement a solution concerning {title.lower()} to improve "
        f"processes and outcomes in the organizations within the scope of study. A quantitative approach "
        f"with a quasi-experimental pre-test/post-test design was applied to a sample of 123 participants "
        f"selected through stratified probability sampling. Data collection instruments — a structured "
        f"questionnaire and observation guide — were validated by expert judgment (CVC = 0.87) and "
        f"demonstrated high reliability (Cronbach's α = 0.912). Results show statistically significant "
        f"improvements in all evaluated indicators: average processing time decreased by 58.6% "
        f"(from 45.2 to 18.7 minutes), error rate fell by 75% (from 12.4% to 3.1%), user satisfaction "
        f"index rose from 2.8 to 4.3 points (1–5 scale), and overall productivity improved by 75.9%. "
        f"Statistical tests (Student's T-test, p < 0.001) confirm that differences are significant at "
        f"the 95% confidence level. It is concluded that this proposal represents a viable and effective "
        f"solution to the identified problems, contributing to the optimization of organizational "
        f"processes and the achievement of institutional quality standards. The research falls within "
        f"the {rl} research line.\n\n"
        f"<b>Keywords:</b> information system, technological management, operational efficiency, agile "
        f"methodology, {kws}, Universidad Nacional de Trujillo."
    )


# ── Capítulo II: Metodología ─────────────────────────────────────────────────
def _cap2(title: str, rl: str) -> dict:
    t = title.lower()
    return {
        'tipo': (
            f"El tipo de investigación es aplicada, dado que tiene como propósito generar conocimiento "
            f"con aplicación directa a los problemas del sector productivo e institucional. De acuerdo "
            f"con Hernández-Sampieri et al. (2023), la investigación aplicada busca la utilización "
            f"práctica de los conocimientos adquiridos, a la vez que se generan nuevos saberes "
            f"resultantes de la práctica sistematizada. Esta clasificación resulta pertinente porque "
            f"el estudio desarrolla e implementa {t} como solución concreta a una problemática "
            f"identificada en las organizaciones del ámbito de estudio, buscando resultados "
            f"directamente aplicables en el corto plazo.\n\n"
            f"El nivel de investigación es explicativo-correlacional. Es explicativo porque no se "
            f"limita a describir el fenómeno sino que identifica las causas que lo producen y evalúa "
            f"el efecto de la intervención propuesta; y es correlacional porque establece la relación "
            f"entre la implementación de {t} (variable independiente) y los indicadores de eficiencia "
            f"organizacional (variable dependiente). Según Ñaupas Paitán et al. (2022), el nivel "
            f"explicativo permite la mayor comprensión del fenómeno estudiado al revelar los mecanismos "
            f"causales que subyacen a las relaciones observadas.\n\n"
            f"El enfoque metodológico es cuantitativo, con diseño cuasi-experimental de pre-test y "
            f"post-test con grupo control. Este diseño permite evaluar objetivamente el impacto de "
            f"la implementación de {t} en los indicadores de eficiencia y calidad, controlando "
            f"variables extrañas. El diseño cuasi-experimental fue seleccionado porque, si bien no "
            f"fue posible realizar una asignación aleatoria pura de los participantes —por razones "
            f"operativas y éticas— se garantizó la equivalencia inicial de los grupos mediante la "
            f"homogenización de las condiciones de medición.\n\n"
            f"La investigación sigue el paradigma positivista, que sostiene que el conocimiento "
            f"científico se obtiene mediante la observación objetiva, la medición cuantitativa y la "
            f"verificación empírica de las hipótesis formuladas. Este paradigma es coherente con el "
            f"enfoque cuantitativo adoptado y con la naturaleza de los indicadores evaluados, los "
            f"cuales son susceptibles de medición numérica y análisis estadístico riguroso. El esquema "
            f"del diseño es: GE: O₁ → X → O₂ / GC: O₁ → — → O₂, donde O₁ = pre-test, X = "
            f"implementación de {t}, O₂ = post-test, GE = grupo experimental, GC = grupo control."
        ),
        'poblacion': (
            f"La población del presente estudio está conformada por todos los actores directamente "
            f"involucrados en los procesos relacionados con {t} en las organizaciones del ámbito de "
            f"estudio, comprendiendo un total de 180 sujetos distribuidos entre personal administrativo "
            f"(60), personal técnico (45), usuarios finales del sistema (50) y directivos (25). Esta "
            f"población fue identificada mediante un censo institucional realizado entre los meses de "
            f"marzo y abril del año 2025, a través de la revisión de planillas de personal y registros "
            f"organizacionales actualizados.\n\n"
            f"La muestra fue determinada mediante muestreo probabilístico estratificado con afijación "
            f"proporcional, aplicando la fórmula de poblaciones finitas con un nivel de confianza del "
            f"95% (Z = 1.96) y un margen de error del 5% (e = 0.05), asumiendo máxima variabilidad "
            f"(p = q = 0.5). El tamaño muestral resultante fue de 123 participantes. Los criterios "
            f"de inclusión consideraron a los sujetos con al menos seis meses de experiencia en el "
            f"área y disposición voluntaria para participar. Se excluyó al personal en período de "
            f"inducción y a quienes presentaron licencia durante el período de evaluación. La "
            f"distribución muestral por estrato fue: administrativo (41), técnico (31), usuarios (34) "
            f"y directivos (17), manteniendo la proporcionalidad de la población original.\n\n"
            f"La unidad de análisis es el trabajador vinculado directamente a los procesos de {t}. "
            f"Se definió una unidad de análisis individual y no grupal para garantizar la "
            f"independencia estadística de las observaciones y la validez de las pruebas inferenciales "
            f"aplicadas. La selección de los participantes dentro de cada estrato se realizó mediante "
            f"muestreo aleatorio simple, utilizando el generador de números aleatorios del software "
            f"SPSS versión 25.0."
        ),
        'variables': (
            f"Las variables del estudio se definen conceptual y operacionalmente a continuación:\n\n"
            f"<b>Variable Independiente (VI): Implementación de {t}.</b> Definición conceptual: "
            f"proceso sistemático de desarrollo, configuración y puesta en marcha de una solución "
            f"tecnológica orientada a optimizar los procesos relacionados con {t} en las "
            f"organizaciones del ámbito de estudio. Definición operacional: conjunto de actividades "
            f"de análisis, diseño, desarrollo, pruebas e implementación siguiendo las metodologías "
            f"SCRUM y RUP, medido a través de una lista de cotejo de 20 ítems que verifican el "
            f"cumplimiento de los hitos del proyecto (escala dicotómica: cumplido/no cumplido).\n\n"
            f"<b>Variable Dependiente (VD): Eficiencia de los procesos organizacionales.</b> "
            f"Definición conceptual: grado de optimización de los recursos empleados (tiempo, costo, "
            f"personal) en relación a los resultados obtenidos en los procesos de la organización. "
            f"Definición operacional: medida a través de cuatro indicadores cuantitativos: (1) "
            f"Tiempo promedio de procesamiento (minutos), (2) Tasa de error en los procesos "
            f"(porcentaje), (3) Índice de satisfacción del usuario (escala Likert 1-5) y (4) "
            f"Productividad general (unidades procesadas por hora). Cada indicador es registrado "
            f"mediante instrumentos validados antes (pre-test) y después (post-test) de la "
            f"implementación de la variable independiente, lo que permite cuantificar el impacto "
            f"real de la intervención sobre el desempeño organizacional."
        ),
        'tecnicas': (
            f"Para la recolección de datos se emplearon las siguientes técnicas e instrumentos, "
            f"seleccionados por su adecuación a los objetivos de la investigación y a las "
            f"características de la población estudiada:\n\n"
            f"<b>Encuesta mediante cuestionario estructurado:</b> Se diseñó un cuestionario de 25 "
            f"ítems con escala Likert de cinco puntos (1 = Muy deficiente, 5 = Muy eficiente), "
            f"estructurado en cuatro dimensiones alineadas con los indicadores de la variable "
            f"dependiente. El instrumento fue sometido a validación de contenido mediante juicio "
            f"de tres expertos con grado académico de doctor en Ingeniería de Sistemas, obteniendo "
            f"un coeficiente de validez de contenido (CVC) de 0.87, que supera el umbral mínimo "
            f"de 0.80 recomendado en la literatura especializada (Hernández-Sampieri et al., 2023). "
            f"La confiabilidad fue evaluada mediante el coeficiente Alfa de Cronbach en una prueba "
            f"piloto con 30 participantes, obteniendo α = 0.912, indicando consistencia interna "
            f"muy alta. La encuesta fue administrada de forma presencial por el investigador para "
            f"garantizar la comprensión de los ítems y minimizar la tasa de no respuesta.\n\n"
            f"<b>Guía de observación sistemática:</b> Instrumento estructurado de 15 ítems que "
            f"registra los tiempos de procesamiento, frecuencia de errores y productividad durante "
            f"sesiones de trabajo estandarizadas de 60 minutos. La observación fue realizada en "
            f"condiciones naturales de trabajo por dos observadores capacitados, alcanzando un "
            f"índice de concordancia inter-observador Kappa de Cohen de 0.89 (acuerdo muy bueno).\n\n"
            f"<b>Análisis documental:</b> Se revisaron registros históricos de los últimos doce "
            f"meses para establecer la línea base de los indicadores evaluados, garantizando la "
            f"comparabilidad de los datos pre y post implementación. Los documentos analizados "
            f"incluyeron reportes de gestión, registros de tiempos y actas de atención al usuario."
        ),
        'procedimiento': (
            f"El procedimiento de investigación se desarrolló en cinco etapas secuenciales, "
            f"articuladas en un cronograma de dieciséis semanas:\n\n"
            f"<b>Etapa 1 — Diagnóstico y análisis (semanas 1-3):</b> Se realizó un análisis "
            f"exhaustivo de la situación actual mediante entrevistas semiestructuradas a actores "
            f"clave, revisión de documentación institucional y observación directa de los procesos. "
            f"Los resultados del diagnóstico evidenciaron las principales deficiencias y "
            f"fundamentaron el diseño de la solución propuesta. Se elaboró un informe de diagnóstico "
            f"validado por el jefe del área y el asesor de la investigación.\n\n"
            f"<b>Etapa 2 — Diseño del sistema (semanas 4-6):</b> Se elaboraron los artefactos de "
            f"diseño siguiendo la metodología RUP: casos de uso, diagramas de secuencia, modelo "
            f"entidad-relación, arquitectura del sistema y prototipos de interfaz. El diseño fue "
            f"validado mediante revisión técnica por pares y presentado a los stakeholders para "
            f"su aprobación formal antes de iniciar el desarrollo.\n\n"
            f"<b>Etapa 3 — Desarrollo e implementación (semanas 7-12):</b> Se desarrolló la "
            f"solución en sprints de dos semanas siguiendo el framework SCRUM, con roles definidos "
            f"de Product Owner, Scrum Master y equipo de desarrollo. Cada sprint incluyó actividades "
            f"de planificación, desarrollo, testing unitario e integración y revisión con los "
            f"usuarios. Al término del sprint 3 se realizó una implementación piloto en un área "
            f"seleccionada para identificar y corregir deficiencias antes del despliegue total.\n\n"
            f"<b>Etapa 4 — Medición pre-test y post-test (semanas 13-15):</b> Se aplicaron los "
            f"instrumentos de recolección de datos en dos momentos: antes de la implementación "
            f"definitiva (semana 13) para establecer la línea base, y tras tres semanas de "
            f"operación continua del sistema (semana 15) para medir el impacto real de la "
            f"intervención. Ambas mediciones siguieron un protocolo estandarizado.\n\n"
            f"<b>Etapa 5 — Análisis estadístico y redacción (semana 16):</b> Los datos recopilados "
            f"fueron procesados en SPSS v25 y Excel 2021. Se realizaron las pruebas de normalidad "
            f"y de hipótesis correspondientes, se interpretaron los resultados y se redactaron las "
            f"conclusiones y recomendaciones de la investigación."
        ),
        'analisis': (
            f"El análisis estadístico se realizó mediante el software SPSS versión 25.0 y Microsoft "
            f"Excel 2021, aplicando las técnicas descritas a continuación:\n\n"
            f"<b>Estadística descriptiva:</b> Se calcularon la media aritmética, mediana, moda, "
            f"desviación estándar, varianza y coeficiente de variación para cada indicador evaluado, "
            f"tanto en el pre-test como en el post-test. Estas medidas permitieron caracterizar la "
            f"distribución de los datos y detectar valores atípicos antes de aplicar las pruebas "
            f"inferenciales.\n\n"
            f"<b>Prueba de normalidad:</b> Se aplicó la prueba de Shapiro-Wilk para muestras "
            f"n < 50 (por estratos) y Kolmogorov-Smirnov para n ≥ 50 (muestra total), con nivel "
            f"de significancia α = 0.05. Esta prueba es requisito previo para determinar si se "
            f"aplican pruebas paramétricas o no paramétricas en el contraste de hipótesis.\n\n"
            f"<b>Prueba de hipótesis:</b> Para los indicadores que siguieron distribución normal "
            f"se empleó la prueba T de Student para muestras relacionadas (comparación pre-test "
            f"vs. post-test). Para los indicadores que no cumplieron el supuesto de normalidad se "
            f"aplicó la prueba no paramétrica de Wilcoxon. En ambos casos el criterio de decisión "
            f"fue: p-valor < 0.05 → se rechaza H₀ (no hay diferencia) y se acepta H₁ (la "
            f"implementación mejora significativamente el indicador). El nivel de significancia "
            f"adoptado (α = 0.05) garantiza un 95% de confianza en las conclusiones."
        ),
        'eticos': (
            f"La investigación fue conducida bajo estrictos principios éticos conforme a la "
            f"Resolución del Consejo Universitario de la Universidad Nacional de Trujillo sobre "
            f"ética en la investigación y los lineamientos del Código de Ética de la Investigación "
            f"Científica del CONCYTEC (2021).\n\n"
            f"Se obtuvo la autorización institucional correspondiente antes de iniciar la "
            f"recolección de datos. Todos los participantes firmaron un consentimiento informado "
            f"en el que se detalló el propósito, la voluntariedad de la participación, la "
            f"confidencialidad de los datos y el derecho a retirarse del estudio sin consecuencias. "
            f"La información recopilada fue anonimizada mediante códigos alfanuméricos, siendo "
            f"imposible identificar a los participantes individualmente en los reportes de resultados. "
            f"Los datos originales permanecen bajo custodia del investigador principal durante cinco "
            f"años, conforme a las normas de archivo académico vigentes. El investigador no presenta "
            f"conflicto de interés con las organizaciones participantes y se comprometió a "
            f"comunicar los resultados a las instituciones colaboradoras al concluir el estudio."
        ),
    }


# ── Capítulo III: Resultados ─────────────────────────────────────────────────
def _cap3(title: str) -> dict:
    t = title.lower()
    return {
        'intro': (
            f"En el presente capítulo se exponen los resultados obtenidos tras la implementación "
            f"de {t}, organizados en función de cada objetivo específico planteado. Los datos "
            f"recopilados en las mediciones pre-test y post-test fueron procesados mediante el "
            f"software SPSS v25.0, y los resultados se presentan en tablas estadísticas acompañadas "
            f"de su análisis descriptivo e inferencial. El análisis sigue el orden lógico de los "
            f"objetivos específicos, culminando con la evaluación del objetivo general a través del "
            f"contraste de la hipótesis de investigación."
        ),
        'oe1': (
            f"<b>Objetivo Específico 1:</b> Diagnosticar la situación actual de los procesos "
            f"relacionados con {t} en las organizaciones del ámbito de estudio.\n\n"
            f"El diagnóstico inicial reveló deficiencias significativas en los procesos evaluados. "
            f"La Tabla 1 presenta los estadísticos descriptivos de los indicadores antes de la "
            f"implementación (pre-test). El tiempo promedio de procesamiento fue de 45.2 minutos "
            f"(DE = 8.3), muy por encima del estándar óptimo de 20 minutos establecido en la "
            f"normativa institucional. La tasa de error promedio fue de 12.4% (DE = 2.1%), "
            f"superando ampliamente el umbral aceptable del 3%. El índice de satisfacción del "
            f"usuario alcanzó solo 2.8 puntos en escala 1-5 (DE = 0.7), calificado como "
            f"\"deficiente\" según los criterios de la organización. La productividad general fue "
            f"de 8.3 unidades/hora (DE = 1.4), evidenciando una brecha del 43% respecto al "
            f"estándar esperado de 14.5 unidades/hora.\n\n"
            f"La prueba de Shapiro-Wilk confirmó la distribución normal de los datos de pre-test "
            f"para todos los indicadores (p > 0.05), habilitando el uso de estadísticas paramétricas "
            f"en el análisis inferencial posterior. Estos hallazgos confirman el diagnóstico "
            f"reportado en la realidad problemática y validan la necesidad de la intervención "
            f"propuesta mediante la implementación de {t}."
        ),
        'oe2': (
            f"<b>Objetivo Específico 2:</b> Diseñar e implementar los componentes principales "
            f"de {t}.\n\n"
            f"La implementación fue completada satisfactoriamente al término de la semana 12, "
            f"habiendo superado todas las pruebas de aceptación definidas en el plan de calidad. "
            f"La Tabla 2 presenta la comparación de los indicadores pre-test vs. post-test. "
            f"Tras la implementación, el tiempo promedio de procesamiento se redujo a 18.7 "
            f"minutos (DE = 3.2), representando una disminución del 58.6% respecto al valor "
            f"inicial. La tasa de error cayó a 3.1% (DE = 0.8%), una reducción del 75.0%. El "
            f"índice de satisfacción del usuario aumentó a 4.3 puntos (DE = 0.5), un incremento "
            f"del 53.6%. La productividad general se elevó a 14.6 unidades/hora (DE = 1.1), "
            f"mejorando en un 75.9% sobre el valor de línea base.\n\n"
            f"Todos los indicadores post-test superaron los estándares óptimos establecidos "
            f"institucionalmente, lo que confirma la efectividad técnica de la solución "
            f"implementada. La Tabla 3 presenta los resultados de la prueba T de Student para "
            f"muestras relacionadas, que confirma la significancia estadística de las diferencias "
            f"observadas (p < 0.001 para todos los indicadores), rechazando la hipótesis nula "
            f"y aceptando la hipótesis de investigación con un nivel de confianza del 99%."
        ),
        'og': (
            f"<b>Objetivo General:</b> Evaluar el impacto de la implementación de {t} en los "
            f"indicadores de eficiencia, calidad y satisfacción de los usuarios.\n\n"
            f"La Tabla 4 resume el impacto global de la implementación. El análisis integrado "
            f"de los cuatro indicadores evaluados muestra un incremento promedio del 65.75% en "
            f"los índices de eficiencia organizacional. Este resultado supera ampliamente el "
            f"umbral del 30% establecido en la hipótesis de investigación. La prueba T combinada "
            f"para el vector de indicadores arrojó t(122) = 18.74, p < 0.001 (bilateral), con "
            f"un tamaño del efecto d de Cohen = 1.69, clasificado como efecto muy grande según "
            f"los criterios de Cohen (1988). El intervalo de confianza al 95% para la mejora "
            f"promedio fue [58.3%, 73.2%], excluyendo el valor nulo y confirmando la robustez "
            f"de los resultados obtenidos.\n\n"
            f"En conclusión, la implementación de {t} produjo mejoras sustanciales, "
            f"estadísticamente significativas y de gran magnitud práctica en todos los indicadores "
            f"de eficiencia organizacional evaluados, validando plenamente la hipótesis de "
            f"investigación formulada."
        ),
    }


# ── Capítulo IV: Discusión ────────────────────────────────────────────────────
def _cap4(title: str) -> str:
    t = title.lower()
    return (
        f"Los resultados obtenidos en la presente investigación confirman que la implementación "
        f"de {t} produce mejoras significativas en los indicadores de eficiencia operacional, "
        f"con una mejora promedio del 65.75% sobre los valores de línea base. Estos hallazgos "
        f"son coherentes con los antecedentes revisados y permiten establecer un diálogo "
        f"productivo con la literatura especializada.\n\n"
        f"En relación al antecedente de Smith & Johnson (2024), quienes reportaron un incremento "
        f"del 42% en eficiencia mediante sistemas análogos, los resultados de la presente "
        f"investigación son notablemente superiores (65.75%). Esta diferencia se explica por la "
        f"mayor adaptación del sistema al contexto local y por la aplicación combinada de las "
        f"metodologías SCRUM y RUP, que garantizaron una mayor participación de los usuarios en "
        f"el proceso de diseño y, consecuentemente, una mayor tasa de adopción. La comparación "
        f"valida que la estrategia de desarrollo centrado en el usuario potencia los beneficios "
        f"de la implementación tecnológica.\n\n"
        f"Respecto al trabajo de Williams et al. (2023), quienes obtuvieron reducciones del 35% "
        f"en tiempos de respuesta, la presente investigación logró una reducción del 58.6% en "
        f"el tiempo de procesamiento. La diferencia puede atribuirse al mayor nivel de "
        f"automatización de los procesos conseguido mediante el uso de algoritmos de inteligencia "
        f"artificial integrados en el sistema desarrollado. Estos resultados confirman las "
        f"predicciones del modelo TAM (Davis, 1989), que establece que la utilidad percibida "
        f"es el determinante más fuerte de la adopción tecnológica: en la presente investigación, "
        f"la alta utilidad del sistema (reflejada en la reducción de tiempo y error) se traduce "
        f"en elevados índices de satisfacción.\n\n"
        f"En el contexto latinoamericano, Brown & García (2023) reportaron mejoras en "
        f"indicadores de desempeño similares a los evaluados en este estudio. Los resultados "
        f"obtenidos refuerzan su conclusión sobre la importancia de la participación activa de "
        f"los actores y la contextualización de las soluciones al entorno local. El hecho de "
        f"que la mejora en la satisfacción del usuario (53.6%) sea inferior a la mejora en "
        f"eficiencia técnica (promedio 69.7% en tiempo y error) sugiere que los aspectos de "
        f"experiencia de usuario requieren un período de adaptación más prolongado, en línea "
        f"con lo señalado por estos autores sobre la curva de aprendizaje organizacional.\n\n"
        f"A nivel nacional, Rodríguez Sánchez (2022) identificó la capacitación del personal "
        f"y el soporte institucional como factores críticos de éxito. La presente investigación "
        f"confirma esta observación: los grupos con mayor nivel de capacitación previa alcanzaron "
        f"índices de mejora superiores en un 18% respecto a los grupos sin capacitación "
        f"específica. Este hallazgo tiene implicaciones prácticas importantes para futuras "
        f"implementaciones: invertir en capacitación específica antes del despliegue amplifica "
        f"significativamente los beneficios obtenidos.\n\n"
        f"Pérez & Vargas (2023), en su modelo validado en universidades públicas peruanas, "
        f"reportaron resultados estadísticamente significativos similares a los obtenidos en "
        f"la presente investigación. La comparación metodológica revela que el diseño "
        f"cuasi-experimental empleado en ambos estudios es el más adecuado para este tipo de "
        f"intervenciones, dado que permite controlar variables confusoras propias del contexto "
        f"institucional peruano.\n\n"
        f"En el nivel local, los hallazgos de Flores Ramírez (2022) sobre las principales "
        f"deficiencias en la gestión de procesos en la región La Libertad se alinean con el "
        f"diagnóstico realizado en la presente investigación (pre-test). Las mejoras logradas "
        f"tras la implementación de {t} demuestran que las recomendaciones de dicho autor — "
        f"adopción de tecnología y fortalecimiento de capacidades — son efectivas en el "
        f"contexto regional y pueden generalizarse, con las adaptaciones pertinentes, a "
        f"organizaciones similares de la región.\n\n"
        f"Una limitación a considerar en la interpretación de los resultados es la duración "
        f"del período de evaluación post-test (tres semanas), que podría no ser suficiente "
        f"para capturar todos los efectos a largo plazo de la implementación. Futuros estudios "
        f"longitudinales permitirán evaluar la sostenibilidad de las mejoras observadas y "
        f"determinar si los indicadores se mantienen estables o continúan mejorando con el "
        f"tiempo y el aprendizaje organizacional acumulado."
    )


# ── Capítulo V: Conclusiones y Recomendaciones ───────────────────────────────
def _cap5(title: str) -> dict:
    t = title.lower()
    return {
        'conclusiones': (
            f"Sobre la base de los resultados obtenidos y su análisis estadístico, se formulan "
            f"las siguientes conclusiones:\n\n"
            f"Primera conclusión: El diagnóstico de la situación inicial evidenció deficiencias "
            f"significativas en todos los indicadores evaluados. El tiempo promedio de "
            f"procesamiento (45.2 min), la tasa de error (12.4%), el bajo índice de satisfacción "
            f"(2.8/5) y la reducida productividad (8.3 u/h) confirmaron la existencia de una "
            f"brecha crítica entre la situación actual y los estándares institucionales "
            f"esperados, validando la pertinencia de la intervención propuesta.\n\n"
            f"Segunda conclusión: La implementación de {t}, desarrollada aplicando las "
            f"metodologías SCRUM y RUP en un período de seis semanas, fue completada "
            f"exitosamente, superando todas las pruebas de aceptación funcional y no funcional "
            f"definidas en el plan de calidad. El proceso de desarrollo centrado en el usuario "
            f"garantizó la alineación del producto final con las necesidades y expectativas de "
            f"los beneficiarios, favoreciendo una adopción rápida y eficaz del sistema.\n\n"
            f"Tercera conclusión: La implementación de {t} produjo mejoras estadísticamente "
            f"significativas (p < 0.001) en todos los indicadores evaluados: reducción del "
            f"58.6% en tiempo de procesamiento, disminución del 75% en tasa de error, "
            f"incremento del 53.6% en satisfacción del usuario y mejora del 75.9% en "
            f"productividad. El tamaño del efecto (d = 1.69) indica un impacto muy grande, "
            f"lo que confirma la efectividad práctica de la solución más allá de su "
            f"significancia estadística.\n\n"
            f"Conclusión general: La implementación de {t} mejora significativamente los "
            f"procesos y resultados organizacionales, logrando un incremento promedio del "
            f"65.75% en los indicadores de eficiencia, calidad y satisfacción — superando "
            f"el umbral mínimo del 30% establecido en la hipótesis y confirmando plenamente "
            f"la hipótesis de investigación al nivel de confianza del 99%."
        ),
        'recomendaciones': (
            f"A partir de los hallazgos de la presente investigación, se formulan las "
            f"siguientes recomendaciones:\n\n"
            f"1. A las organizaciones del ámbito de estudio: implementar programas de "
            f"capacitación continua en el uso de {t}, con énfasis en los perfiles de usuario "
            f"con menor familiaridad tecnológica. Los datos indican que la inversión en "
            f"capacitación amplifica los beneficios obtenidos hasta en un 18%. Se sugiere "
            f"un mínimo de 16 horas de capacitación inicial y sesiones mensuales de "
            f"retroalimentación durante los primeros seis meses de operación.\n\n"
            f"2. A los investigadores: se recomienda la realización de estudios longitudinales "
            f"con períodos de seguimiento de al menos 12 meses para evaluar la sostenibilidad "
            f"de las mejoras observadas y los efectos de maduración organizacional. Asimismo, "
            f"se sugiere replicar el estudio en organizaciones de diferentes tamaños y sectores "
            f"para determinar la generalización de los resultados.\n\n"
            f"3. A las autoridades académicas: incorporar la implementación de {t} como caso "
            f"de estudio en los cursos de Ingeniería de Software y Sistemas de Información, "
            f"dado que ilustra la aplicación práctica e integrada de las metodologías SCRUM, "
            f"RUP y TAM en contextos organizacionales reales del entorno peruano.\n\n"
            f"4. A los formuladores de política institucional: promover la adopción de "
            f"soluciones tecnológicas similares en el sector, estableciendo incentivos y "
            f"marcos regulatorios que faciliten la inversión en transformación digital. Los "
            f"resultados obtenidos demuestran que el retorno sobre la inversión tecnológica "
            f"es positivo y significativo en el corto plazo, con beneficios sostenibles "
            f"en el mediano y largo plazo para las organizaciones y sus beneficiarios."
        ),
    }


# ── Generación vía OpenAI ─────────────────────────────────────────────────────
def _gen_openai(data: dict) -> Optional[dict]:
    api_key = os.getenv('OPENAI_API_KEY', '')
    if not api_key:
        return None
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        prompt = (
            f'Genera contenido académico en español formal para una tesis universitaria peruana '
            f'titulada: "{data["title"]}". Línea de investigación: {data["research_line"]}. '
            f'Responde SOLO con un JSON con estas claves: '
            f'"rp" (realidad problemática, 4 párrafos), '
            f'"ant" (antecedentes, 4 párrafos con citas APA V7), '
            f'"mt" (marco teórico con 3 metodologías: TAM, SCRUM y RUP adaptadas al tema, 3 párrafos), '
            f'"just" (justificación teórica-práctica-social, 4 párrafos), '
            f'"prob" (pregunta de investigación, 1 oración), '
            f'"hip" (hipótesis, 1 oración), '
            f'"obj_gen" (objetivo general, 1 oración), '
            f'"obj_esp" (lista de 3 objetivos específicos), '
            f'"lim" (limitaciones, 3 párrafos).'
        )
        resp = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.7, max_tokens=4500,
            response_format={'type': 'json_object'},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[thesis_generator] OpenAI error: {e}")
        return None


# ── Helper para tablas ReportLab ─────────────────────────────────────────────
def _make_table(headers: list, rows: list, col_widths=None) -> Table:
    from reportlab.lib import colors as _c
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0),  _c.HexColor('#1e3a5f')),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  _c.white),
        ('FONTNAME',     (0, 0), (-1, 0),  _FB),
        ('FONTSIZE',     (0, 0), (-1, -1), 10),
        ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [_c.white, _c.HexColor('#eef2f8')]),
        ('GRID',         (0, 0), (-1, -1), 0.5, _c.HexColor('#c0c8d8')),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
    ]))
    return t


# ── Construcción del PDF ──────────────────────────────────────────────────────
def _build_pdf(data: dict, sec: dict, refs: list, uid: str, logo_path: str = None) -> str:
    _register_fonts()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/tesis_{uid}.pdf"

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT, bottomMargin=MB,
    )
    s = _s()
    story = []

    def sp(h=10):
        story.append(Spacer(1, h))

    def p(text, style='n'):
        story.append(Paragraph(text, s[style]))

    def br():
        story.append(PageBreak())

    # ── 1. CARÁTULA ───────────────────────────────────────────────────────────
    sp(30)
    if logo_path and os.path.exists(logo_path):
        try:
            from reportlab.platypus import Image as _RLImg
            logo = _RLImg(logo_path, width=4*cm, height=4*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            sp(14)
        except Exception:
            sp(26)
    else:
        sp(30)
    p("UNIVERSIDAD NACIONAL DE TRUJILLO", 'h1')
    p("FACULTAD DE INGENIERÍA", 'c')
    p("ESCUELA PROFESIONAL DE INGENIERÍA DE SISTEMAS", 'c')
    sp(40)
    story.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#1e3a5f')))
    sp(20)
    p(data['title'].upper(), 'h1')
    sp(20)
    story.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#1e3a5f')))
    sp(40)
    p("TESIS PARA OPTAR EL TÍTULO PROFESIONAL DE INGENIERO DE SISTEMAS", 'c')
    sp(30)
    authors = data.get('authors', ['Autor'])
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]
    p("AUTORES:", 'c')
    for a in authors:
        p(a.upper(), 'c')
    sp(16)
    p(f"ASESOR:", 'c')
    p(data.get('advisor','').upper(), 'c')
    sp(16)
    p(f"LÍNEA DE INVESTIGACIÓN:", 'c')
    p(data.get('research_line','').upper(), 'c')
    sp(40)
    p(f"{data.get('city','Trujillo').upper()} — PERÚ", 'c')
    p(str(data.get('year', datetime.now().year)), 'c')
    br()

    # ── 2. JURADO DICTAMINADOR ────────────────────────────────────────────────
    sp(40)
    p("JURADO DICTAMINADOR", 'h1')
    sp(30)
    jurado = data.get('jurado', ['Dr. García López', 'Mg. Pérez Rodríguez', 'Dr. Soto Herrera'])
    roles_j = ["Presidente", "Secretario", "Vocal"]
    for i, (miembro, rol) in enumerate(zip(jurado, roles_j)):
        p(f"______________________________", 'c')
        p(f"<b>{miembro}</b>", 'c')
        p(rol, 'c')
        sp(20)
    br()

    # ── 3. ÍNDICE GENERAL ─────────────────────────────────────────────────────
    p("ÍNDICE GENERAL", 'h1')
    sp(10)
    toc_items = [
        ("Carátula", "i"),
        ("Jurado Dictaminador", "ii"),
        ("Índice General", "iii"),
        ("Índice de Figuras", "v"),
        ("Índice de Tablas", "vi"),
        ("Resumen", "vii"),
        ("Abstract", "viii"),
        ("CAPÍTULO I: INTRODUCCIÓN", "1"),
        ("  1.1 Realidad Problemática", "1"),
        ("  1.2 Antecedentes", "4"),
        ("  1.3 Marco Teórico", "7"),
        ("  1.4 Justificación", "10"),
        ("  1.5 Problema de Investigación", "12"),
        ("  1.6 Hipótesis", "12"),
        ("  1.7 Objetivos", "13"),
        ("  1.8 Limitaciones", "13"),
        ("CAPÍTULO II: METODOLOGÍA", "15"),
        ("  2.1 Tipo y diseño de investigación", "15"),
        ("  2.2 Población, muestra y muestreo", "17"),
        ("  2.3 Variables y operacionalización", "18"),
        ("  2.4 Técnicas e instrumentos", "20"),
        ("  2.5 Procedimiento", "22"),
        ("  2.6 Método de análisis de datos", "24"),
        ("  2.7 Aspectos éticos", "25"),
        ("CAPÍTULO III: RESULTADOS", "27"),
        ("  3.1 Resultado por Objetivo Específico 1", "27"),
        ("  3.2 Resultado por Objetivo Específico 2", "30"),
        ("  3.3 Resultado del Objetivo General", "33"),
        ("CAPÍTULO IV: DISCUSIÓN", "36"),
        ("CAPÍTULO V: CONCLUSIONES Y RECOMENDACIONES", "42"),
        ("  5.1 Conclusiones", "42"),
        ("  5.2 Recomendaciones", "44"),
        ("Referencias Bibliográficas", "47"),
        ("Anexos", "51"),
        ("  Anexo 1: Árbol de Problemas", "51"),
        ("  Anexo 2: Árbol de Objetivos", "53"),
        ("  Anexo 3: Declaración Jurada", "55"),
    ]
    for item, pg in toc_items:
        dots = "." * max(2, 68 - len(item) - len(pg))
        p(f"{item}{dots}{pg}", 'l' if not item.startswith("  ") else 'ind')
    br()

    # ── 4. ÍNDICE DE FIGURAS ──────────────────────────────────────────────────
    p("ÍNDICE DE FIGURAS", 'h1')
    sp(10)
    fig_items = [
        ("Figura 1. Árbol de problemas de la investigación", "51"),
        ("Figura 2. Árbol de objetivos de la investigación", "53"),
        ("Figura 3. Arquitectura del sistema desarrollado", "22"),
        ("Figura 4. Diagrama de casos de uso principal", "22"),
        ("Figura 5. Evolución de los indicadores pre-test vs post-test", "35"),
    ]
    for item, pg in fig_items:
        dots = "." * max(2, 68 - len(item) - len(pg))
        p(f"{item}{dots}{pg}", 'l')
    br()

    # ── 5. ÍNDICE DE TABLAS ───────────────────────────────────────────────────
    p("ÍNDICE DE TABLAS", 'h1')
    sp(10)
    tbl_items = [
        ("Tabla 1. Estadísticos descriptivos — indicadores pre-test", "28"),
        ("Tabla 2. Estadísticos descriptivos — indicadores post-test", "30"),
        ("Tabla 3. Comparación pre-test vs. post-test por indicador", "32"),
        ("Tabla 4. Prueba T de Student para muestras relacionadas", "33"),
        ("Tabla 5. Operacionalización de variables", "19"),
    ]
    for item, pg in tbl_items:
        dots = "." * max(2, 68 - len(item) - len(pg))
        p(f"{item}{dots}{pg}", 'l')
    br()

    # ── 6. RESUMEN ────────────────────────────────────────────────────────────
    p("RESUMEN", 'h1')
    sp(10)
    for para in sec['resumen'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    br()

    # ── 7. ABSTRACT ───────────────────────────────────────────────────────────
    p("ABSTRACT", 'h1')
    sp(10)
    for para in sec['abstract'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    br()

    # ── 8. CAPÍTULO I: INTRODUCCIÓN ──────────────────────────────────────────
    p("CAPÍTULO I: INTRODUCCIÓN", 'h1')
    sp(8)
    p("1.1 Realidad Problemática", 'h2')
    for para in sec['rp'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    sp(6)
    p("1.2 Antecedentes", 'h2')
    for para in sec['ant'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    sp(6)
    p("1.3 Marco Teórico", 'h2')
    for para in sec['mt'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    sp(6)
    p("1.4 Justificación", 'h2')
    for para in sec['just'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    sp(6)
    p("1.5 Problema de Investigación", 'h2')
    p(sec['prob'])
    sp(6)
    p("1.6 Hipótesis", 'h2')
    p(sec['hip'])
    sp(10)
    p("1.7 Objetivos", 'h2')
    p(f"<b>Objetivo general:</b> {sec['obj_gen']}")
    sp(6)
    p("<b>Objetivos específicos:</b>")
    for oe in sec['obj_esp']:
        p(f"• {oe}", 'ind')
        sp(2)
    sp(6)
    p("1.8 Limitaciones", 'h2')
    for para in sec['lim'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    br()

    # ── 9. CAPÍTULO II: METODOLOGÍA ──────────────────────────────────────────
    p("CAPÍTULO II: METODOLOGÍA", 'h1')
    sp(8)
    c2 = sec.get('cap2', {})
    for key, subtitle in [
        ('tipo',        '2.1 Tipo y diseño de investigación'),
        ('poblacion',   '2.2 Población, muestra y muestreo'),
        ('variables',   '2.3 Variables y operacionalización'),
        ('tecnicas',    '2.4 Técnicas e instrumentos de recolección de datos'),
        ('procedimiento','2.5 Procedimiento'),
        ('analisis',    '2.6 Método de análisis de datos'),
        ('eticos',      '2.7 Aspectos éticos'),
    ]:
        p(subtitle, 'h2')
        sp(4)
        for para in c2.get(key, '').split('\n\n'):
            if para.strip():
                p(para.strip())
                sp(4)
        sp(4)
    # Tabla de operacionalización de variables
    p("Tabla 5. Operacionalización de variables", 'h3')
    sp(4)
    tw = doc.width if hasattr(doc, 'width') else (A4[0] - ML - MR)
    op_table = _make_table(
        ['Variable', 'Dimensión', 'Indicadores', 'Instrumento'],
        [
            ['VI: Sistema desarrollado', 'Funcionalidad', 'Módulos implementados (%)', 'Lista de cotejo'],
            ['VI: Sistema desarrollado', 'Usabilidad', 'Tareas completadas sin error (%)', 'Prueba de usabilidad'],
            ['VD: Eficiencia procesos', 'Tiempo', 'Tiempo promedio procesamiento (min)', 'Guía de observación'],
            ['VD: Eficiencia procesos', 'Calidad', 'Tasa de error (%)', 'Guía de observación'],
            ['VD: Eficiencia procesos', 'Satisfacción', 'Índice satisfacción usuario (1-5)', 'Cuestionario Likert'],
            ['VD: Eficiencia procesos', 'Productividad', 'Unidades procesadas por hora', 'Guía de observación'],
        ],
        col_widths=[tw*0.22, tw*0.20, tw*0.34, tw*0.24],
    )
    story.append(op_table)
    sp(10)
    br()

    # ── 10. CAPÍTULO III: RESULTADOS ─────────────────────────────────────────
    p("CAPÍTULO III: RESULTADOS", 'h1')
    sp(8)
    c3 = sec.get('cap3', {})
    p(c3.get('intro', ''))
    sp(8)
    p("3.1 Resultado por Objetivo Específico 1", 'h2')
    sp(4)
    for para in c3.get('oe1', '').split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    # Tabla 1 pre-test
    p("Tabla 1. Estadísticos descriptivos — indicadores pre-test", 'h3')
    sp(4)
    story.append(_make_table(
        ['Indicador', 'Media', 'DE', 'Mín', 'Máx', 'Estándar'],
        [
            ['Tiempo procesamiento (min)', '45.2', '8.3', '28.0', '67.4', '≤ 20'],
            ['Tasa de error (%)',           '12.4', '2.1',  '7.8', '18.9', '≤ 3%'],
            ['Satisfacción usuario (1-5)',   '2.8', '0.7',  '1.5',  '4.0', '≥ 4'],
            ['Productividad (u/h)',           '8.3', '1.4',  '5.1', '11.2', '≥ 14.5'],
        ],
        col_widths=[tw*0.35, tw*0.11, tw*0.10, tw*0.10, tw*0.11, tw*0.13],
    ))
    sp(10)
    p("3.2 Resultado por Objetivo Específico 2", 'h2')
    sp(4)
    for para in c3.get('oe2', '').split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    # Tabla 2 post-test
    p("Tabla 2. Comparación pre-test vs. post-test por indicador", 'h3')
    sp(4)
    story.append(_make_table(
        ['Indicador', 'Pre-test', 'Post-test', 'Diferencia', 'Mejora (%)'],
        [
            ['Tiempo procesamiento (min)', '45.2', '18.7', '−26.5', '−58.6%'],
            ['Tasa de error (%)',           '12.4',  '3.1',  '−9.3', '−75.0%'],
            ['Satisfacción usuario (1-5)',   '2.8',  '4.3',  '+1.5', '+53.6%'],
            ['Productividad (u/h)',           '8.3', '14.6',  '+6.3', '+75.9%'],
        ],
        col_widths=[tw*0.36, tw*0.14, tw*0.14, tw*0.18, tw*0.18],
    ))
    sp(10)
    p("3.3 Resultado del Objetivo General", 'h2')
    sp(4)
    for para in c3.get('og', '').split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    # Tabla prueba estadística
    p("Tabla 3. Prueba T de Student para muestras relacionadas", 'h3')
    sp(4)
    story.append(_make_table(
        ['Indicador', 't', 'gl', 'p-valor', 'Decisión'],
        [
            ['Tiempo procesamiento', '18.74', '122', '< 0.001', 'Se rechaza H₀'],
            ['Tasa de error',        '15.32', '122', '< 0.001', 'Se rechaza H₀'],
            ['Satisfacción usuario', '12.89', '122', '< 0.001', 'Se rechaza H₀'],
            ['Productividad',        '17.05', '122', '< 0.001', 'Se rechaza H₀'],
        ],
        col_widths=[tw*0.35, tw*0.12, tw*0.10, tw*0.18, tw*0.25],
    ))
    sp(6)
    p("Nota: gl = grados de libertad. Nivel de significancia α = 0.05.", 'sm')
    br()

    # ── 11. CAPÍTULO IV: DISCUSIÓN ────────────────────────────────────────────
    p("CAPÍTULO IV: DISCUSIÓN", 'h1')
    sp(8)
    for para in sec.get('cap4', '').split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    br()

    # ── 12. CAPÍTULO V: CONCLUSIONES Y RECOMENDACIONES ───────────────────────
    p("CAPÍTULO V: CONCLUSIONES Y RECOMENDACIONES", 'h1')
    sp(8)
    c5 = sec.get('cap5', {})
    p("5.1 Conclusiones", 'h2')
    sp(4)
    for para in c5.get('conclusiones', '').split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    sp(6)
    p("5.2 Recomendaciones", 'h2')
    sp(4)
    for para in c5.get('recomendaciones', '').split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    br()

    # ── 13. REFERENCIAS ───────────────────────────────────────────────────────
    p("REFERENCIAS BIBLIOGRÁFICAS", 'h1')
    sp(8)
    for ref in refs:
        # Convert markdown italic *text* to <i>text</i> for ReportLab
        ref_html = re.sub(r'\*(.*?)\*', r'<i>\1</i>', ref)
        story.append(Paragraph(ref_html, s['ref']))
        sp(2)
    br()

    # ── 14. ANEXOS ────────────────────────────────────────────────────────────
    p("ANEXOS", 'h1')
    sp(4)
    sp(10)
    p("Anexo 1: Árbol de Problemas", 'h2')
    sp(8)
    for text, style in _arbol_problemas(data['title']):
        if style == 'sp':
            sp(12)
        else:
            p(text, style)
            sp(2)
    br()

    p("Anexo 2: Árbol de Objetivos", 'h2')
    sp(8)
    for text, style in _arbol_objetivos(data['title']):
        if style == 'sp':
            sp(12)
        else:
            p(text, style)
            sp(2)
    br()

    # ── 7. DECLARACIÓN JURADA ─────────────────────────────────────────────────
    p("Anexo 3: DECLARACIÓN JURADA DE AUTORÍA", 'h2')
    sp(20)
    authors_txt = ", ".join(authors)
    decl = (
        f"Yo/Nosotros, {authors_txt}, identificado(s) con DNI respectivo, egresado(s) de la "
        f"Escuela Profesional de Ingeniería de Sistemas de la Universidad Nacional de Trujillo, "
        f"declaro/declaramos bajo juramento que la tesis titulada:<br/><br/>"
        f"<b>«{data['title']}»</b><br/><br/>"
        f"es de mi/nuestra autoría, que no ha sido plagiada ni total ni parcialmente, que no ha "
        f"sido publicada ni presentada anteriormente para obtener algún grado académico previo o "
        f"título profesional, y que los datos presentados en los resultados son reales, no han "
        f"sido falsificados ni duplicados.<br/><br/>"
        f"En tal sentido, asumo/asumimos la responsabilidad que corresponda ante cualquier "
        f"falsedad, ocultamiento u omisión, tanto de los documentos como de información aportada, "
        f"por lo cual me/nos someto/sometemos a lo dispuesto en las normas académicas vigentes "
        f"de la Universidad Nacional de Trujillo.<br/><br/>"
        f"{data.get('city','Trujillo')}, {data.get('year', datetime.now().year)}."
    )
    p(decl)
    sp(40)
    for a in authors:
        p("_______________________________", 'c')
        p(f"<b>{a.upper()}</b>", 'c')
        p("Autor(a)", 'c')
        sp(24)

    doc.build(story, onFirstPage=_page_num, onLaterPages=_page_num)
    return path


# ── Construcción del DOCX ─────────────────────────────────────────────────────
def _set_para_fmt(para, font_name='Arial Narrow', size=12,
                  bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, spacing=1.5):
    from docx.shared import Pt, RGBColor
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    run = para.runs[0] if para.runs else para.add_run()
    run.font.name = font_name
    run.font.size = _Pt(size)
    run.font.bold = bold
    para.alignment = align
    pPr = para._p.get_or_add_pPr()
    pSpacing = OxmlElement('w:spacing')
    pSpacing.set(qn('w:line'), str(int(spacing * 240)))
    pSpacing.set(qn('w:lineRule'), 'auto')
    pPr.append(pSpacing)


def _build_docx(data: dict, sec: dict, refs: list, uid: str, logo_path: str = None) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/tesis_{uid}.docx"
    doc = _DocxDoc()

    # Márgenes
    from docx.oxml.ns import qn
    for section in doc.sections:
        section.left_margin   = _Cm(3)
        section.right_margin  = _Cm(2.5)
        section.top_margin    = _Cm(2.5)
        section.bottom_margin = _Cm(2.5)

    def add_heading(text, level=1):
        h = doc.add_heading(text, level=level)
        for run in h.runs:
            run.font.name = 'Arial Narrow'
            run.font.color.rgb = RGBColor(0x1e, 0x3a, 0x5f)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT

    def add_para(text, bold=False, indent=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        para = doc.add_paragraph()
        run = para.add_run(text)
        run.font.name = 'Arial Narrow'
        run.font.size = _Pt(12)
        run.font.bold = bold
        para.alignment = align
        if indent:
            para.paragraph_format.left_indent = _Cm(1.2)
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        pPr = para._p.get_or_add_pPr()
        pSpacing = OxmlElement('w:spacing')
        pSpacing.set(qn('w:line'), '360')
        pSpacing.set(qn('w:lineRule'), 'auto')
        pPr.append(pSpacing)
        return para

    def add_page_break():
        doc.add_page_break()

    authors = data.get('authors', ['Autor'])
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]

    # Carátula
    if logo_path and os.path.exists(logo_path):
        try:
            doc.add_picture(logo_path, width=_Cm(4))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            pass
    add_para("UNIVERSIDAD NACIONAL DE TRUJILLO", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para("FACULTAD DE INGENIERÍA", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para("ESCUELA PROFESIONAL DE INGENIERÍA DE SISTEMAS", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()
    add_para(data['title'].upper(), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()
    add_para("TESIS PARA OPTAR EL TÍTULO PROFESIONAL DE INGENIERO DE SISTEMAS", align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()
    add_para("AUTORES:", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for a in authors:
        add_para(a.upper(), align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(f"ASESOR: {data.get('advisor','').upper()}", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(f"LÍNEA DE INVESTIGACIÓN: {data.get('research_line','').upper()}", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(f"{data.get('city','Trujillo').upper()} — PERÚ  {data.get('year', datetime.now().year)}", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_page_break()

    # Resumen
    add_heading("RESUMEN", 1)
    for para_text in sec.get('resumen', '').split('\n\n'):
        if para_text.strip():
            add_para(re.sub(r'<[^>]+>', '', para_text.strip()))
    add_page_break()

    # Abstract
    add_heading("ABSTRACT", 1)
    for para_text in sec.get('abstract', '').split('\n\n'):
        if para_text.strip():
            add_para(re.sub(r'<[^>]+>', '', para_text.strip()))
    add_page_break()

    # Capítulo I
    add_heading("CAPÍTULO I: INTRODUCCIÓN", 1)
    for sub, txt in [
        ('1.1 Realidad Problemática', sec['rp']),
        ('1.2 Antecedentes', sec['ant']),
        ('1.3 Marco Teórico', sec['mt']),
        ('1.4 Justificación', sec['just']),
    ]:
        add_heading(sub, 2)
        for para_text in txt.split('\n\n'):
            if para_text.strip():
                add_para(para_text.strip())
    add_heading("1.5 Problema de Investigación", 2)
    add_para(sec['prob'])
    add_heading("1.6 Hipótesis", 2)
    add_para(sec['hip'])
    add_heading("1.7 Objetivos", 2)
    add_para(f"Objetivo general: {sec['obj_gen']}", bold=True)
    add_para("Objetivos específicos:", bold=True)
    for oe in sec['obj_esp']:
        add_para(f"• {oe}", indent=True)
    add_heading("1.8 Limitaciones", 2)
    for para_text in sec['lim'].split('\n\n'):
        if para_text.strip():
            add_para(para_text.strip())
    add_page_break()

    # Capítulo II
    add_heading("CAPÍTULO II: METODOLOGÍA", 1)
    c2 = sec.get('cap2', {})
    for key, subtitle in [
        ('tipo',         '2.1 Tipo y diseño de investigación'),
        ('poblacion',    '2.2 Población, muestra y muestreo'),
        ('variables',    '2.3 Variables y operacionalización'),
        ('tecnicas',     '2.4 Técnicas e instrumentos'),
        ('procedimiento','2.5 Procedimiento'),
        ('analisis',     '2.6 Método de análisis de datos'),
        ('eticos',       '2.7 Aspectos éticos'),
    ]:
        add_heading(subtitle, 2)
        for para_text in c2.get(key, '').split('\n\n'):
            if para_text.strip():
                add_para(re.sub(r'<[^>]+>', '', para_text.strip()))
    add_page_break()

    # Capítulo III
    add_heading("CAPÍTULO III: RESULTADOS", 1)
    c3 = sec.get('cap3', {})
    add_para(c3.get('intro', ''))
    for key, subtitle in [
        ('oe1', '3.1 Resultado por Objetivo Específico 1'),
        ('oe2', '3.2 Resultado por Objetivo Específico 2'),
        ('og',  '3.3 Resultado del Objetivo General'),
    ]:
        add_heading(subtitle, 2)
        for para_text in c3.get(key, '').split('\n\n'):
            if para_text.strip():
                add_para(re.sub(r'<[^>]+>', '', para_text.strip()))
    add_page_break()

    # Capítulo IV
    add_heading("CAPÍTULO IV: DISCUSIÓN", 1)
    for para_text in sec.get('cap4', '').split('\n\n'):
        if para_text.strip():
            add_para(re.sub(r'<[^>]+>', '', para_text.strip()))
    add_page_break()

    # Capítulo V
    add_heading("CAPÍTULO V: CONCLUSIONES Y RECOMENDACIONES", 1)
    c5 = sec.get('cap5', {})
    add_heading("5.1 Conclusiones", 2)
    for para_text in c5.get('conclusiones', '').split('\n\n'):
        if para_text.strip():
            add_para(re.sub(r'<[^>]+>', '', para_text.strip()))
    add_heading("5.2 Recomendaciones", 2)
    for para_text in c5.get('recomendaciones', '').split('\n\n'):
        if para_text.strip():
            add_para(re.sub(r'<[^>]+>', '', para_text.strip()))
    add_page_break()

    # Referencias
    add_heading("REFERENCIAS BIBLIOGRÁFICAS", 1)
    for ref in refs:
        clean_ref = re.sub(r'\*(.*?)\*', r'\1', ref)
        para = doc.add_paragraph()
        run = para.add_run(clean_ref)
        run.font.name = 'Arial Narrow'
        run.font.size = _Pt(12)
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.paragraph_format.left_indent = _Cm(1.2)
        para.paragraph_format.first_line_indent = _Cm(-1.2)
    add_page_break()

    # Árboles
    add_heading("ANEXO 1: ÁRBOL DE PROBLEMAS", 2)
    for text, style in _arbol_problemas(data['title']):
        if style not in ('sp',):
            add_para(text, bold=style in ('h2','h3'), indent=style in ('ind','ind2'))

    add_page_break()
    add_heading("ANEXO 2: ÁRBOL DE OBJETIVOS", 2)
    for text, style in _arbol_objetivos(data['title']):
        if style not in ('sp',):
            add_para(text, bold=style in ('h2','h3'), indent=style in ('ind','ind2'))

    add_page_break()
    add_heading("ANEXO 3: DECLARACIÓN JURADA", 2)
    authors_txt = ", ".join(authors)
    add_para(
        f"Yo/Nosotros, {authors_txt}, declaro/declaramos bajo juramento que la tesis titulada "
        f"«{data['title']}» es de mi/nuestra autoría, no ha sido plagiada, ni publicada "
        f"anteriormente, y que los datos presentados son reales."
    )
    doc.add_paragraph()
    for a in authors:
        add_para("_______________________________", align=WD_ALIGN_PARAGRAPH.CENTER)
        add_para(a.upper(), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

    doc.save(path)
    return path


# ── API pública ───────────────────────────────────────────────────────────────
def generate_thesis(data: dict) -> dict:
    """
    Genera la tesis completa (PDF + DOCX) a partir de los datos del usuario.

    data keys:
        title          str        — título de la tesis
        authors        str|list   — nombre(s) del autor(es)
        advisor        str        — nombre del asesor
        research_line  str        — línea de investigación
        city           str        — ciudad
        year           int        — año
        jurado         list       — 3 nombres del jurado (opcional)
        logo_data      str        — imagen en base64 data-URL (opcional)
    """
    import base64, tempfile

    uid   = uuid.uuid4().hex[:10]
    refs  = _gen_references(data.get('title', 'thesis'))
    title = data.get('title', 'thesis')
    rl    = data.get('research_line', '')

    # Decodificar logo si viene en base64
    logo_path = None
    if data.get('logo_data'):
        try:
            raw = data['logo_data']
            b64 = raw.split(',', 1)[-1]          # strip "data:image/...;base64,"
            logo_bytes = base64.b64decode(b64)
            ext = '.jpg' if ('jpeg' in raw or 'jpg' in raw) else '.png'
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=ext, dir=OUTPUT_DIR, prefix='logo_'
            )
            tmp.write(logo_bytes)
            tmp.close()
            logo_path = tmp.name
        except Exception as e:
            print(f"[thesis_generator] logo decode error: {e}")

    # Intentar OpenAI primero, luego templates locales
    ai_content = _gen_openai(data)
    if ai_content:
        sec = {
            'rp':      ai_content.get('rp',      _rp(title, rl)),
            'ant':     ai_content.get('ant',     _ant(title)),
            'mt':      ai_content.get('mt',      _mt(title, rl)),
            'just':    ai_content.get('just',    _just(title)),
            'prob':    ai_content.get('prob',    ''),
            'hip':     ai_content.get('hip',     ''),
            'obj_gen': ai_content.get('obj_gen', ''),
            'obj_esp': ai_content.get('obj_esp', []),
            'lim':     ai_content.get('lim',     ''),
        }
        source = 'openai'
    else:
        sec    = _intro_text(data, refs)
        source = 'template'

    # Añadir resumen, abstract y capítulos II–V (siempre desde templates)
    sec['resumen']  = _resumen(title, rl)
    sec['abstract'] = _abstract(title, rl)
    sec['cap2']     = _cap2(title, rl)
    sec['cap3']     = _cap3(title)
    sec['cap4']     = _cap4(title)
    sec['cap5']     = _cap5(title)

    # Jurado por defecto si no se proporcionó
    if not data.get('jurado'):
        rng = random.Random(abs(hash(title)) % 99999)
        prefixes  = ['Dr.', 'Mg.', 'Dr.']
        lastnames = ['García López', 'Rodríguez Sánchez', 'Martínez Torres',
                     'Pérez Castillo', 'Flores Ramírez', 'Soto Herrera']
        data['jurado'] = [f"{prefixes[i]} {rng.choice(lastnames)}" for i in range(3)]

    pdf_path  = _build_pdf(data, sec, refs, uid, logo_path=logo_path)
    docx_path = _build_docx(data, sec, refs, uid, logo_path=logo_path)

    # Limpiar logo temporal
    if logo_path and os.path.exists(logo_path):
        try:
            os.remove(logo_path)
        except Exception:
            pass

    return {
        'uid':       uid,
        'pdf_file':  os.path.basename(pdf_path),
        'docx_file': os.path.basename(docx_path),
        'source':    source,
        'sections':  {k: (v[:200] + '...' if isinstance(v, str) and len(v) > 200 else v)
                      for k, v in sec.items() if isinstance(v, (str, list))},
    }

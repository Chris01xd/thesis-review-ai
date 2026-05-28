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
def _gen_references(title: str, n: int = 32) -> list:
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


# ── Construcción del PDF ──────────────────────────────────────────────────────
def _build_pdf(data: dict, sec: dict, refs: list, uid: str) -> str:
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
    sp(60)
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
        ("Índice de Figuras", "iv"),
        ("Índice de Tablas", "v"),
        ("Resumen", "vi"),
        ("Abstract", "vii"),
        ("CAPÍTULO I: INTRODUCCIÓN", "1"),
        ("  Realidad Problemática", "1"),
        ("  Antecedentes", "3"),
        ("  Marco Teórico", "5"),
        ("  Justificación", "7"),
        ("  Problema", "8"),
        ("  Hipótesis", "8"),
        ("  Objetivos", "9"),
        ("  Limitaciones", "9"),
        ("Referencias Bibliográficas", "10"),
        ("Anexos", "12"),
        ("  Anexo 1: Árbol de Problemas", "12"),
        ("  Anexo 2: Árbol de Objetivos", "14"),
        ("  Anexo 3: Declaración Jurada", "16"),
    ]
    for item, pg in toc_items:
        dots = "." * max(2, 68 - len(item) - len(pg))
        p(f"{item}{dots}{pg}", 'l' if not item.startswith("  ") else 'ind')
    br()

    # ── 4. CAPÍTULO I (prosa, sin subtítulos) ─────────────────────────────────
    p("CAPÍTULO I: INTRODUCCIÓN", 'h1')
    sp(8)

    for para in sec['rp'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    sp(6)
    for para in sec['ant'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    sp(6)
    for para in sec['mt'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    sp(6)
    for para in sec['just'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    sp(6)
    p(sec['prob'])
    sp(6)
    p(sec['hip'])
    sp(10)
    p(f"El <b>objetivo general</b> de la presente investigación es: {sec['obj_gen']}")
    sp(6)
    p("Los <b>objetivos específicos</b> son:")
    for oe in sec['obj_esp']:
        p(f"• {oe}", 'ind')
        sp(2)
    sp(6)
    for para in sec['lim'].split('\n\n'):
        if para.strip():
            p(para.strip())
            sp(4)
    br()

    # ── 5. REFERENCIAS ────────────────────────────────────────────────────────
    p("REFERENCIAS BIBLIOGRÁFICAS", 'h1')
    sp(8)
    for ref in refs:
        # Convert markdown italic *text* to <i>text</i> for ReportLab
        ref_html = re.sub(r'\*(.*?)\*', r'<i>\1</i>', ref)
        story.append(Paragraph(ref_html, s['ref']))
        sp(2)
    br()

    # ── 6. ANEXOS ─────────────────────────────────────────────────────────────
    p("ANEXOS", 'h1')
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


def _build_docx(data: dict, sec: dict, refs: list, uid: str) -> str:
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

    # Capítulo I
    add_heading("CAPÍTULO I: INTRODUCCIÓN", 1)
    for section_text in [sec['rp'], sec['ant'], sec['mt'], sec['just']]:
        for para_text in section_text.split('\n\n'):
            if para_text.strip():
                add_para(para_text.strip())
    add_para(sec['prob'])
    add_para(sec['hip'])
    add_para(f"El objetivo general es: {sec['obj_gen']}", bold=True)
    add_para("Objetivos específicos:", bold=True)
    for oe in sec['obj_esp']:
        add_para(f"• {oe}", indent=True)
    for para_text in sec['lim'].split('\n\n'):
        if para_text.strip():
            add_para(para_text.strip())
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
        title          str  — título de la tesis
        authors        str | list  — nombre(s) del autor(es)
        advisor        str  — nombre del asesor
        research_line  str  — línea de investigación
        city           str  — ciudad
        year           int  — año
        jurado         list — 3 nombres del jurado (opcional)
    """
    uid  = uuid.uuid4().hex[:10]
    refs = _gen_references(data.get('title', 'thesis'))

    # Intentar OpenAI primero, luego templates locales
    ai_content = _gen_openai(data)
    if ai_content:
        sec = {
            'rp':      ai_content.get('rp', _rp(data['title'], data.get('research_line',''))),
            'ant':     ai_content.get('ant', _ant(data['title'])),
            'mt':      ai_content.get('mt', _mt(data['title'], data.get('research_line',''))),
            'just':    ai_content.get('just', _just(data['title'])),
            'prob':    ai_content.get('prob', ''),
            'hip':     ai_content.get('hip', ''),
            'obj_gen': ai_content.get('obj_gen', ''),
            'obj_esp': ai_content.get('obj_esp', []),
            'lim':     ai_content.get('lim', ''),
        }
        source = 'openai'
    else:
        base = _intro_text(data, refs)
        sec  = base
        source = 'template'

    # Jurado por defecto si no se proporcionó
    if not data.get('jurado'):
        rng = random.Random(abs(hash(data.get('title','x'))) % 99999)
        prefixes = ['Dr.', 'Mg.', 'Dr.']
        lastnames = ['García López', 'Rodríguez Sánchez', 'Martínez Torres',
                     'Pérez Castillo', 'Flores Ramírez', 'Soto Herrera']
        data['jurado'] = [f"{prefixes[i]} {rng.choice(lastnames)}" for i in range(3)]

    pdf_path  = _build_pdf(data, sec, refs, uid)
    docx_path = _build_docx(data, sec, refs, uid)

    return {
        'uid':       uid,
        'pdf_file':  os.path.basename(pdf_path),
        'docx_file': os.path.basename(docx_path),
        'source':    source,
        'sections':  {k: v[:200] + '...' if isinstance(v,str) and len(v)>200 else v
                      for k, v in sec.items()},
    }

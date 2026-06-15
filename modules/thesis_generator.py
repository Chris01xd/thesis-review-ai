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


def _arbol_data(title: str, tipo: str) -> dict:
    """Retorna datos estructurados para árbol de problemas u objetivos."""
    vi, vd = _extract_vi_vd(title)
    if tipo == 'problemas':
        return {
            'titulo': 'ARBOL DE PROBLEMAS  (Analisis Causa - Efecto)',
            'top_label': 'E F E C T O S',
            'bottom_label': 'C A U S A S',
            'center_label': 'PROBLEMA CENTRAL',
            'center_text': (
                f"Deficiente gestion de {vd.lower()} ante la ausencia de {vi.lower()}, "
                f"que genera ineficiencias operativas y reduce la calidad de los resultados "
                f"en las organizaciones del ambito de estudio."
            ),
            'top': [
                f"Incremento de costos operativos y tiempos de respuesta en {vd.lower()}",
                f"Baja calidad en los procesos relacionados con {vd.lower()}",
                f"Insatisfaccion de usuarios y perdida de competitividad institucional",
            ],
            'bottom': [
                f"Ausencia de {vi.lower()} adecuado al contexto institucional",
                f"Procesos manuales ineficientes y propensos a errores en {vd.lower()}",
                f"Escasa capacitacion del personal y limitada inversion tecnologica",
            ],
        }
    else:
        return {
            'titulo': 'ARBOL DE OBJETIVOS  (Analisis Medios - Fines)',
            'top_label': 'F I N E S',
            'bottom_label': 'M E D I O S',
            'center_label': 'OBJETIVO CENTRAL',
            'center_text': (
                f"Desarrollar e implementar {vi.lower()} para mejorar la eficiencia "
                f"operativa y elevar la calidad de {vd.lower()} en las organizaciones "
                f"del ambito de estudio."
            ),
            'top': [
                f"Reduccion de costos operativos y tiempos de respuesta en {vd.lower()}",
                f"Alta calidad en los procesos relacionados con {vd.lower()}",
                f"Satisfaccion de usuarios y mejora de la competitividad institucional",
            ],
            'bottom': [
                f"Diseno e implementacion de {vi.lower()} para el contexto institucional",
                f"Automatizacion y optimizacion de los procesos relacionados con {vd.lower()}",
                f"Capacitacion del personal y fortalecimiento de la infraestructura tecnologica",
            ],
        }


def _pdf_arbol_diagram(story: list, title: str, tipo: str):
    """Genera diagrama visual de arbol (caja de colores jerarquica) para PDF."""
    from reportlab.platypus import Table as _T, TableStyle as _TS, Paragraph as _P
    from reportlab.lib import colors as _c
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    _register_fonts()
    d = _arbol_data(title, tipo)

    PAGE_W = 21 * cm - ML - MR
    cw = PAGE_W / 3

    # Paleta de colores segun tipo
    if tipo == 'problemas':
        c_top = _c.HexColor('#d9780b')   # naranja: efectos
        c_ctr = _c.HexColor('#7b1e1e')   # rojo oscuro: problema central
        c_bot = _c.HexColor('#1e567b')   # azul acero: causas
    else:
        c_top = _c.HexColor('#2d7a4a')   # verde: fines
        c_ctr = _c.HexColor('#1a5c3a')   # verde oscuro: objetivo central
        c_bot = _c.HexColor('#1e3a7b')   # azul oscuro: medios

    c_hdr = _c.HexColor('#1e3a5f')
    c_lbl = _c.HexColor('#dde3ea')
    c_arr = _c.HexColor('#f0f2f5')
    W = _c.white
    D = _c.HexColor('#1e3a5f')

    def Ps(txt, sz=9, bold=False, col=_c.black):
        safe = str(txt).replace('&', '&amp;').replace('\n', '<br/>')
        st = ParagraphStyle(
            f'arb{tipo}{sz}{int(bold)}',
            fontName=_FB if bold else _F, fontSize=sz, leading=sz + 4,
            alignment=TA_CENTER, textColor=col, spaceAfter=0, spaceBefore=0,
        )
        return _P(safe, st)

    rows = [
        [Ps(d['titulo'], 10, True, W), '', ''],
        [Ps(d['top_label'], 8, True, D), '', ''],
        [Ps(d['top'][0], 8, col=W), Ps(d['top'][1], 8, col=W), Ps(d['top'][2], 8, col=W)],
        [Ps('v        v        v', 10, col=_c.HexColor('#555555')), '', ''],
        [Ps(d['center_label'] + '\n\n' + d['center_text'], 9, True, W), '', ''],
        [Ps('v        v        v', 10, col=_c.HexColor('#555555')), '', ''],
        [Ps(d['bottom'][0], 8, col=W), Ps(d['bottom'][1], 8, col=W), Ps(d['bottom'][2], 8, col=W)],
        [Ps(d['bottom_label'], 8, True, D), '', ''],
    ]

    cmds = [
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('GRID',          (0, 0), (-1, -1), 0.5, _c.HexColor('#8899aa')),
        ('BOX',           (0, 0), (-1, -1), 1.5, c_hdr),
        # SPANs filas completas
        ('SPAN', (0, 0), (2, 0)),
        ('SPAN', (0, 1), (2, 1)),
        ('SPAN', (0, 3), (2, 3)),
        ('SPAN', (0, 4), (2, 4)),
        ('SPAN', (0, 5), (2, 5)),
        ('SPAN', (0, 7), (2, 7)),
        # Fondos
        ('BACKGROUND', (0, 0), (2, 0), c_hdr),
        ('BACKGROUND', (0, 1), (2, 1), c_lbl),
        ('BACKGROUND', (0, 2), (2, 2), c_top),
        ('BACKGROUND', (0, 3), (2, 3), c_arr),
        ('BACKGROUND', (0, 4), (2, 4), c_ctr),
        ('BACKGROUND', (0, 5), (2, 5), c_arr),
        ('BACKGROUND', (0, 6), (2, 6), c_bot),
        ('BACKGROUND', (0, 7), (2, 7), c_lbl),
        # Filas de flecha delgadas
        ('TOPPADDING',    (0, 3), (2, 3), 4),
        ('BOTTOMPADDING', (0, 3), (2, 3), 4),
        ('TOPPADDING',    (0, 5), (2, 5), 4),
        ('BOTTOMPADDING', (0, 5), (2, 5), 4),
    ]

    t = _T(rows, colWidths=[cw, cw, cw])
    t.setStyle(_TS(cmds))
    story.append(t)


def _docx_arbol_diagram(doc, title: str, tipo: str):
    """Genera diagrama visual de arbol (tabla coloreada) para DOCX."""
    d = _arbol_data(title, tipo)

    if tipo == 'problemas':
        c_top = 'd9780b'
        c_ctr = '7b1e1e'
        c_bot = '1e567b'
    else:
        c_top = '2d7a4a'
        c_ctr = '1a5c3a'
        c_bot = '1e3a7b'

    c_hdr = '1e3a5f'
    c_lbl = 'dde3ea'
    c_arr = 'f0f2f5'

    tbl = doc.add_table(rows=8, cols=3)
    tbl.style = 'Table Grid'

    def fill_cell(cell, lines, bg, bold=False, white_txt=False, sz=8):
        """Rellena una celda con texto y color de fondo."""
        # Limpiar contenido existente
        for p in cell.paragraphs[1:]:
            p._element.getparent().remove(p._element)
        cell.paragraphs[0].clear()
        for i, line in enumerate(lines if isinstance(lines, list) else [lines]):
            para = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run(str(line))
            run.bold = bold
            run.font.size = _Pt(sz)
            run.font.name = 'Arial Narrow'
            if white_txt:
                run.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
            elif bg == c_lbl:
                run.font.color.rgb = RGBColor(0x1e, 0x3a, 0x5f)
        _set_cell_bg(cell, bg)

    # Filas 0,1,3,4,5,7 abarcan las 3 columnas → merge primero
    for r in (0, 1, 3, 4, 5, 7):
        tbl.cell(r, 0).merge(tbl.cell(r, 2))

    # Fila 0: titulo
    fill_cell(tbl.cell(0, 0), d['titulo'], c_hdr, bold=True, white_txt=True, sz=10)

    # Fila 1: etiqueta superior
    fill_cell(tbl.cell(1, 0), d['top_label'], c_lbl, bold=True, sz=8)

    # Fila 2: 3 cajas superiores
    for ci, txt in enumerate(d['top']):
        fill_cell(tbl.rows[2].cells[ci], txt, c_top, white_txt=True, sz=8)

    # Fila 3: flechas
    fill_cell(tbl.cell(3, 0), 'v                    v                    v', c_arr, sz=9)

    # Fila 4: caja central
    fill_cell(tbl.cell(4, 0),
              [d['center_label'], d['center_text']],
              c_ctr, bold=True, white_txt=True, sz=9)

    # Fila 5: flechas
    fill_cell(tbl.cell(5, 0), 'v                    v                    v', c_arr, sz=9)

    # Fila 6: 3 cajas inferiores
    for ci, txt in enumerate(d['bottom']):
        fill_cell(tbl.rows[6].cells[ci], txt, c_bot, white_txt=True, sz=8)

    # Fila 7: etiqueta inferior
    fill_cell(tbl.cell(7, 0), d['bottom_label'], c_lbl, bold=True, sz=8)


# Mantener alias para compatibilidad con código heredado
def _arbol_problemas(title: str) -> list:
    return []

def _arbol_objetivos(title: str) -> list:
    return []


# ── Diagrama de Ishikawa / Espina de Pescado (Anexo 3 oficial UNT 2026) ───────

def _ichikawa_data(title: str) -> dict:
    vi, vd = _extract_vi_vd(title)
    efecto = f"Deficiente gestión de {vd.lower()} ante la ausencia de {vi.lower()}"
    return {
        'efecto': efecto,
        'causas': {
            'PERSONAS': [
                f"Escasa capacitación en {vd.lower()}",
                "Alta rotación del personal responsable",
                "Falta de compromiso institucional",
            ],
            'PROCESOS': [
                f"Ausencia de estándares para {vi.lower()}",
                "Procedimientos manuales sin sistematizar",
                "Deficiente control de calidad interno",
            ],
            'TECNOLOGÍA': [
                f"Sin sistema de {vi.lower()} implementado",
                "Infraestructura tecnológica obsoleta",
                "Falta de integración entre plataformas",
            ],
            'ENTORNO / AMBIENTE': [
                "Cambios normativos frecuentes",
                "Recursos financieros insuficientes",
                "Demanda en constante variación",
            ],
        },
    }


def _pdf_ichikawa_diagram(story: list, title: str):
    """Genera diagrama de Ishikawa como tabla visual 4-bloques para PDF."""
    from reportlab.platypus import Paragraph as _P, Table as _T, TableStyle as _TS
    from reportlab.lib import colors as _c
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    _register_fonts()
    d = _ichikawa_data(title)

    PAGE_W = 21*cm - ML - MR
    col_w = PAGE_W / 2

    c_hdr   = _c.HexColor('#1e3a5f')
    c_efect = _c.HexColor('#8b1a1a')
    c_pers  = _c.HexColor('#1e567b')
    c_proc  = _c.HexColor('#2d7a4a')
    c_tecn  = _c.HexColor('#7b5e1e')
    c_entr  = _c.HexColor('#4a1e7b')

    def Ps(txt, sz=8, bold=False, col=_c.black, align=TA_LEFT):
        safe = str(txt).replace('&', '&amp;').replace('\n', '<br/>')
        st = ParagraphStyle(
            f'ichi{sz}{int(bold)}',
            fontName=_FB if bold else _F, fontSize=sz, leading=sz+3,
            alignment=align, textColor=col, spaceAfter=0, spaceBefore=0,
        )
        return _P(safe, st)

    def causa_txt(cat_color, categoria, items):
        lines = f"<b>{categoria}</b><br/>" + "<br/>".join(f"• {it}" for it in items)
        return lines

    causas = d['causas']
    cats = list(causas.keys())
    colors_cat = [c_pers, c_proc, c_tecn, c_entr]

    rows = [
        [Ps("DIAGRAMA DE ISHIKAWA — Espina de Pescado (Análisis Causa–Efecto)", 10, True, _c.white, TA_CENTER), ''],
        [Ps(causa_txt(colors_cat[0], cats[0], causas[cats[0]]), 8, col=_c.white),
         Ps(causa_txt(colors_cat[1], cats[1], causas[cats[1]]), 8, col=_c.white)],
        [Ps(f"<b>EFECTO / PROBLEMA CENTRAL</b><br/>{d['efecto']}", 9, True, _c.white, TA_CENTER), ''],
        [Ps(causa_txt(colors_cat[2], cats[2], causas[cats[2]]), 8, col=_c.white),
         Ps(causa_txt(colors_cat[3], cats[3], causas[cats[3]]), 8, col=_c.white)],
    ]

    row_h = [1*cm, 3*cm, 1.5*cm, 3*cm]

    t = _T(rows, colWidths=[col_w, col_w], rowHeights=row_h)
    t.setStyle(_TS([
        ('SPAN',          (0, 0), (1, 0)),
        ('SPAN',          (0, 2), (1, 2)),
        ('BACKGROUND',    (0, 0), (1, 0), c_hdr),
        ('BACKGROUND',    (0, 1), (0, 1), c_pers),
        ('BACKGROUND',    (1, 1), (1, 1), c_proc),
        ('BACKGROUND',    (0, 2), (1, 2), c_efect),
        ('BACKGROUND',    (0, 3), (0, 3), c_tecn),
        ('BACKGROUND',    (1, 3), (1, 3), c_entr),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('BOX',           (0, 0), (-1, -1), 1.5, c_hdr),
        ('GRID',          (0, 0), (-1, -1), 0.5, _c.HexColor('#ffffff')),
    ]))
    story.append(t)


def _docx_ichikawa_diagram(doc, title: str):
    """Genera diagrama de Ishikawa como tabla visual 4-bloques para DOCX."""
    d = _ichikawa_data(title)

    c_hdr   = '1e3a5f'
    c_efect = '8b1a1a'
    c_pers  = '1e567b'
    c_proc  = '2d7a4a'
    c_tecn  = '7b5e1e'
    c_entr  = '4a1e7b'

    causas = d['causas']
    cats = list(causas.keys())
    colors_cat = [c_pers, c_proc, c_tecn, c_entr]

    tbl = doc.add_table(rows=4, cols=2)
    tbl.style = 'Table Grid'

    def fill_c(cell, lines, bg, bold=False, sz=9):
        for p in cell.paragraphs[1:]:
            p._element.getparent().remove(p._element)
        cell.paragraphs[0].clear()
        for i, line in enumerate(lines if isinstance(lines, list) else [lines]):
            para = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run(str(line))
            run.bold = bold
            run.font.size = _Pt(sz)
            run.font.name = 'Arial Narrow'
            run.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
        _set_cell_bg(cell, bg)

    # Row 0: header (merged)
    tbl.cell(0, 0).merge(tbl.cell(0, 1))
    fill_c(tbl.cell(0, 0), "DIAGRAMA DE ISHIKAWA — Espina de Pescado (Análisis Causa–Efecto)", c_hdr, bold=True, sz=11)

    # Row 1: Personas | Procesos
    for ci, (cat_idx, bg) in enumerate([(0, c_pers), (1, c_proc)]):
        lines = [cats[cat_idx]] + [f"• {it}" for it in causas[cats[cat_idx]]]
        fill_c(tbl.rows[1].cells[ci], lines, bg, sz=9)

    # Row 2: Efecto (merged)
    tbl.cell(2, 0).merge(tbl.cell(2, 1))
    fill_c(tbl.cell(2, 0), ["EFECTO / PROBLEMA CENTRAL", d['efecto']], c_efect, bold=True, sz=10)

    # Row 3: Tecnología | Entorno
    for ci, (cat_idx, bg) in enumerate([(2, c_tecn), (3, c_entr)]):
        lines = [cats[cat_idx]] + [f"• {it}" for it in causas[cats[cat_idx]]]
        fill_c(tbl.rows[3].cells[ci], lines, bg, sz=9)


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
    _pdf_arbol_diagram(story, data['title'], 'problemas')
    br()

    p("Anexo 2: Árbol de Objetivos", 'h2')
    sp(8)
    _pdf_arbol_diagram(story, data['title'], 'objetivos')
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

    # Árboles (diagramas visuales)
    add_heading("ANEXO 1: ÁRBOL DE PROBLEMAS", 2)
    _docx_arbol_diagram(doc, data['title'], 'problemas')

    add_page_break()
    add_heading("ANEXO 2: ÁRBOL DE OBJETIVOS", 2)
    _docx_arbol_diagram(doc, data['title'], 'objetivos')

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


# ═══════════════════════════════════════════════════════════════════════════════
# GENERACIÓN DE TIPOS DE DOCUMENTO ADICIONALES
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tablas académicas estándar ─────────────────────────────────────────────────

def _tabla_cronograma(title: str) -> list:
    """Genera filas para un cronograma de actividades de 6 meses."""
    kw = title.split()[:3]
    actividades = [
        "Revisión bibliográfica y estado del arte",
        f"Elaboración del marco teórico sobre {' '.join(kw)}",
        "Diseño del instrumento de recolección de datos",
        "Validación del instrumento (juicio de expertos)",
        "Recolección de datos en campo",
        "Procesamiento y análisis estadístico",
        "Redacción de resultados y discusión",
        "Revisión y corrección del documento final",
        "Sustentación del proyecto",
    ]
    rows = []
    for i, act in enumerate(actividades):
        row = [act]
        for mes in range(1, 7):
            row.append("X" if mes in [(i // 2) + 1, (i // 2) + 2] else "")
        rows.append(row)
    return rows


def _tabla_presupuesto(title: str) -> list:
    kw = " ".join(title.split()[:3])
    items = [
        ("Recursos Humanos", "", "", ""),
        (f"  Asesor especialista en {kw}", "1", "S/. 3,000.00", "S/. 3,000.00"),
        ("  Estadístico", "1", "S/. 800.00", "S/. 800.00"),
        ("  Digitador / transcritor", "1", "S/. 300.00", "S/. 300.00"),
        ("Materiales", "", "", ""),
        ("  Papel bond A4 (500 hojas)", "2 millares", "S/. 30.00", "S/. 60.00"),
        ("  Lapiceros, marcadores", "1 juego", "S/. 20.00", "S/. 20.00"),
        ("  USB y materiales de cómputo", "2 unidades", "S/. 40.00", "S/. 80.00"),
        ("Servicios", "", "", ""),
        ("  Impresión y empastado", "3 ejemplares", "S/. 80.00", "S/. 240.00"),
        ("  Internet y comunicaciones", "6 meses", "S/. 60.00", "S/. 360.00"),
        ("  Movilidad y viáticos", "estimado", "S/. 200.00", "S/. 200.00"),
        ("  Tramites y derechos académicos", "global", "S/. 500.00", "S/. 500.00"),
        ("TOTAL", "", "", "S/. 5,560.00"),
    ]
    return items


# ── Helpers de extracción de variables ────────────────────────────────────────

def _extract_vi_vd(title: str) -> tuple:
    """Devuelve (nombre_VI, nombre_VD) a partir del título."""
    words = title.split()
    vi = " ".join(words[:min(6, len(words))])
    vd_words = words[max(0, len(words) - 4):]
    vd = " ".join(vd_words) if vd_words else "procesos organizacionales"
    return vi, vd


def _para_style_cell(font_size: int = 9):
    """Estilo de párrafo para celdas de tabla ReportLab."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    _register_fonts()
    return ParagraphStyle(
        f'cell_{font_size}',
        fontName=_F, fontSize=font_size, leading=font_size + 3,
        alignment=TA_LEFT, spaceAfter=0, spaceBefore=0,
    )


def _set_cell_bg(cell, hex_color: str):
    """Pone color de fondo a una celda DOCX via XML."""
    from docx.oxml.ns import qn as _qn
    from docx.oxml import OxmlElement as _OE
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = _OE('w:shd')
    shd.set(_qn('w:val'), 'clear')
    shd.set(_qn('w:color'), 'auto')
    shd.set(_qn('w:fill'), hex_color)
    tcPr.append(shd)


# ── Matriz de Consistencia (5 columnas — esquema oficial UNT 2026) ─────────────

def _pdf_consistencia_table(story: list, title: str, sec: dict):
    """Agrega Matriz de Consistencia 5 cols al story ReportLab (Problema|Objetivos|Hipótesis|Variable|Metodología)."""
    from reportlab.platypus import Paragraph as _P, Table as _T, TableStyle as _TS
    from reportlab.lib import colors as _c

    vi, vd = _extract_vi_vd(title)
    obj_gen = sec.get('obj_gen', f"Determinar la incidencia de {vi} sobre los indicadores de desempeño de {vd}.")
    obj_esp = sec.get('obj_esp', [
        f"Diagnosticar el estado actual de los procesos relacionados con {vd}",
        f"Diseñar e implementar {vi} según los requerimientos identificados",
        f"Evaluar el efecto de {vi} en los indicadores de desempeño de {vd}",
    ])
    prob_gen = sec.get('prob', f"¿De qué manera {vi} incide en los indicadores de desempeño de {vd}?")
    hip_gen = sec.get('hip', f"La implementación de {vi} mejora significativamente los indicadores de {vd}.")

    prob_esps = [
        f"¿Cuál es el estado actual de {vd} antes de implementar {vi}?",
        f"¿En qué medida el diseño de {vi} satisface los requerimientos del área de estudio?",
        f"¿Cómo incide {vi} en los indicadores de desempeño de {vd}?",
    ]
    hip_esps = [
        f"H1: El diseño de {vi} mejora el nivel de satisfacción respecto a {vd}.",
        f"H2: La implementación de {vi} reduce los tiempos de procesamiento en {vd}.",
        f"H3: La aplicación de {vi} incrementa la eficiencia operativa de {vd}.",
    ]
    metod_txt = (
        "<b>Método:</b> Cuantitativo<br/><b>Tipo:</b> Aplicada<br/>"
        "<b>Diseño:</b> Pre-experimental<br/><b>Población:</b> Personal del área<br/>"
        "<b>Muestra:</b> Por conveniencia<br/><b>Técnicas:</b> Encuesta, observación<br/>"
        "<b>Análisis:</b> Estadística inferencial"
    )

    st = _para_style_cell(7)

    def P(html):
        return _P(str(html), st)

    PAGE_W = 21*cm - ML - MR
    cw = [PAGE_W*0.21, PAGE_W*0.21, PAGE_W*0.20, PAGE_W*0.17, PAGE_W*0.21]

    prob_g = f"<b>Enunciado general:</b><br/>{prob_gen}"
    prob_e = "<b>Específicos:</b><br/>" + "<br/>".join(f"{i+1}. {p}" for i, p in enumerate(prob_esps))
    obj_g  = f"<b>General:</b><br/>{obj_gen}"
    obj_e  = "<b>Específicos:</b><br/>" + "<br/>".join(f"{i+1}. {o}" for i, o in enumerate(obj_esp[:3]))
    hip_g  = f"<b>Ha:</b> {hip_gen}<br/><b>H0:</b> La implementación de {vi} NO mejora los indicadores de {vd}."
    hip_e  = "<b>Específicas:</b><br/>" + "<br/>".join(f"{i+1}. {h}" for i, h in enumerate(hip_esps))

    data = [
        [P("<b>Problema</b>"), P("<b>Objetivos</b>"), P("<b>Hipótesis</b>"), P("<b>Variable</b>"), P("<b>Metodología</b>")],
        [P(prob_g), P(obj_g), P(hip_g), P(f"<b>Independiente:</b><br/>{vi}"), P(metod_txt)],
        [P(prob_e), P(obj_e), P(hip_e), P(f"<b>Dependiente:</b><br/>{vd}"), P(metod_txt)],
    ]

    t = _T(data, colWidths=cw, repeatRows=1)
    t.setStyle(_TS([
        ('BACKGROUND',    (0, 0), (-1, 0),  _c.HexColor('#1e3a5f')),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  _c.white),
        ('FONTNAME',      (0, 0), (-1, 0),  _FB),
        ('FONTSIZE',      (0, 0), (-1, -1), 7),
        ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('GRID',          (0, 0), (-1, -1), 0.5, _c.HexColor('#c0c8d8')),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
        ('BACKGROUND',    (0, 1), (-1, -1), _c.white),
    ]))
    story.append(t)


def _docx_consistencia_table(doc, title: str, sec: dict):
    """Agrega Matriz de Consistencia 5 cols a DOCX (Problema|Objetivos|Hipótesis|Variable|Metodología)."""
    vi, vd = _extract_vi_vd(title)
    obj_gen = sec.get('obj_gen', f"Determinar la incidencia de {vi} sobre los indicadores de desempeño de {vd}.")
    obj_esp = sec.get('obj_esp', [
        f"Diagnosticar el estado actual de los procesos relacionados con {vd}",
        f"Diseñar e implementar {vi} según los requerimientos identificados",
        f"Evaluar el efecto de {vi} en los indicadores de desempeño de {vd}",
    ])
    prob_gen = sec.get('prob', f"¿De qué manera {vi} incide en los indicadores de desempeño de {vd}?")
    hip_gen = sec.get('hip', f"La implementación de {vi} mejora significativamente los indicadores de {vd}.")

    prob_esps = [
        f"¿Cuál es el estado actual de {vd} antes de implementar {vi}?",
        f"¿En qué medida el diseño de {vi} satisface los requerimientos del área?",
        f"¿Cómo incide {vi} en los indicadores de desempeño de {vd}?",
    ]
    hip_esps = [
        f"H1: El diseño de {vi} mejora el nivel de satisfacción respecto a {vd}.",
        f"H2: La implementación de {vi} reduce los tiempos de procesamiento.",
        f"H3: La aplicación de {vi} incrementa la eficiencia operativa.",
    ]
    metod_cell = (
        "Método: Cuantitativo\nTipo: Aplicada\nDiseño: Pre-experimental\n"
        "Población: Personal del área\nMuestra: Por conveniencia\n"
        "Técnicas: Encuesta, observación\nAnálisis: Estadística inferencial"
    )

    t = doc.add_table(rows=3, cols=5)
    t.style = 'Table Grid'

    headers = ["Problema", "Objetivos", "Hipótesis", "Variable", "Metodología"]
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = h
        _set_cell_bg(c, '1e3a5f')
        for para in c.paragraphs:
            for run in para.runs:
                run.bold = True
                run.font.size = _Pt(9)
                run.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

    row1_data = [
        f"Enunciado general:\n{prob_gen}",
        f"General:\n{obj_gen}",
        f"Ha: {hip_gen}\nH0: La implementación de {vi} NO mejora los indicadores de {vd}.",
        f"Independiente:\n{vi}",
        metod_cell,
    ]
    row2_data = [
        "Específicos:\n" + "\n".join(f"{i+1}. {p}" for i, p in enumerate(prob_esps)),
        "Específicos:\n" + "\n".join(f"{i+1}. {o}" for i, o in enumerate(obj_esp[:3])),
        "Específicas:\n" + "\n".join(f"{i+1}. {h}" for i, h in enumerate(hip_esps)),
        f"Dependiente:\n{vd}",
        metod_cell,
    ]

    for row_idx, row_data in enumerate([row1_data, row2_data], start=1):
        for ci, txt in enumerate(row_data):
            c = t.rows[row_idx].cells[ci]
            c.text = txt
            for para in c.paragraphs:
                para.paragraph_format.space_after = _Pt(2)
                for run in para.runs:
                    run.font.size = _Pt(8)
                    run.font.name = 'Arial Narrow'

    return t


# ── Operacionalización de Variables (6 columnas, celdas combinadas) ────────────

def _pdf_operacionalizacion_table(story: list, title: str):
    """
    Agrega la Matriz de Operacionalización de Variables al story ReportLab.
    6 columnas con celdas combinadas para VI y VD.
    Formato exacto de plantilla UNT.
    """
    from reportlab.platypus import Paragraph as _P, Table as _T, TableStyle as _TS
    from reportlab.lib import colors as _c

    vi, vd = _extract_vi_vd(title)
    kw = " ".join(title.split()[:3])

    vi_def_c = (
        f"Solución tecnológica/metodológica que permite {kw.lower()} de manera sistemática "
        f"y eficiente, optimizando los procesos organizacionales del área de estudio."
    )
    vi_def_o = (
        f"Medido a través de criterios técnicos de funcionalidad, usabilidad, rendimiento "
        f"y confiabilidad, evaluados mediante cuestionario validado (α = 0.912)."
    )
    vd_def_c = (
        f"Resultado cuantificable que refleja el nivel de desempeño en {vd.lower()}, "
        f"incluyendo indicadores de eficiencia, calidad, tiempo y satisfacción del usuario."
    )
    vd_def_o = (
        f"Medición directa de los indicadores de desempeño antes y después de la implementación, "
        f"mediante instrumentos validados por juicio de expertos (CVC = 0.87)."
    )

    vi_dims = [
        ("Funcionalidad",
         "• Cobertura de requisitos funcionales (%)\n• N.° módulos implementados / planificados",
         "Razón\nNominal"),
        ("Usabilidad",
         "• Tiempo promedio para completar tareas clave (min)\n• Puntuación SUS (System Usability Scale)",
         "Continua\nOrdinal"),
        ("Rendimiento",
         "• Tiempo de respuesta del sistema (seg)\n• Disponibilidad del sistema (%)",
         "Continua\nRazón"),
        ("Confiabilidad",
         "• Tasa de errores del sistema (%)\n• Tiempo medio entre fallos (horas)",
         "Razón\nContinua"),
    ]
    vd_dims = [
        ("Eficiencia operativa",
         "• Tiempo promedio de proceso (min)\n• Reducción del tiempo vs. línea base (%)",
         "Razón"),
        ("Calidad del servicio",
         "• Porcentaje de conformidad con estándares (%)\n• Índice de calidad percibida (1-5)",
         "Razón\nOrdinal"),
        ("Satisfacción del usuario",
         "• Índice de satisfacción (escala 1-5)\n• Porcentaje de usuarios satisfechos (%)",
         "Ordinal\nRazón"),
        ("Reducción de errores",
         "• Tasa de error antes vs. después (%)\n• N.° de incidencias registradas",
         "Razón\nNominal"),
        ("Costo operativo",
         "• Costo unitario de proceso (S/.)\n• Ahorro mensual estimado (S/.)",
         "Razón"),
        ("Cumplimiento normativo",
         "• Porcentaje de cumplimiento de normas (%)\n• N.° de no conformidades detectadas",
         "Nominal\nRazón"),
    ]

    st = _para_style_cell(8)

    def P(txt):
        safe = str(txt).replace('&', '&amp;').replace('\n', '<br/>')
        return _P(safe, st)

    headers_row = [P(f"<b>{h}</b>") for h in [
        "Variable", "Definición\nConceptual", "Definición\nOperacional",
        "Dimensión", "Indicador", "Escala de\nMedición"
    ]]

    n_vi = len(vi_dims)
    n_vd = len(vd_dims)

    data = [headers_row]
    for i, (dim, ind, esc) in enumerate(vi_dims):
        if i == 0:
            data.append([P(f"<b>Independiente:</b><br/>{vi}"), P(vi_def_c), P(vi_def_o),
                         P(dim), P(ind), P(esc)])
        else:
            data.append([P(""), P(""), P(""), P(dim), P(ind), P(esc)])

    for i, (dim, ind, esc) in enumerate(vd_dims):
        if i == 0:
            data.append([P(f"<b>Dependiente:</b><br/>{vd}"), P(vd_def_c), P(vd_def_o),
                         P(dim), P(ind), P(esc)])
        else:
            data.append([P(""), P(""), P(""), P(dim), P(ind), P(esc)])

    PAGE_W = 21*cm - ML - MR
    cw = [3.0*cm, 3.5*cm, 3.5*cm, 2.5*cm, 3.5*cm, 1.5*cm]

    vi_r1 = 1
    vi_r2 = n_vi          # inclusive
    vd_r1 = n_vi + 1
    vd_r2 = n_vi + n_vd   # inclusive

    style_cmds = [
        ('BACKGROUND',    (0, 0),      (-1, 0),      _c.HexColor('#1e3a5f')),
        ('TEXTCOLOR',     (0, 0),      (-1, 0),      _c.white),
        ('FONTNAME',      (0, 0),      (-1, -1),     _F),
        ('FONTSIZE',      (0, 0),      (-1, -1),     8),
        ('ALIGN',         (0, 0),      (-1, -1),     'LEFT'),
        ('VALIGN',        (0, 0),      (-1, -1),     'TOP'),
        ('VALIGN',        (0, vi_r1),  (2, vi_r2),   'MIDDLE'),
        ('VALIGN',        (0, vd_r1),  (2, vd_r2),   'MIDDLE'),
        ('GRID',          (0, 0),      (-1, -1),     0.5, _c.HexColor('#c0c8d8')),
        ('TOPPADDING',    (0, 0),      (-1, -1),     3),
        ('BOTTOMPADDING', (0, 0),      (-1, -1),     3),
        ('LEFTPADDING',   (0, 0),      (-1, -1),     3),
        ('RIGHTPADDING',  (0, 0),      (-1, -1),     3),
        ('BACKGROUND',    (0, vi_r1),  (-1, vi_r2),  _c.HexColor('#f0f4fa')),
        ('BACKGROUND',    (0, vd_r1),  (-1, vd_r2),  _c.white),
        # Celdas combinadas: cols 0,1,2 para todas las filas de VI
        ('SPAN',          (0, vi_r1),  (0, vi_r2)),
        ('SPAN',          (1, vi_r1),  (1, vi_r2)),
        ('SPAN',          (2, vi_r1),  (2, vi_r2)),
        # Celdas combinadas: cols 0,1,2 para todas las filas de VD
        ('SPAN',          (0, vd_r1),  (0, vd_r2)),
        ('SPAN',          (1, vd_r1),  (1, vd_r2)),
        ('SPAN',          (2, vd_r1),  (2, vd_r2)),
    ]

    t = _T(data, colWidths=cw, repeatRows=1)
    t.setStyle(_TS(style_cmds))
    story.append(t)


def _docx_operacionalizacion_table(doc, title: str):
    """
    Agrega la Matriz de Operacionalización de Variables a un DOCX.
    6 columnas con celdas combinadas para VI y VD.
    Formato exacto de plantilla UNT.
    """
    vi, vd = _extract_vi_vd(title)
    kw = " ".join(title.split()[:3])

    vi_def_c = (
        f"Solución tecnológica/metodológica que permite {kw.lower()} de manera sistemática "
        f"y eficiente, optimizando los procesos del área de estudio."
    )
    vi_def_o = (
        f"Medido mediante criterios técnicos de funcionalidad, usabilidad, rendimiento "
        f"y confiabilidad, con cuestionario validado (α = 0.912)."
    )
    vd_def_c = (
        f"Resultado cuantificable que refleja el nivel de desempeño en {vd.lower()}, "
        f"incluyendo indicadores de eficiencia, calidad y satisfacción."
    )
    vd_def_o = (
        f"Medición directa de indicadores antes y después de la implementación, "
        f"mediante instrumentos validados por expertos (CVC = 0.87)."
    )

    vi_dims = [
        ("Funcionalidad",
         "• Cobertura de requisitos funcionales (%)\n• N.° módulos implementados / planificados",
         "Razón\nNominal"),
        ("Usabilidad",
         "• Tiempo promedio para completar tareas (min)\n• Puntuación SUS",
         "Continua\nOrdinal"),
        ("Rendimiento",
         "• Tiempo de respuesta del sistema (seg)\n• Disponibilidad del sistema (%)",
         "Continua\nRazón"),
        ("Confiabilidad",
         "• Tasa de errores (%)\n• Tiempo medio entre fallos (horas)",
         "Razón\nContinua"),
    ]
    vd_dims = [
        ("Eficiencia operativa",
         "• Tiempo promedio de proceso (min)\n• Reducción vs. línea base (%)",
         "Razón"),
        ("Calidad del servicio",
         "• Porcentaje de conformidad (%)\n• Índice de calidad percibida (1-5)",
         "Razón\nOrdinal"),
        ("Satisfacción del usuario",
         "• Índice de satisfacción (1-5)\n• Porcentaje de usuarios satisfechos (%)",
         "Ordinal\nRazón"),
        ("Reducción de errores",
         "• Tasa de error pre vs. post (%)\n• N.° de incidencias registradas",
         "Razón\nNominal"),
        ("Costo operativo",
         "• Costo unitario de proceso (S/.)\n• Ahorro mensual estimado (S/.)",
         "Razón"),
        ("Cumplimiento normativo",
         "• Porcentaje de cumplimiento (%)\n• N.° de no conformidades",
         "Nominal\nRazón"),
    ]

    n_vi = len(vi_dims)
    n_vd = len(vd_dims)
    total = 1 + n_vi + n_vd

    t = doc.add_table(rows=total, cols=6)
    t.style = 'Table Grid'

    headers = [
        "Variable", "Definición Conceptual", "Definición Operacional",
        "Dimensión", "Indicador", "Escala de Medición"
    ]
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = h
        _set_cell_bg(c, '1e3a5f')
        for para in c.paragraphs:
            for run in para.runs:
                run.bold = True
                run.font.size = _Pt(8)
                run.font.color.rgb = RGBColor(0xff, 0xff, 0xff)

    def _fill_row(row_obj, col0, col1, col2, dim, ind, esc):
        vals = [col0, col1, col2, dim, ind, esc]
        for ci, val in enumerate(vals):
            c = row_obj.cells[ci]
            c.text = val
            for para in c.paragraphs:
                for run in para.runs:
                    run.font.size = _Pt(8)
                    run.font.name = 'Arial Narrow'

    # VI rows
    for i, (dim, ind, esc) in enumerate(vi_dims):
        row_obj = t.rows[1 + i]
        c0 = f"Independiente:\n{vi}" if i == 0 else ""
        c1 = vi_def_c if i == 0 else ""
        c2 = vi_def_o if i == 0 else ""
        _fill_row(row_obj, c0, c1, c2, dim, ind, esc)

    # Merge VI cols 0,1,2
    if n_vi > 1:
        t.cell(1, 0).merge(t.cell(n_vi, 0))
        t.cell(1, 1).merge(t.cell(n_vi, 1))
        t.cell(1, 2).merge(t.cell(n_vi, 2))

    # VD rows
    vd_start = 1 + n_vi
    for i, (dim, ind, esc) in enumerate(vd_dims):
        row_obj = t.rows[vd_start + i]
        c0 = f"Dependiente:\n{vd}" if i == 0 else ""
        c1 = vd_def_c if i == 0 else ""
        c2 = vd_def_o if i == 0 else ""
        _fill_row(row_obj, c0, c1, c2, dim, ind, esc)

    # Merge VD cols 0,1,2
    if n_vd > 1:
        t.cell(vd_start, 0).merge(t.cell(vd_start + n_vd - 1, 0))
        t.cell(vd_start, 1).merge(t.cell(vd_start + n_vd - 1, 1))
        t.cell(vd_start, 2).merge(t.cell(vd_start + n_vd - 1, 2))

    return t


# ── Contenido: Proyecto de Tesis ───────────────────────────────────────────────

def _content_proyecto_tesis(title: str, rl: str) -> dict:
    """Genera el contenido completo para un Proyecto de Tesis."""
    sec = _intro_text({'title': title, 'research_line': rl}, _gen_references(title))
    sec['resumen'] = _resumen(title, rl)
    sec['abstract'] = _abstract(title, rl)

    kw = " ".join(title.split()[:4])
    year = datetime.now().year

    sec['cap2_proyecto'] = (
        f"La investigación se enmarca en un enfoque cuantitativo con diseño pre-experimental "
        f"de un solo grupo con pre y post test. El tipo de investigación es aplicada, ya que busca "
        f"resolver una problemática concreta relacionada con {kw}. El nivel es explicativo-correlacional, "
        f"orientado a determinar el efecto de la variable independiente sobre la dependiente. "
        f"La población está constituida por 180 colaboradores del área de estudio, y la muestra, "
        f"calculada mediante muestreo aleatorio estratificado con un 95% de confianza y margen de error "
        f"del 5%, asciende a 123 participantes. Los instrumentos han sido validados mediante juicio de "
        f"expertos (CVC = 0.87) y prueba de confiabilidad (α = 0.912, Cronbach)."
    )

    sec['cronograma_rows'] = _tabla_cronograma(title)
    sec['presupuesto_rows'] = _tabla_presupuesto(title)

    return sec


# ── Contenido: Artículo de Investigación ──────────────────────────────────────

def _content_articulo(title: str, rl: str) -> dict:
    """Genera el contenido para un Artículo de Investigación."""
    kw = " ".join(title.split()[:5])
    year = datetime.now().year

    abstract_es = (
        f"El presente artículo analiza el impacto de {kw} en el contexto peruano, "
        f"abordando la problemática desde una perspectiva cuantitativa. Se aplicó un diseño "
        f"cuasi-experimental con pre y post test a una muestra de 123 participantes seleccionados "
        f"mediante muestreo aleatorio estratificado. Los resultados evidencian mejoras "
        f"estadísticamente significativas (p < 0.05) en los indicadores clave tras la implementación "
        f"de la propuesta. Se concluye que {kw} contribuye de manera efectiva a la optimización "
        f"de los procesos estudiados. Se recomienda ampliar el estudio a contextos institucionales "
        f"similares para validar la generalización de los hallazgos."
    )
    abstract_en = (
        f"This article analyzes the impact of {kw} in the Peruvian context, addressing the "
        f"problematic from a quantitative perspective. A quasi-experimental design with pre and "
        f"post-test was applied to a sample of 123 participants selected through stratified random "
        f"sampling. Results show statistically significant improvements (p < 0.05) in key indicators "
        f"after the implementation of the proposal. It is concluded that {kw} effectively contributes "
        f"to the optimization of the studied processes. Further research is recommended to validate "
        f"generalization across similar institutional contexts."
    )

    introduction = (
        f"En la actualidad, {kw} representa uno de los ejes centrales del desarrollo organizacional "
        f"y tecnológico en América Latina. Diversos organismos internacionales, como la UNESCO y el "
        f"Banco Mundial, han señalado la necesidad de adoptar estrategias basadas en evidencia para "
        f"mejorar los procesos vinculados a {kw}. En el contexto peruano, la situación no es diferente: "
        f"múltiples estudios evidencian brechas significativas en la implementación de soluciones "
        f"tecnológicas que optimicen {kw}. El presente artículo tiene como objetivo evaluar el efecto "
        f"de una intervención sistemática sobre los indicadores de desempeño asociados a {kw}, "
        f"contribuyendo así al cuerpo de conocimiento existente en la materia."
    )

    methodology = (
        f"Se empleó un diseño cuasi-experimental con un grupo de control y un grupo experimental. "
        f"La muestra estuvo conformada por 123 participantes (n = 123) seleccionados mediante "
        f"muestreo aleatorio estratificado con un nivel de confianza del 95% y margen de error del 5%. "
        f"El instrumento de recolección fue un cuestionario estructurado de 25 ítems (escala Likert 1-5), "
        f"validado mediante juicio de expertos (CVC = 0.87) y con alta confiabilidad (α = 0.912). "
        f"El análisis estadístico incluyó pruebas de normalidad (Shapiro-Wilk), estadística descriptiva "
        f"e inferencial (prueba t de Student para datos paramétricos y Wilcoxon para no paramétricos), "
        f"procesados con SPSS v.26."
    )

    results = (
        f"Los resultados del pre-test mostraron que el 68.3% de los participantes presentaban "
        f"niveles insatisfactorios en los indicadores evaluados. Tras la implementación de la "
        f"intervención relacionada con {kw}, el post-test reveló una mejora significativa: el 84.6% "
        f"alcanzó niveles satisfactorios o superiores. La prueba t de Student arrojó un valor "
        f"t(122) = 8.47, p < 0.001, IC 95% [12.3, 19.8], lo que indica diferencias estadísticamente "
        f"significativas entre el pre y post test. El tamaño del efecto (d de Cohen = 1.52) "
        f"refleja un impacto grande de la intervención propuesta."
    )

    discussion = (
        f"Los hallazgos obtenidos son consistentes con lo reportado por investigaciones previas "
        f"sobre {kw}. En línea con los postulados de la Teoría de Aceptación Tecnológica (TAM), "
        f"los participantes mostraron alta percepción de utilidad y facilidad de uso, lo que facilitó "
        f"la adopción de las estrategias propuestas. Estos resultados contrastan con estudios de "
        f"contextos similares que reportan tasas de mejora menores, posiblemente por diferencias "
        f"metodológicas o en las características de la muestra. Las implicaciones prácticas sugieren "
        f"que la réplica de esta intervención en instituciones similares podría generar beneficios "
        f"comparables, siempre que se garanticen las condiciones de capacitación y seguimiento."
    )

    conclusions = (
        f"Se concluye que la implementación de la propuesta relacionada con {kw} generó mejoras "
        f"estadísticamente significativas (p < 0.001) en los indicadores de desempeño evaluados, "
        f"con un tamaño de efecto grande (d = 1.52). La intervención demostró ser viable, replicable "
        f"y pertinente para el contexto peruano. Se recomienda realizar estudios longitudinales para "
        f"evaluar la sostenibilidad de los efectos a largo plazo, así como ampliar la muestra a "
        f"contextos geográficos e institucionales distintos para fortalecer la validez externa del estudio."
    )

    return {
        'resumen':      abstract_es,
        'abstract':     abstract_en,
        'introduction': introduction,
        'methodology':  methodology,
        'results':      results,
        'discussion':   discussion,
        'conclusions':  conclusions,
    }


# ── Mapeo de sección de plantilla → contenido ──────────────────────────────────

def _map_section_to_content(section_title: str, title: str, rl: str,
                             all_sec: dict) -> str:
    """Devuelve contenido textual para una sección de plantilla dado su título."""
    norm = section_title.lower()
    for c in 'áéíóú':
        norm = norm.replace(c, 'aeiou'['áéíóú'.index(c)])

    if any(k in norm for k in ['realidad problem', 'situacion problem', 'contexto']):
        return _rp(title, rl)
    if any(k in norm for k in ['antecedente', 'estado del arte', 'trabajos previos']):
        return _ant(title)
    if any(k in norm for k in ['marco teorico', 'bases teoricas', 'fundamentacion']):
        return _mt(title, rl)
    if any(k in norm for k in ['justificacion', 'importancia', 'relevancia']):
        return _just(title)
    if any(k in norm for k in ['planteamiento', 'problema de investigacion', 'formulacion']):
        return all_sec.get('prob', f"¿De qué manera {title.split()[0] if title else 'la propuesta'} influye en los resultados organizacionales?")
    if any(k in norm for k in ['hipotesis', 'suposicion']):
        return all_sec.get('hip', f"La implementación de {' '.join(title.split()[:4])} mejora significativamente los indicadores de desempeño (p < 0.05).")
    if any(k in norm for k in ['objetivo general']):
        return all_sec.get('obj_gen', f"Determinar el efecto de {' '.join(title.split()[:4])} sobre los indicadores de desempeño organizacional.")
    if any(k in norm for k in ['objetivo especific', 'objetivos especificos']):
        obj = all_sec.get('obj_esp', [])
        return '\n'.join(f"OE{i+1}: {o}" for i, o in enumerate(obj[:3])) if obj else ''
    if any(k in norm for k in ['limitacion', 'delimitacion', 'alcance']):
        return all_sec.get('lim', f"El estudio se delimita geográficamente al ámbito de {rl or 'la institución evaluada'}, con una temporalidad de 12 meses.")
    if any(k in norm for k in ['metodolog', 'capitulo ii', 'tipo de investigacion',
                                'diseno', 'poblacion', 'muestra']):
        return all_sec.get('cap2', _cap2(title, rl)).get('tipo', _cap2(title, rl)) if isinstance(all_sec.get('cap2'), dict) else all_sec.get('cap2', _cap2(title, rl))
    if any(k in norm for k in ['resultado', 'capitulo iii', 'hallazgos']):
        return all_sec.get('cap3', _cap3(title))
    if any(k in norm for k in ['discusion', 'capitulo iv', 'interpretacion']):
        return all_sec.get('cap4', _cap4(title))
    if any(k in norm for k in ['conclusion', 'recomendacion', 'capitulo v']):
        return all_sec.get('cap5', _cap5(title))
    if any(k in norm for k in ['resumen', 'abstract']):
        return all_sec.get('resumen', _resumen(title, rl))
    if any(k in norm for k in ['introducc', 'capitulo i']):
        return _rp(title, rl)
    # Contenido genérico para secciones no reconocidas
    kw = ' '.join(title.split()[:4])
    return (
        f"En el marco de la investigación sobre {kw}, esta sección desarrolla los aspectos "
        f"correspondientes a {section_title}, tomando como referencia los lineamientos "
        f"establecidos por las normas académicas vigentes y los estándares internacionales "
        f"de investigación científica. El análisis se sustenta en la revisión sistemática de "
        f"la literatura especializada y en los datos primarios recolectados durante el trabajo de campo."
    )


# ── PDF: Proyecto de Tesis ─────────────────────────────────────────────────────

def _build_pdf_proyecto(data: dict, sec: dict, refs: list, uid: str, logo_path: str = None) -> str:
    _register_fonts()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/doc_{uid}.pdf"

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
    )
    s = _s()
    story = []

    def sp(h=10): story.append(Spacer(1, h))
    def p(text, style='n'): story.append(Paragraph(str(text), s[style]))
    def br(): story.append(PageBreak())
    def tbl(headers, rows, widths=None): story.append(_make_table(headers, rows, widths))

    # ── CARÁTULA
    sp(30)
    if logo_path and os.path.exists(logo_path):
        try:
            from reportlab.platypus import Image as _RLImg
            lg = _RLImg(logo_path, width=4*cm, height=4*cm)
            lg.hAlign = 'CENTER'
            story.append(lg)
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
    p("PROYECTO DE TESIS PARA OPTAR EL TÍTULO PROFESIONAL DE INGENIERO DE SISTEMAS", 'c')
    sp(30)
    authors = data.get('authors', ['Autor'])
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]
    p("AUTOR(ES):", 'c')
    for a in authors:
        p(a.upper(), 'c')
    sp(16)
    p("ASESOR:", 'c')
    p(data.get('advisor', '').upper(), 'c')
    sp(16)
    p("LÍNEA DE INVESTIGACIÓN:", 'c')
    p(data.get('research_line', '').upper(), 'c')
    sp(40)
    p(f"{data.get('city', 'Trujillo').upper()} — PERÚ", 'c')
    p(str(data.get('year', datetime.now().year)), 'c')
    br()

    # ── RESUMEN
    p("RESUMEN", 'h1')
    sp(10)
    p(sec.get('resumen', ''), 'n')
    sp(8)
    p(f"<b>Palabras clave:</b> investigación, metodología, tecnología, innovación, {data['title'].split()[0].lower()}", 'n')
    br()

    p("ABSTRACT", 'h1')
    sp(10)
    p(sec.get('abstract', ''), 'n')
    sp(8)
    p(f"<b>Keywords:</b> research, methodology, technology, innovation, {data['title'].split()[0].lower()}", 'n')
    br()

    # ── CAPÍTULO I
    p("CAPÍTULO I: EL PROBLEMA DE INVESTIGACIÓN", 'h1')
    sp(10)
    p("1.1 Realidad Problemática", 'h2')
    p(sec.get('rp', ''), 'n')
    sp(8)
    p("1.2 Antecedentes", 'h2')
    p(sec.get('ant', ''), 'n')
    sp(8)
    p("1.3 Marco Teórico", 'h2')
    mt_val = sec.get('mt', '')
    if isinstance(mt_val, dict):
        for k, v in mt_val.items():
            p(str(v), 'n')
    else:
        p(str(mt_val), 'n')
    sp(8)
    p("1.4 Justificación", 'h2')
    just_val = sec.get('just', '')
    if isinstance(just_val, dict):
        for v in just_val.values():
            p(str(v), 'n')
    else:
        p(str(just_val), 'n')
    sp(8)
    p("1.5 Planteamiento del Problema", 'h2')
    p(sec.get('prob', ''), 'n')
    sp(8)
    p("1.6 Hipótesis", 'h2')
    p(sec.get('hip', ''), 'n')
    sp(8)
    p("1.7 Objetivos", 'h2')
    p("1.7.1 Objetivo General", 'h3')
    p(sec.get('obj_gen', ''), 'n')
    p("1.7.2 Objetivos Específicos", 'h3')
    for i, o in enumerate(sec.get('obj_esp', [])[:3], 1):
        p(f"OE{i}: {o}", 'n')
    sp(8)
    p("1.8 Limitaciones", 'h2')
    lim_val = sec.get('lim', '')
    if isinstance(lim_val, list):
        for l in lim_val:
            p(str(l), 'n')
    else:
        p(str(lim_val), 'n')
    br()

    # ── CAPÍTULO II: MÉTODO
    p("CAPÍTULO II: MÉTODO", 'h1')
    sp(10)
    p(sec.get('cap2_proyecto', ''), 'n')
    sp(8)
    p("2.1 Variables y Operacionalización", 'h2')
    sp(6)
    _pdf_operacionalizacion_table(story, data['title'])
    br()

    # ── CAPÍTULO III: ASPECTOS ADMINISTRATIVOS
    p("CAPÍTULO III: ASPECTOS ADMINISTRATIVOS", 'h1')
    sp(10)
    p("3.1 Cronograma de Actividades", 'h2')
    sp(6)
    cron_rows = sec.get('cronograma_rows', _tabla_cronograma(data['title']))
    tbl(
        ["Actividad", "Mes 1", "Mes 2", "Mes 3", "Mes 4", "Mes 5", "Mes 6"],
        cron_rows,
        [7*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm],
    )
    sp(16)
    p("3.2 Presupuesto", 'h2')
    sp(6)
    pres_rows = sec.get('presupuesto_rows', _tabla_presupuesto(data['title']))
    tbl(
        ["Descripción", "Cantidad/Tiempo", "Precio unitario", "Total"],
        pres_rows,
        [7*cm, 3.5*cm, 3.5*cm, 3*cm],
    )
    br()

    # ── REFERENCIAS
    p("REFERENCIAS BIBLIOGRÁFICAS", 'h1')
    sp(10)
    for ref in refs[:25]:
        p(ref, 'ref')
    br()

    # ── ANEXOS (orden oficial UNT 2026)
    p("ANEXOS", 'h1')
    sp(10)
    p("Anexo 1: Operacionalización de Variables", 'h2')
    sp(6)
    _pdf_operacionalizacion_table(story, data['title'])
    sp(20)
    p("Anexo 2: Matriz de Consistencia", 'h2')
    sp(4)
    p(f"Título: \"{data['title']}\"", 'n')
    sp(6)
    _pdf_consistencia_table(story, data['title'], sec)
    sp(20)
    p("Anexo 3: Diagrama de Ishikawa", 'h2')
    sp(6)
    _pdf_ichikawa_diagram(story, data['title'])
    sp(20)
    p("Anexo 4: Árbol de Problemas", 'h2')
    sp(6)
    _pdf_arbol_diagram(story, data['title'], 'problemas')
    sp(20)
    p("Anexo 5: Árbol de Objetivos", 'h2')
    sp(6)
    _pdf_arbol_diagram(story, data['title'], 'objetivos')
    sp(20)
    p("Anexo 6: Declaración Jurada de Autoría", 'h2')
    sp(10)
    p(
        f"Yo/Nosotros, {', '.join(authors)}, declaro/declaramos bajo juramento que el proyecto "
        f"de tesis titulado «{data['title']}» es de mi/nuestra autoría, no ha sido plagiado "
        f"ni publicado anteriormente.", 'n'
    )
    sp(20)
    for a in authors:
        p("_______________________________", 'c')
        p(a.upper(), 'c')
        sp(10)

    doc.build(story)
    return path


# ── DOCX: Proyecto de Tesis ────────────────────────────────────────────────────

def _build_docx_proyecto(data: dict, sec: dict, refs: list, uid: str, logo_path: str = None) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/doc_{uid}.docx"

    doc = _DocxDoc()
    _set_docx_margins(doc)

    authors = data.get('authors', 'Autor')
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]

    def add_h(text, level=1):
        h = doc.add_heading(text, level=level)
        for run in h.runs:
            run.font.color.rgb = RGBColor(0x1e, 0x3a, 0x5f)

    def add_para(text, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        para = doc.add_paragraph()
        para.paragraph_format.line_spacing = _Pt(20)
        run = para.add_run(str(text))
        run.font.name = 'Arial Narrow'
        run.font.size = _Pt(12)
        run.bold = bold
        para.alignment = align

    def add_table_docx(headers, rows):
        if not rows:
            return
        t = doc.add_table(rows=1 + len(rows), cols=len(headers))
        t.style = 'Table Grid'
        for i, h in enumerate(headers):
            cell = t.rows[0].cells[i]
            cell.text = h
            for run in cell.paragraphs[0].runs:
                run.bold = True
                run.font.size = _Pt(9)
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row[:len(headers)]):
                t.rows[r_idx + 1].cells[c_idx].text = str(val)

    # Carátula
    add_para("UNIVERSIDAD NACIONAL DE TRUJILLO", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para("FACULTAD DE INGENIERÍA", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para("ESCUELA PROFESIONAL DE INGENIERÍA DE SISTEMAS", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para("")
    add_para("PROYECTO DE TESIS PARA OPTAR EL TÍTULO PROFESIONAL\nDE INGENIERO DE SISTEMAS", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para("")
    add_para(data['title'].upper(), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para("")
    add_para("AUTOR(ES):", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for a in authors:
        add_para(a.upper(), align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(f"ASESOR: {data.get('advisor','').upper()}", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(f"LÍNEA DE INVESTIGACIÓN: {data.get('research_line','').upper()}", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(f"{data.get('city','Trujillo').upper()} — PERÚ   {data.get('year', datetime.now().year)}", align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_page_break()

    # Resumen
    add_h("RESUMEN", 1)
    add_para(sec.get('resumen', ''))
    doc.add_page_break()

    # Abstract
    add_h("ABSTRACT", 1)
    add_para(sec.get('abstract', ''))
    doc.add_page_break()

    # Cap I
    add_h("CAPÍTULO I: EL PROBLEMA DE INVESTIGACIÓN", 1)
    for subh, key in [
        ("1.1 Realidad Problemática", 'rp'),
        ("1.2 Antecedentes", 'ant'),
        ("1.4 Justificación", 'just'),
    ]:
        add_h(subh, 2)
        val = sec.get(key, '')
        if isinstance(val, dict):
            for v in val.values():
                add_para(str(v))
        elif isinstance(val, list):
            for v in val:
                add_para(str(v))
        else:
            add_para(str(val))

    add_h("1.3 Marco Teórico", 2)
    mt_val = sec.get('mt', '')
    if isinstance(mt_val, dict):
        for v in mt_val.values():
            add_para(str(v))
    else:
        add_para(str(mt_val))

    add_h("1.5 Planteamiento del Problema", 2)
    add_para(sec.get('prob', ''))
    add_h("1.6 Hipótesis", 2)
    add_para(sec.get('hip', ''))
    add_h("1.7.1 Objetivo General", 3)
    add_para(sec.get('obj_gen', ''))
    add_h("1.7.2 Objetivos Específicos", 3)
    for i, o in enumerate(sec.get('obj_esp', [])[:3], 1):
        add_para(f"OE{i}: {o}")
    add_h("1.8 Limitaciones", 2)
    lim_val = sec.get('lim', '')
    if isinstance(lim_val, list):
        for l in lim_val:
            add_para(str(l))
    else:
        add_para(str(lim_val))
    doc.add_page_break()

    # Cap II
    add_h("CAPÍTULO II: MÉTODO", 1)
    add_para(sec.get('cap2_proyecto', ''))
    add_h("2.1 Operacionalización de Variables", 2)
    _docx_operacionalizacion_table(doc, data['title'])
    doc.add_page_break()

    # Cap III
    add_h("CAPÍTULO III: ASPECTOS ADMINISTRATIVOS", 1)
    add_h("3.1 Cronograma de Actividades", 2)
    cron_rows = sec.get('cronograma_rows', _tabla_cronograma(data['title']))
    add_table_docx(
        ["Actividad", "Mes 1", "Mes 2", "Mes 3", "Mes 4", "Mes 5", "Mes 6"],
        cron_rows,
    )
    add_h("3.2 Presupuesto", 2)
    pres_rows = sec.get('presupuesto_rows', _tabla_presupuesto(data['title']))
    add_table_docx(["Descripción", "Cantidad/Tiempo", "Precio unitario", "Total"], pres_rows)
    doc.add_page_break()

    # Referencias
    add_h("REFERENCIAS BIBLIOGRÁFICAS", 1)
    for ref in refs[:25]:
        add_para(ref)
    doc.add_page_break()

    # Anexos (orden oficial UNT 2026)
    add_h("ANEXOS", 1)
    add_h("Anexo 1: Operacionalización de Variables", 2)
    _docx_operacionalizacion_table(doc, data['title'])
    doc.add_page_break()
    add_h("Anexo 2: Matriz de Consistencia", 2)
    add_para(f"Título: \"{data['title']}\"")
    _docx_consistencia_table(doc, data['title'], sec)
    doc.add_page_break()
    add_h("Anexo 3: Diagrama de Ishikawa", 2)
    _docx_ichikawa_diagram(doc, data['title'])
    doc.add_page_break()
    add_h("Anexo 4: Árbol de Problemas", 2)
    _docx_arbol_diagram(doc, data['title'], 'problemas')
    doc.add_page_break()
    add_h("Anexo 5: Árbol de Objetivos", 2)
    _docx_arbol_diagram(doc, data['title'], 'objetivos')
    doc.add_page_break()
    add_h("Anexo 6: Declaración Jurada de Autoría", 2)
    add_para(
        f"Yo/Nosotros, {', '.join(authors)}, declaro/declaramos bajo juramento que el proyecto "
        f"«{data['title']}» es de nuestra autoría y no ha sido plagiado."
    )

    doc.save(path)
    return path


# ── PDF: Artículo de Investigación ────────────────────────────────────────────

def _build_pdf_articulo(data: dict, sec: dict, refs: list, uid: str, logo_path: str = None) -> str:
    _register_fonts()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/doc_{uid}.pdf"

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
    )
    s = _s()
    story = []

    def sp(h=10): story.append(Spacer(1, h))
    def p(text, style='n'): story.append(Paragraph(str(text), s[style]))
    def br(): story.append(PageBreak())

    authors = data.get('authors', 'Autor')
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]

    # Encabezado del artículo
    sp(20)
    p(data['title'], 'h1')
    sp(10)
    p(' · '.join(authors), 'c')
    p(f"Universidad Nacional de Trujillo · {data.get('city', 'Trujillo')}", 'c')
    sp(6)
    p(f"Correo: investigacion@unitru.edu.pe · Año: {data.get('year', datetime.now().year)}", 'c')
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#1e3a5f')))
    sp(10)

    # Resumen
    p("Resumen", 'h2')
    p(sec.get('resumen', ''), 'n')
    sp(6)
    kw_list = ' '.join(data['title'].split()[:5]).lower()
    p(f"<b>Palabras clave:</b> {kw_list}, investigación cuantitativa, metodología aplicada.", 'n')
    sp(12)
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#c0c8d8')))
    sp(12)

    # Abstract
    p("Abstract", 'h2')
    p(sec.get('abstract', ''), 'n')
    sp(6)
    p(f"<b>Keywords:</b> {kw_list}, quantitative research, applied methodology.", 'n')
    br()

    # Secciones del artículo
    sections_map = [
        ("I. INTRODUCCIÓN", 'introduction'),
        ("II. MATERIALES Y MÉTODOS", 'methodology'),
        ("III. RESULTADOS", 'results'),
        ("IV. DISCUSIÓN", 'discussion'),
        ("V. CONCLUSIONES", 'conclusions'),
    ]
    for heading, key in sections_map:
        p(heading, 'h1')
        sp(6)
        content = sec.get(key, '')
        if isinstance(content, (list, dict)):
            p(str(content), 'n')
        else:
            p(str(content), 'n')
        sp(12)

    br()

    # Referencias
    p("REFERENCIAS", 'h1')
    sp(10)
    for ref in refs[:20]:
        p(ref, 'ref')

    doc.build(story)
    return path


# ── DOCX: Artículo de Investigación ───────────────────────────────────────────

def _build_docx_articulo(data: dict, sec: dict, refs: list, uid: str, logo_path: str = None) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/doc_{uid}.docx"

    doc = _DocxDoc()
    _set_docx_margins(doc)

    authors = data.get('authors', 'Autor')
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]

    def add_h(text, level=1):
        h = doc.add_heading(text, level=level)
        for run in h.runs:
            run.font.color.rgb = RGBColor(0x1e, 0x3a, 0x5f)

    def add_para(text, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        para = doc.add_paragraph()
        para.paragraph_format.line_spacing = _Pt(20)
        run = para.add_run(str(text))
        run.font.name = 'Arial Narrow'
        run.font.size = _Pt(12)
        run.bold = bold
        para.alignment = align

    add_h(data['title'], 1)
    add_para(' · '.join(authors), align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(f"Universidad Nacional de Trujillo · {data.get('city','Trujillo')}", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para("")

    add_h("Resumen", 2)
    add_para(sec.get('resumen', ''))
    kw_list = ' '.join(data['title'].split()[:5]).lower()
    add_para(f"Palabras clave: {kw_list}, investigación cuantitativa.")

    add_h("Abstract", 2)
    add_para(sec.get('abstract', ''))
    add_para(f"Keywords: {kw_list}, quantitative research.")

    doc.add_page_break()

    for heading, key in [
        ("I. INTRODUCCIÓN", 'introduction'),
        ("II. MATERIALES Y MÉTODOS", 'methodology'),
        ("III. RESULTADOS", 'results'),
        ("IV. DISCUSIÓN", 'discussion'),
        ("V. CONCLUSIONES", 'conclusions'),
    ]:
        add_h(heading, 1)
        content = sec.get(key, '')
        add_para(str(content) if not isinstance(content, str) else content)

    doc.add_page_break()

    add_h("REFERENCIAS", 1)
    for ref in refs[:20]:
        add_para(ref)

    doc.save(path)
    return path


# ── Helper DOCX: márgenes ─────────────────────────────────────────────────────

def _set_docx_margins(doc):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    section = doc.sections[0]
    section.left_margin   = _Cm(3)
    section.right_margin  = _Cm(2.5)
    section.top_margin    = _Cm(2.5)
    section.bottom_margin = _Cm(2.5)


# ── PDF/DOCX basado en plantilla ──────────────────────────────────────────────

def _build_pdf_from_template(data: dict, template_structure: dict, all_sec: dict,
                              refs: list, uid: str, logo_path: str = None) -> str:
    """Construye un PDF siguiendo la estructura de una plantilla analizada."""
    _register_fonts()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/doc_{uid}.pdf"

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
    )
    s = _s()
    story = []

    def sp(h=10): story.append(Spacer(1, h))
    def p(text, style='n'): story.append(Paragraph(str(text)[:8000], s[style]))
    def br(): story.append(PageBreak())
    def tbl(headers, rows, widths=None): story.append(_make_table(headers, rows, widths))

    rl = data.get('research_line', '')
    title = data['title']
    table_idx = 0
    tables_in_template = template_structure.get('tables', [])

    # Carátula siempre
    sp(30)
    if logo_path and os.path.exists(logo_path):
        try:
            from reportlab.platypus import Image as _RLImg
            lg = _RLImg(logo_path, width=4*cm, height=4*cm)
            lg.hAlign = 'CENTER'
            story.append(lg)
            sp(14)
        except Exception:
            sp(26)
    else:
        sp(30)
    p("UNIVERSIDAD NACIONAL DE TRUJILLO", 'h1')
    p("FACULTAD DE INGENIERÍA", 'c')
    p("ESCUELA PROFESIONAL DE INGENIERÍA DE SISTEMAS", 'c')
    sp(30)
    story.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#1e3a5f')))
    sp(16)
    p(title.upper(), 'h1')
    sp(16)
    story.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#1e3a5f')))
    sp(30)
    authors = data.get('authors', 'Autor')
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]
    for a in authors:
        p(a.upper(), 'c')
    p(f"Asesor: {data.get('advisor','')}", 'c')
    p(f"{data.get('city','Trujillo').upper()} — PERÚ   {data.get('year', datetime.now().year)}", 'c')
    br()

    # Recorrer secciones de la plantilla
    sections = template_structure.get('sections', [])
    if not sections:
        # Sin secciones detectadas: generar contenido estándar según tipo
        p("CONTENIDO PRINCIPAL", 'h1')
        p(_rp(title, rl), 'n')
        p(_ant(title), 'n')
    else:
        prev_level = 0
        for sec_item in sections:
            level = sec_item.get('level', 2)
            sec_title = sec_item.get('title', '')
            if not sec_title:
                continue

            style_key = 'h1' if level == 1 else ('h2' if level == 2 else 'h3')
            p(sec_title, style_key)
            sp(6)

            content = _map_section_to_content(sec_title, title, rl, all_sec)
            if content:
                if isinstance(content, list):
                    for item in content:
                        p(str(item), 'n')
                else:
                    p(str(content), 'n')
            sp(10)

            # Insertar tablas de la plantilla cuando correspondan
            norm_title = sec_title.lower()
            for acc in ['á','é','í','ó','ú']:
                norm_title = norm_title.replace(acc, 'aeiou'['áéíóú'.index(acc)])

            if any(k in norm_title for k in ['cronograma', 'actividade']):
                cron_rows = all_sec.get('cronograma_rows', _tabla_cronograma(title))
                tbl(["Actividad", "Mes 1", "Mes 2", "Mes 3", "Mes 4", "Mes 5", "Mes 6"], cron_rows,
                    [7*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm])
                sp(12)
            elif any(k in norm_title for k in ['presupuesto', 'recursos', 'financiamiento']):
                pres_rows = all_sec.get('presupuesto_rows', _tabla_presupuesto(title))
                tbl(["Descripción", "Cantidad", "Precio unit.", "Total"], pres_rows,
                    [7*cm, 3*cm, 3.5*cm, 3*cm])
                sp(12)
            elif any(k in norm_title for k in ['ishikawa', 'ichikawa', 'espina', 'pescado']):
                _pdf_ichikawa_diagram(story, title)
                sp(12)
            elif any(k in norm_title for k in ['arbol de prob', 'arbol prob', 'causa', 'causa efecto']):
                _pdf_arbol_diagram(story, title, 'problemas')
                sp(12)
            elif any(k in norm_title for k in ['arbol de obj', 'arbol obj', 'medio', 'medio fin']):
                _pdf_arbol_diagram(story, title, 'objetivos')
                sp(12)
            elif any(k in norm_title for k in ['operacionaliz']):
                _pdf_operacionalizacion_table(story, title)
                sp(12)
            elif any(k in norm_title for k in ['consistencia', 'matriz']):
                _pdf_consistencia_table(story, title, all_sec)
                sp(12)
            elif table_idx < len(tables_in_template):
                tpl_table = tables_in_template[table_idx]
                tpl_type  = tpl_table.get('type', 'generic')
                if tpl_type == 'cronograma':
                    tbl(["Actividad", "Mes 1", "Mes 2", "Mes 3", "Mes 4", "Mes 5", "Mes 6"],
                        _tabla_cronograma(title))
                elif tpl_type == 'presupuesto':
                    tbl(["Descripción", "Cantidad", "Precio unit.", "Total"], _tabla_presupuesto(title))
                elif tpl_type == 'operacionalizacion':
                    _pdf_operacionalizacion_table(story, title)
                elif tpl_type == 'consistencia':
                    _pdf_consistencia_table(story, title, all_sec)
                table_idx += 1

            if level == 1:
                br()

    # Referencias siempre al final
    p("REFERENCIAS BIBLIOGRÁFICAS", 'h1')
    sp(10)
    for ref in refs[:25]:
        p(ref, 'ref')

    doc.build(story)
    return path


def _build_docx_from_template(data: dict, template_structure: dict, all_sec: dict,
                               refs: list, uid: str, logo_path: str = None) -> str:
    """Construye un DOCX siguiendo la estructura de una plantilla analizada."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/doc_{uid}.docx"

    doc = _DocxDoc()
    _set_docx_margins(doc)

    title = data['title']
    rl    = data.get('research_line', '')

    authors = data.get('authors', 'Autor')
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]

    def add_h(text, level=1):
        h = doc.add_heading(str(text), level=level)
        for run in h.runs:
            run.font.color.rgb = RGBColor(0x1e, 0x3a, 0x5f)

    def add_para(text, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        para = doc.add_paragraph()
        para.paragraph_format.line_spacing = _Pt(20)
        run = para.add_run(str(text)[:8000])
        run.font.name = 'Arial Narrow'
        run.font.size = _Pt(12)
        run.bold = bold
        para.alignment = align

    def add_table_docx(headers, rows):
        if not rows:
            return
        t = doc.add_table(rows=1 + len(rows), cols=len(headers))
        t.style = 'Table Grid'
        for i, h in enumerate(headers):
            cell = t.rows[0].cells[i]
            cell.text = h
            for run in cell.paragraphs[0].runs:
                run.bold = True
                run.font.size = _Pt(9)
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row[:len(headers)]):
                t.rows[r_idx + 1].cells[c_idx].text = str(val)

    # Carátula
    add_para(title.upper(), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(' · '.join(authors), align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(f"Asesor: {data.get('advisor','')}", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(f"{data.get('city','Trujillo').upper()} — {data.get('year', datetime.now().year)}", align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_page_break()

    sections = template_structure.get('sections', [])
    if not sections:
        add_h("CONTENIDO", 1)
        add_para(_rp(title, rl))
        add_para(_ant(title))
    else:
        for sec_item in sections:
            level = sec_item.get('level', 2)
            sec_title = sec_item.get('title', '')
            if not sec_title:
                continue

            add_h(sec_title, min(level, 3))

            content = _map_section_to_content(sec_title, title, rl, all_sec)
            if content:
                if isinstance(content, list):
                    for item in content:
                        add_para(str(item))
                else:
                    add_para(str(content))

            norm_title = sec_title.lower()
            for acc in ['á','é','í','ó','ú']:
                norm_title = norm_title.replace(acc, 'aeiou'['áéíóú'.index(acc)])

            if any(k in norm_title for k in ['cronograma', 'actividade']):
                add_table_docx(
                    ["Actividad", "Mes 1", "Mes 2", "Mes 3", "Mes 4", "Mes 5", "Mes 6"],
                    all_sec.get('cronograma_rows', _tabla_cronograma(title)),
                )
            elif any(k in norm_title for k in ['presupuesto', 'recursos']):
                add_table_docx(
                    ["Descripción", "Cantidad", "Precio unit.", "Total"],
                    all_sec.get('presupuesto_rows', _tabla_presupuesto(title)),
                )
            elif any(k in norm_title for k in ['ishikawa', 'ichikawa', 'espina', 'pescado']):
                _docx_ichikawa_diagram(doc, title)
            elif any(k in norm_title for k in ['arbol de prob', 'arbol prob', 'causa', 'causa efecto']):
                _docx_arbol_diagram(doc, title, 'problemas')
            elif any(k in norm_title for k in ['arbol de obj', 'arbol obj', 'medio', 'medio fin']):
                _docx_arbol_diagram(doc, title, 'objetivos')
            elif any(k in norm_title for k in ['operacionaliz']):
                _docx_operacionalizacion_table(doc, title)
            elif any(k in norm_title for k in ['consistencia', 'matriz']):
                _docx_consistencia_table(doc, title, all_sec)

            if level == 1:
                doc.add_page_break()

    # Referencias
    add_h("REFERENCIAS BIBLIOGRÁFICAS", 1)
    for ref in refs[:25]:
        add_para(ref)

    doc.save(path)
    return path


# ── API pública extendida ─────────────────────────────────────────────────────

def generate_document(data: dict) -> dict:
    """
    Genera un documento académico completo (PDF + DOCX).

    data keys adicionales respecto a generate_thesis:
        doc_type          str  — "tesis" | "proyecto_tesis" | "articulo"
        template_structure dict — resultado de template_analyzer.analyze_template() (opcional)
    """
    import base64, tempfile

    uid   = uuid.uuid4().hex[:10]
    title = data.get('title', 'documento')
    rl    = data.get('research_line', '')
    doc_type = data.get('doc_type', 'tesis')
    template_structure = data.get('template_structure', None)

    refs = _gen_references(title)

    # Decodificar logo si viene en base64
    logo_path = None
    if data.get('logo_data'):
        try:
            raw = data['logo_data']
            b64 = raw.split(',', 1)[-1]
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
            print(f"[generate_document] logo decode error: {e}")

    # Jurado por defecto
    if not data.get('jurado'):
        rng = random.Random(abs(hash(title)) % 99999)
        prefixes  = ['Dr.', 'Mg.', 'Dr.']
        lastnames = ['García López', 'Rodríguez Sánchez', 'Martínez Torres',
                     'Pérez Castillo', 'Flores Ramírez', 'Soto Herrera']
        data['jurado'] = [f"{prefixes[i]} {rng.choice(lastnames)}" for i in range(3)]

    source = 'template'

    # Generar contenido según tipo de documento
    if doc_type == 'proyecto_tesis':
        sec = _content_proyecto_tesis(title, rl)
    elif doc_type == 'articulo':
        sec = _content_articulo(title, rl)
    else:
        # Tesis: flujo existente
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
            sec = _intro_text(data, refs)
        sec['resumen']  = _resumen(title, rl)
        sec['abstract'] = _abstract(title, rl)
        sec['cap2']     = _cap2(title, rl)
        sec['cap3']     = _cap3(title)
        sec['cap4']     = _cap4(title)
        sec['cap5']     = _cap5(title)

    # Construir PDF y DOCX
    if template_structure and template_structure.get('sections'):
        # Con plantilla: respetar su estructura
        pdf_path  = _build_pdf_from_template(data, template_structure, sec, refs, uid, logo_path)
        docx_path = _build_docx_from_template(data, template_structure, sec, refs, uid, logo_path)
    elif doc_type == 'proyecto_tesis':
        pdf_path  = _build_pdf_proyecto(data, sec, refs, uid, logo_path)
        docx_path = _build_docx_proyecto(data, sec, refs, uid, logo_path)
    elif doc_type == 'articulo':
        pdf_path  = _build_pdf_articulo(data, sec, refs, uid, logo_path)
        docx_path = _build_docx_articulo(data, sec, refs, uid, logo_path)
    else:
        pdf_path  = _build_pdf(data, sec, refs, uid, logo_path)
        docx_path = _build_docx(data, sec, refs, uid, logo_path)

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
        'doc_type':  doc_type,
        'sections':  {k: (v[:200] + '...' if isinstance(v, str) and len(v) > 200 else v)
                      for k, v in sec.items()
                      if isinstance(v, (str, list)) and not k.endswith('_rows')},
    }

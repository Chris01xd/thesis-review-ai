"""
Script de carga de datos demo.
Ejecutar una sola vez antes de la defensa:
    python seed_demo.py
"""
import sys, json, os, time
sys.path.insert(0, ".")

from modules.database import init_db, query, execute, now
from modules.ai_engine import local_agentic_analysis, agent_plan_for_document
from modules.plagiarism import run_similarity_check
from modules.citations import validate_citations

init_db()

# ── Verificar si ya hay datos ────────────────────────────────────────────────
existing = query("SELECT COUNT(*) AS c FROM advances")[0]["c"]
if existing >= 3:
    print(f"Ya existen {existing} avances en la base de datos. No se volvieron a crear.")
    sys.exit(0)

# ── Leer documento de muestra ────────────────────────────────────────────────
sample_path = "sample_documents/avance_demo.txt"
if not os.path.exists(sample_path):
    print(f"No se encontró {sample_path}. Usando texto genérico.")
    text = """
Universidad Nacional de Trujillo
Facultad de Ingeniería
Escuela Profesional de Ingeniería de Sistemas
Proyecto de Tesis

Título: Sistema web inteligente de gestión y predicción de desperdicio alimentario
Autor: Torres Kevin
Asesor: Dr. Pérez

Resumen
El presente proyecto propone el desarrollo de un sistema web inteligente para la gestión y
predicción de desperdicio alimentario en comedores universitarios. El sistema utilizará
técnicas de inteligencia artificial y aprendizaje automático para analizar patrones de
consumo y generar predicciones que permitan reducir el desperdicio.

Introducción
El desperdicio alimentario representa uno de los problemas más graves a nivel mundial.
Según la FAO (2021), aproximadamente un tercio de los alimentos producidos se desperdicia.

Planteamiento del problema
El alto índice de desperdicio alimentario en los comedores universitarios genera pérdidas
económicas significativas y un impacto ambiental negativo. El problema central identificado
mediante análisis causal es la falta de herramientas de predicción y gestión eficiente.

Antecedentes
A nivel internacional, Sharma (2022) desarrolló un sistema de predicción de demanda
alimentaria utilizando redes neuronales con una precisión del 87%.
Chen y Liu (2023) implementaron un modelo de aprendizaje automático para optimizar
inventarios alimentarios en instituciones educativas.
A nivel nacional, Mamani y Quispe (2021) propusieron un sistema de gestión de residuos
alimentarios en universidades peruanas.

Marco teórico
La Lean Supply Chain (Womack, 2003) propone la eliminación de desperdicios en la cadena
de suministro. La Economía Circular (Ellen MacArthur Foundation, 2015) plantea modelos
de producción y consumo sostenibles. Los Sistemas de Apoyo a la Toma de Decisiones
(Turban et al., 2018) integran datos y modelos para optimizar decisiones empresariales.

Objetivos
Objetivo general: Desarrollar un sistema web inteligente para la gestión y predicción
del desperdicio alimentario en comedores universitarios.
Objetivos específicos:
1. Analizar los patrones de consumo alimentario actuales.
2. Diseñar el modelo de predicción basado en inteligencia artificial.
3. Implementar el sistema web con interfaz intuitiva.
4. Evaluar el impacto del sistema en la reducción del desperdicio.

Justificación
Justificación teórica: contribuye al conocimiento sobre aplicación de IA en gestión alimentaria.
Justificación práctica: reduce pérdidas económicas y ambientales.
Justificación metodológica: aplica metodología CRISP-DM para proyectos de ciencia de datos.

Hipótesis
Ha: El sistema web inteligente reduce significativamente el desperdicio alimentario.
H0: El sistema web inteligente no reduce el desperdicio alimentario.

Metodología
Diseño preexperimental con preprueba y postprueba.
Población: 4 comedores universitarios de la región.
Muestra: 2 comedores seleccionados por conveniencia.
Instrumentos: encuestas, registros de consumo, sensores IoT.
Técnicas: análisis documental, observación, entrevistas.
Se aplicará la metodología Kimball para el diseño del data warehouse.

Limitaciones
El estudio se limita a los comedores de la Universidad Nacional de Trujillo.
El período de recolección de datos es de 6 meses.

Referencias
Chen, L. y Liu, M. (2023). Machine learning for food inventory optimization. Journal of
  Food Engineering, 45(2), 112-128. https://doi.org/10.1016/j.jfoodeng.2023.01.015
Ellen MacArthur Foundation. (2015). Towards a circular economy. EMF Publishing.
FAO. (2021). Global food losses and food waste. Food and Agriculture Organization.
Mamani, R. y Quispe, C. (2021). Sistema de gestión de residuos alimentarios universitarios.
  Revista Peruana de Ingeniería, 8(1), 34-49.
Sharma, A. (2022). Neural networks for food demand forecasting. International Journal of
  Artificial Intelligence, 19(3), 78-95. https://doi.org/10.1007/s10462-022-10234-5
Turban, E., Sharda, R. y Delen, D. (2018). Decision support and business intelligence systems.
  Pearson Education.
Womack, J. P. (2003). Lean thinking: Banish waste and create wealth. Free Press.

Matriz de consistencia
Variable independiente: Sistema web inteligente
Variable dependiente: Gestión y predicción de desperdicio alimentario
Indicadores: porcentaje de reducción de desperdicio, precisión del modelo, tiempo de respuesta.

Anexos
Anexo 1: Árbol de problemas
Anexo 2: Árbol de objetivos
Anexo 3: Matriz de operacionalización de variables
"""
else:
    with open(sample_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

print(f"Texto base: {len(text):,} caracteres")

# ── Obtener datos base ───────────────────────────────────────────────────────
student  = query("SELECT * FROM users WHERE role='STUDENT' LIMIT 1")[0]
advisor  = query("SELECT * FROM users WHERE role='ADVISOR'  LIMIT 1")[0]
template = query("SELECT * FROM templates WHERE active=1 LIMIT 1")[0]
rubric   = json.loads(template["rubric_json"])
expected = template["expected_sections"].split("|")

os.makedirs("data/uploads", exist_ok=True)

# ── Definir los 3 avances demo ────────────────────────────────────────────────
avances = [
    {
        "titulo": "Capítulo 1 - Planteamiento del problema",
        "tipo": "Capítulo 1",
        "status_final": "Aprobado",
        "human_grade": 14.5,
        "comment": "Buen planteamiento. Fortalecer la hipótesis con mayor precisión estadística.",
    },
    {
        "titulo": "Capítulo 2 - Marco teórico y antecedentes",
        "tipo": "Capítulo 2",
        "status_final": "Observado",
        "human_grade": 12.0,
        "comment": "El marco teórico requiere mayor profundidad. Ampliar antecedentes internacionales.",
    },
    {
        "titulo": "Proyecto de tesis - versión preliminar",
        "tipo": "Tesis completa",
        "status_final": "En revision humana",
        "human_grade": None,
        "comment": None,
    },
]

created = []
for av in avances:
    fname = f"demo_{int(time.time())}_{av['tipo'].replace(' ', '_')}.txt"
    fpath = f"data/uploads/{fname}"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(text)

    prev = query(
        "SELECT MAX(version) AS v FROM advances WHERE student_id=? AND advance_type=?",
        (student["id"], av["tipo"])
    )
    version = (prev[0]["v"] or 0) + 1

    adv_id = execute(
        """INSERT INTO advances(student_id,advisor_id,program_id,template_id,title,advance_type,
           version,filename,file_path,file_type,text_content,page_count,status,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (student["id"], advisor["id"], student["program_id"], template["id"],
         av["titulo"], av["tipo"], version, fname, fpath, "txt", text, 5, "Pendiente", now())
    )

    execute(
        "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
        ("Agente extractor de documentos", adv_id, "Finalizado",
         f"Texto: {len(text):,} chars", now(), now())
    )
    execute(
        "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
        ("Agente planificador", adv_id, "Finalizado",
         " | ".join(agent_plan_for_document(text)), now(), now())
    )

    # ── Análisis IA ─────────────────────────────────────────────────────────
    result = local_agentic_analysis(text, expected, rubric, av["tipo"])
    execute("DELETE FROM ai_analyses WHERE advance_id=?", (adv_id,))
    aid = execute(
        """INSERT INTO ai_analyses(advance_id,structure_score,content_score,form_score,
           originality_score,overall_score,grade,executive_summary,model_used,processing_ms,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (adv_id,
         result["scores"]["structure"], result["scores"]["content"],
         result["scores"]["form"],      result["scores"]["originality"],
         result["scores"]["overall"],   result["grade"],
         result["executiveSummary"],    result["modelUsed"],
         result["processingMs"],        now())
    )
    for fi in result["findings"]:
        execute(
            """INSERT INTO findings(analysis_id,type,section_ref,page_ref,severity,description,
               correction_steps,example_improvement,recommendation,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (aid, fi["type"], fi["section_ref"], fi.get("page_ref"), fi["severity"],
             fi["description"], fi["correction_steps"], fi["example_improvement"],
             fi["recommendation"], now())
        )

    execute(
        "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
        ("Agente evaluador IA", adv_id, "Finalizado",
         f"Cumplimiento: {result['scores']['overall']}%", now(), now())
    )

    run_similarity_check(adv_id, text, student["program_id"])
    execute(
        "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
        ("Agente similitud/plagio", adv_id, "Finalizado", "Análisis completado", now(), now())
    )

    validate_citations(adv_id, text, online=False)
    execute(
        "INSERT INTO agent_jobs(name,advance_id,status,result,created_at,finished_at) VALUES (?,?,?,?,?,?)",
        ("Agente validador de citas", adv_id, "Finalizado", "Citas procesadas", now(), now())
    )

    # ── Revisión humana para los avances ya revisados ───────────────────────
    if av["human_grade"] is not None:
        execute(
            """INSERT INTO reviews(advance_id,reviewer_id,final_grade,human_comment,status,reviewed_at,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (adv_id, advisor["id"], av["human_grade"], av["comment"],
             av["status_final"], now(), now())
        )
        # Marcar algunos hallazgos como aceptados
        findings_ids = query("SELECT id FROM findings WHERE analysis_id=?", (aid,))
        for i, frow in enumerate(findings_ids):
            action = "Aceptado" if i % 2 == 0 else "Modificado"
            execute(
                "UPDATE findings SET human_action=?, human_comment=? WHERE id=?",
                (action, av["comment"] if action == "Modificado" else None, frow["id"])
            )

    execute("UPDATE advances SET status=? WHERE id=?", (av["status_final"], adv_id))
    created.append((adv_id, av["titulo"], result["grade"], av["status_final"]))
    time.sleep(0.1)

print("\nAvances creados:")
for adv_id, titulo, grade, status in created:
    print(f"  ID {adv_id} | {titulo[:45]:45s} | nota {grade:.1f}/20 | {status}")

print(f"\nSistema listo para defensa. Abre http://localhost:8501")

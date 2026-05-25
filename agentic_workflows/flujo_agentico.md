# Flujo agéntico del sistema

Este proyecto implementa un comportamiento de IA agéntica mediante un pipeline de agentes:

1. Agente extractor: lee PDF, DOCX o TXT y obtiene texto limpio.
2. Agente estructural: identifica secciones presentes y faltantes frente al patrón institucional.
3. Agente evaluador académico: califica estructura, contenido, forma y originalidad.
4. Agente de citas: extrae referencias y valida si poseen DOI o requieren revisión.
5. Agente de similitud: compara el avance con otros documentos del programa.
6. Agente revisor: genera hallazgos accionables con severidad, corrección y ejemplo.
7. Humano en el ciclo: el asesor acepta, modifica o rechaza cada hallazgo.
8. Aprendizaje futuro: las correcciones humanas quedan almacenadas para fine-tuning.

La versión entregada funciona sin API externa mediante reglas académicas locales. 
Opcionalmente puede conectarse a OpenAI, CrossRef, ORCID o Copyleaks agregando credenciales.

# Pipeline de Fine-Tuning — ThesisReview AI

## Propósito

El sistema almacena, en cada revisión humana, las acciones del asesor sobre los hallazgos generados por la IA (`Aceptado`, `Modificado`, `Rechazado`) junto con un comentario opcional de corrección. Este feedback constituye el conjunto de datos de entrenamiento supervisado que permitirá ajustar el motor de evaluación en iteraciones futuras.

---

## Datos almacenados

### Tabla `findings`

| Campo             | Tipo   | Descripción                                               |
|-------------------|--------|-----------------------------------------------------------|
| `description`     | TEXT   | Hallazgo generado por la IA                               |
| `correction_steps`| TEXT   | Pasos de corrección sugeridos por la IA                   |
| `human_action`    | TEXT   | Veredicto del asesor: `Aceptado`, `Modificado`, `Rechazado` |
| `human_comment`   | TEXT   | Corrección o justificación del asesor (texto libre)       |
| `type`            | TEXT   | Categoría del hallazgo: Estructura, Contenido, Forma, etc.|
| `severity`        | TEXT   | Criticidad: Crítico, Mayor, Menor, Sugerencia             |

### Tabla `ai_analyses`

Contiene las dimensiones de puntuación (`structure_score`, `content_score`, `form_score`, `originality_score`) y la nota final estimada, que pueden compararse con la nota final asignada por el asesor en `reviews.final_grade`.

---

## Paso 1 — Exportar datos de entrenamiento

Ejecuta el siguiente script Python para exportar los pares prompt/completion en formato JSONL (compatible con OpenAI fine-tuning y Hugging Face):

```python
import sqlite3, json, os

DB_PATH = "data/thesis_review.db"
OUTPUT  = "data/fine_tuning_dataset.jsonl"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT
        f.description       AS ai_finding,
        f.correction_steps  AS ai_correction,
        f.type              AS finding_type,
        f.severity          AS severity,
        f.human_action      AS label,
        f.human_comment     AS human_correction
    FROM findings f
    WHERE f.human_action IN ('Aceptado', 'Modificado', 'Rechazado')
      AND f.human_action IS NOT NULL
""").fetchall()

with open(OUTPUT, "w", encoding="utf-8") as fout:
    for r in rows:
        system_prompt = (
            "Eres un evaluador académico de avances de tesis universitarias. "
            "Tu tarea es analizar hallazgos de revisión y determinar si son correctos, "
            "incorrectos o necesitan modificación, según el criterio del asesor humano."
        )
        user_msg = (
            f"Hallazgo IA ({r['finding_type']} — {r['severity']}):\n"
            f"{r['ai_finding']}\n\n"
            f"Corrección IA propuesta:\n{r['ai_correction']}"
        )
        assistant_msg = r["human_correction"] if r["label"] == "Modificado" else r["label"]
        record = {
            "messages": [
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_msg},
                {"role": "assistant","content": assistant_msg or r["label"]},
            ]
        }
        fout.write(json.dumps(record, ensure_ascii=False) + "\n")

conn.close()
print(f"Dataset exportado: {OUTPUT} ({len(rows)} registros)")
```

---

## Paso 2 — Filtrado de calidad

Se recomienda filtrar el dataset antes de fine-tuning:

```python
import json

MIN_COMMENT_LENGTH = 20  # caracteres mínimos en el comentario del asesor

with open("data/fine_tuning_dataset.jsonl", "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

# Solo incluir registros con feedback no trivial
quality = [
    r for r in records
    if len(r["messages"][-1]["content"]) >= MIN_COMMENT_LENGTH
]

with open("data/fine_tuning_quality.jsonl", "w", encoding="utf-8") as f:
    for r in quality:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Registros de calidad: {len(quality)} / {len(records)}")
```

---

## Paso 3 — Fine-tuning con OpenAI API

```python
from openai import OpenAI

client = OpenAI()

# 1. Subir el dataset
with open("data/fine_tuning_quality.jsonl", "rb") as f:
    response = client.files.create(file=f, purpose="fine-tune")
    file_id = response.id
    print("Archivo subido:", file_id)

# 2. Crear el job de fine-tuning
job = client.fine_tuning.jobs.create(
    training_file=file_id,
    model="gpt-4o-mini-2024-07-18",
    hyperparameters={"n_epochs": 3}
)
print("Job creado:", job.id)

# 3. Monitorear (ejecutar periódicamente)
status = client.fine_tuning.jobs.retrieve(job.id)
print("Estado:", status.status, "| Modelo:", status.fine_tuned_model)
```

---

## Paso 4 — Fine-tuning local con Hugging Face (alternativa sin costo)

Para entornos sin acceso a OpenAI, se puede usar `transformers` con un modelo liviano:

```bash
pip install transformers datasets accelerate trl
```

```python
from datasets import load_dataset
from trl import SFTTrainer
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments

model_name = "microsoft/phi-2"   # ~2.7B parámetros, corre en CPU/GPU modesto
tokenizer  = AutoTokenizer.from_pretrained(model_name)
model      = AutoModelForCausalLM.from_pretrained(model_name)

dataset = load_dataset("json", data_files="data/fine_tuning_quality.jsonl", split="train")

training_args = TrainingArguments(
    output_dir="./model_finetuned",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    save_steps=50,
    logging_steps=10,
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=training_args,
)
trainer.train()
model.save_pretrained("./model_finetuned")
```

---

## Métricas de éxito esperadas

| Métrica                         | Objetivo sugerido |
|---------------------------------|-------------------|
| % hallazgos aceptados por asesor| > 70%             |
| Reducción de hallazgos rechazados| -30% tras 1 ciclo |
| Coherencia calificación IA vs asesor | Δ < 1.5 pts  |

---

## Consideraciones éticas y de privacidad

- Los datos exportados contienen texto de documentos académicos de estudiantes. No publicar ni compartir sin consentimiento.
- En producción, aplicar anonimización antes de subir a APIs externas.
- Conservar siempre al asesor humano como árbitro final; el fine-tuning mejora sugerencias, no reemplaza juicio experto.

---

## Estado actual del sistema

| Componente                        | Estado      |
|-----------------------------------|-------------|
| Almacenamiento de feedback humano | Implementado (`findings.human_action/human_comment`) |
| Export script JSONL               | Documentado (este archivo) |
| Fine-tuning OpenAI                | Configurable (requiere `OPENAI_API_KEY`) |
| Fine-tuning local (HuggingFace)   | Documentado, requiere GPU/CPU potente |
| Integración automática al pipeline| Pendiente (roadmap v2) |

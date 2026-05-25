# ThesisReview AI Agent

Sistema académico para gestión, revisión y evaluación automatizada de avances de tesis universitarias. Implementado como prototipo interactivo con interfaz web, API REST y aplicación móvil.

---

## Arquitectura del sistema

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENTE WEB                               │
│              Streamlit (Python) · Puerto 8501                    │
│   Dashboard · Cargar avance · Revisión IA · Revisión humana     │
│   Plantillas · Usuarios/ORCID · Reportes · Auditoría            │
└──────────────────────┬───────────────────────────────────────────┘
                       │ lee/escribe
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    BASE DE DATOS                                  │
│                 SQLite · data/thesis_review.db                   │
│  users · programs · templates · advances · ai_analyses          │
│  findings · reviews · plagiarism_results · citations             │
│  notifications · audit_logs · agent_jobs                        │
└──────────────────────┬───────────────────────────────────────────┘
                       │ lee (solo lectura)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                      API REST                                     │
│              FastAPI · Puerto 8000 · /docs (Swagger)             │
│   /api/auth/login · /api/students · /api/student/:id/dashboard  │
│   /api/advance/:id/findings · /api/advance/:id/similarity       │
└──────────────────────┬───────────────────────────────────────────┘
                       │ HTTP
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    APP MÓVIL                                      │
│               React Native + Expo SDK 54                         │
│   Inicio · Avances · Hallazgos · Historial · Reportes           │
│   Solo lectura · Fallback a datos demo si API no disponible     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Stack tecnológico

| Capa           | Tecnología                             |
|----------------|----------------------------------------|
| Web UI         | Streamlit 1.40+                        |
| API REST       | FastAPI 0.115+ + Uvicorn               |
| Base de datos  | SQLite (migrable a PostgreSQL)         |
| Motor IA       | Local (reglas + heurísticas académicas)|
| PDF            | ReportLab 4.2+                         |
| Extracción doc.| PyPDF2 + python-docx                   |
| Similitud      | Similitud coseno sobre TF local        |
| Citas          | Parser local + CrossRef (opcional)     |
| Autenticación  | bcrypt + control de acceso por rol     |
| Visualización  | Plotly Express                         |
| App móvil      | React Native + Expo SDK 54 (TypeScript)|

---

## Roles y permisos

| Rol         | Permisos                                                                      |
|-------------|-------------------------------------------------------------------------------|
| ADMIN       | Acceso total a todas las funciones y configuración                            |
| COORDINATOR | Gestión de usuarios, plantillas, reportes, auditoría; no accede a configuración |
| ADVISOR     | Cargar avances, revisión IA y humana, estadísticas, reportes                  |
| STUDENT     | Dashboard propio, ver sus revisiones IA, acceso a la app móvil               |

---

## Módulos del sistema

### Backend (Python)
| Módulo                       | Descripción                                                  |
|------------------------------|--------------------------------------------------------------|
| `modules/database.py`        | Esquema SQLite, helpers CRUD, auditoría, hash de contraseñas |
| `modules/ai_engine.py`       | Motor IA local: detección de secciones, puntuación 4 dims.  |
| `modules/document_processing.py` | Extracción de texto PDF/DOCX/TXT, análisis de estilo  |
| `modules/plagiarism.py`      | Similitud coseno interna por programa                        |
| `modules/citations.py`       | Validación de referencias APA + integración CrossRef         |
| `modules/reports.py`         | Generación PDF: acta individual, comparativo, gestión        |

### Web UI (`app.py`)
Interfaz Streamlit con control de acceso por rol. 12 secciones funcionales.

### API REST (`api_server.py`)
FastAPI con 9 endpoints documentados en Swagger. Incluye autenticación demo.

### App móvil (`mobile/`)
Expo SDK 54. Pantallas: Inicio, Avances, Hallazgos, Historial, Reportes.

---

## Pipeline de análisis IA

El motor local evalúa cuatro dimensiones con los pesos de la rúbrica institucional:

| Dimensión        | Peso | Criterios                                               |
|------------------|------|---------------------------------------------------------|
| Estructura       | 30%  | Presencia de secciones obligatorias vs. documento patrón|
| Contenido        | 40%  | Longitud, estilo académico, coherencia, citas           |
| Forma            | 20%  | Formato APA, extensión, uso de signos de puntuación     |
| Calidad interna  | 10%  | Repetición de oraciones, consistencia argumentativa     |

La nota final se calcula: `nota = (puntuación_global / 100) × nota_máxima (20)`

Cada análisis genera hallazgos accionables con severidad (Crítico / Mayor / Menor / Sugerencia), pasos de corrección y ejemplos de mejora.

---

## Variables de entorno

Copia `.env.example` como `.env`:

```
OPENAI_API_KEY=          # Opcional: habilita GPT-4o-mini como motor alternativo
OPENAI_MODEL=gpt-4o-mini
CROSSREF_ENABLED=false   # true → valida DOIs en tiempo real
ORCID_ENABLED=false      # true → verifica perfiles ORCID reales
COPYLEAKS_API_KEY=       # Opcional: detección de plagio externo
APP_SECRET=tesis-review-demo-secret
MAX_FILE_MB=20
DB_PATH=data/thesis_review.db
```

Si no se define ninguna variable, el sistema funciona completamente en modo local sin dependencias externas.

---

## Guía de instalación local

### Requisitos
- Python 3.11 o 3.12 (recomendado)
- Node.js 18+ y npm (solo para la app móvil)

### Paso 1 — Entorno Python

```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Paso 2 — Variables de entorno (opcional)

```bash
copy .env.example .env    # Windows
cp .env.example .env      # Linux/macOS
# Editar .env si se quieren activar integraciones externas
```

### Paso 3 — Interfaz web

```bash
streamlit run app.py
# Abre http://localhost:8501
```

### Paso 4 — API REST (en otra terminal)

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
# Swagger en http://localhost:8000/docs
```

### Paso 5 — App móvil (en otra terminal)

```bash
cd mobile
npm install
npx expo start -c
# Escanear QR con la app Expo Go en Android/iOS
```

Para conectar la app móvil a la API, obtén la IP local:
- Windows: `ipconfig` → buscar IPv4
- Linux/macOS: `ifconfig` o `ip addr`

Luego en la pestaña API de la app móvil ingresar `http://TU_IP:8000`.

---

## Docker Compose

Levanta la stack completa (web + API) con un solo comando:

```bash
# Primera vez (construye la imagen)
docker compose up --build

# Modo fondo
docker compose up -d

# Ver logs
docker compose logs -f

# Detener
docker compose down
```

Accesos después del arranque:
- Interfaz web: `http://localhost:8501`
- API Swagger: `http://localhost:8000/docs`

Los datos persisten en el volumen Docker `thesis_data`. Para resetear la base de datos:

```bash
docker compose down -v    # elimina también el volumen
docker compose up --build
```

---

## Credenciales demo

Todos usan contraseña `123456`:

| Rol         | Correo                      |
|-------------|------------------------------|
| ADMIN       | admin@tesis.edu              |
| COORDINATOR | coordinador@tesis.edu        |
| ADVISOR     | asesor@tesis.edu             |
| STUDENT     | estudiante@tesis.edu         |

---

## API REST — Endpoints principales

| Método | Ruta                                    | Descripción                       |
|--------|-----------------------------------------|-----------------------------------|
| POST   | `/api/auth/login`                       | Autenticación por email/contraseña|
| GET    | `/api/students`                         | Lista de estudiantes              |
| GET    | `/api/student/{id}/dashboard`           | Resumen del estudiante            |
| GET    | `/api/student/{id}/advances`            | Avances con métricas IA           |
| GET    | `/api/advance/{id}/findings`            | Hallazgos ordenados por severidad |
| GET    | `/api/student/{id}/grade-history`       | Historial de notas                |
| GET    | `/api/advance/{id}/citations`           | Citas bibliográficas              |
| GET    | `/api/advance/{id}/similarity`          | Resultados de similitud           |

Documentación interactiva disponible en `/docs` (Swagger UI) y `/redoc` (ReDoc).

---

## Fine-tuning del modelo IA

El sistema almacena el feedback humano de los asesores (aceptar/modificar/rechazar hallazgos) para entrenar versiones mejoradas del motor de evaluación.

Ver documentación completa en `docs/fine_tuning_pipeline.md`.

---

## Decisiones de arquitectura

### ¿Por qué SQLite y no PostgreSQL?
SQLite elimina la necesidad de configurar un servidor de base de datos, permitiendo la ejecución local sin instalación adicional. La migración a PostgreSQL (con `pgvector` para embeddings) está preparada cambiando el string de conexión y la capa de acceso en `modules/database.py`.

### ¿Por qué motor IA local y no GPT?
El motor local (reglas + heurísticas académicas) no requiere API key, funciona sin internet, no tiene costo por consulta y es determinístico. Si se define `OPENAI_API_KEY` en `.env`, el sistema puede delegar el análisis a GPT-4o-mini como motor alternativo. Esta decisión cumple el requisito de "modo configurable con alternativa demo/local".

### ¿Por qué Streamlit para la interfaz web?
Streamlit permite prototipar rápidamente interfaces de datos en Python sin separar frontend/backend. Para producción se recomienda migrar a FastAPI + React, pero para una defensa académica Streamlit es suficientemente completo y demostrable.

### ¿Por qué Expo para la app móvil?
Expo permite desarrollar y probar apps React Native sin configurar Xcode ni Android Studio. La app funciona en iOS y Android vía Expo Go con un solo QR, lo que facilita la demostración en tiempo real.

### Similitud/plagio interno
Se usa similitud coseno sobre frecuencia de términos (TF) sin dependencias pesadas (no requiere scikit-learn ni pytorch). En producción puede reemplazarse por pgvector + embeddings o por la API de Copyleaks, activables desde `.env`.

---

## Limitaciones conocidas

- El motor local de IA no detecta texto generado por inteligencia artificial (no es Turnitin).
- La similitud interna usa TF-coseno; para detección robusta se requieren embeddings semánticos.
- La autenticación de la API usa tokens demo; en producción implementar JWT con expiración.
- SQLite no soporta concurrencia alta; para múltiples usuarios simultáneos migrar a PostgreSQL.

---

## Estructura de archivos

```
thesis_review_full_agentico_fixed/
├── app.py                    # Interfaz web Streamlit
├── api_server.py             # API REST FastAPI
├── requirements.txt          # Dependencias Python
├── Dockerfile                # Imagen Docker
├── docker-compose.yml        # Stack completa Docker
├── .env.example              # Plantilla de variables de entorno
├── README.md                 # Este archivo
│
├── modules/
│   ├── database.py           # Esquema SQLite + helpers
│   ├── ai_engine.py          # Motor IA académico local
│   ├── document_processing.py# Extracción texto PDF/DOCX/TXT
│   ├── plagiarism.py         # Detección similitud interna
│   ├── citations.py          # Validación referencias APA
│   └── reports.py            # Generación PDFs
│
├── docs/
│   └── fine_tuning_pipeline.md # Documentación fine-tuning
│
├── mobile/                   # App React Native + Expo
│   ├── App.tsx
│   ├── src/screens/
│   ├── src/components/
│   └── package.json
│
├── mobile_app_mock/          # Preview HTML de la app (demostración web)
│   └── index.html
│
├── sample_documents/         # Documentos de prueba
├── agentic_workflows/        # Documentación del flujo agéntico
└── data/                     # Datos en tiempo de ejecución (no versionar)
    ├── thesis_review.db
    ├── uploads/
    └── reports/
```

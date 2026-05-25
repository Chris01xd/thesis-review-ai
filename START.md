# ThesisReview AI — Cómo arrancar el sistema

## 1. Backend (FastAPI)

Desde la raíz del proyecto:

```bash
# Instalar dependencias (una sola vez)
pip install -r requirements.txt

# Arrancar el servidor backend
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

Docs interactivos: http://localhost:8000/docs

## 2. Frontend React

```bash
cd frontend

# Instalar dependencias (una sola vez)
npm install

# Modo desarrollo (con hot-reload)
npm run dev
# → http://localhost:5173

# Build de producción
npm run build
npm run preview
```

## 3. App Móvil (React Native + Expo)

```bash
cd mobile
npm install
npx expo start
```

---

## Cuentas de demostración

| Rol         | Email                     | Contraseña |
|-------------|---------------------------|------------|
| Admin       | admin@tesis.edu           | 123456     |
| Coordinador | coordinador@tesis.edu     | 123456     |
| Asesor      | asesor@tesis.edu          | 123456     |
| Estudiante  | estudiante@tesis.edu      | 123456     |

---

## Estructura del proyecto

```
thesis_review_full_agentico_fixed/
├── api_server.py        ← Backend FastAPI (expandido v3.0)
├── modules/             ← Lógica de negocio (IA, DB, reportes)
├── frontend/            ← Nuevo frontend React + Vite + Tailwind
│   ├── src/
│   │   ├── pages/       ← 13 páginas por rol
│   │   ├── components/  ← UI components (shadcn style)
│   │   ├── api/         ← Cliente API con axios
│   │   ├── contexts/    ← AuthContext
│   │   └── types/       ← TypeScript types
│   └── dist/            ← Build de producción
├── mobile/              ← App React Native + Expo
└── data/                ← DB SQLite + archivos subidos
```

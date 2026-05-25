# ThesisReview Student Mobile conectado a API

Esta app móvil de solo lectura puede conectarse a la base real mediante FastAPI.

## 1. Ejecuta la API en la laptop

Desde la raíz del proyecto:

```cmd
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

Abre:

```text
http://localhost:8000/docs
```

## 2. Obtén tu IP local

```cmd
ipconfig
```

Busca IPv4. Ejemplo:

```text
192.168.1.35
```

## 3. Ejecuta Expo

```cmd
npm install
npx expo start -c
```

## 4. En la app

Entra a la pestaña `API`, coloca:

```text
http://TU_IP:8000
```

y presiona `Conectar / Actualizar`.

No uses `localhost` desde el celular.


## Selector de alumnos

Desde la pestaña `API` puedes seleccionar qué alumno consultar.
La app carga el listado real desde `/api/students`.

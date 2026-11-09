# CodeMentor IA

**CodeMentor IA** es una aplicación web educativa desarrollada con Python y Flask que utiliza inteligencia artificial para ayudar a aprender y practicar programación en Python.

El proyecto combina un tutor conversacional, generación de ejercicios personalizados, corrección de código y seguimiento del progreso del estudiante.

## Funcionalidades

### Tutor IA

- Chat con un tutor de programación en español.
- Explicaciones de conceptos de Python.
- Conversaciones persistentes en SQLite.
- Historial de conversaciones.
- Eliminación de conversaciones con confirmación.
- Respuestas con formato Markdown, resaltado de sintaxis y opción para copiar código.

### Ejercicios prácticos

- Generación de ejercicios por tema y dificultad.
- Temas: variables, condicionales, bucles, funciones, listas y diccionarios.
- Niveles básico, intermedio y avanzado.
- Corrección de soluciones mediante inteligencia artificial.
- Comentarios sobre aciertos, errores y posibles mejoras.
- Opción de solicitar una solución completa explicada después de realizar un intento.

### Seguimiento del progreso

- Estadísticas de ejercicios generados y completados.
- Registro de intentos.
- Historial de actividad.
- Recuperación de ejercicios anteriores.

### Interfaz

- Diseño adaptable a distintos tamaños de pantalla.
- Modo claro y oscuro.
- Navegación entre tutor, ejercicios y progreso.

## Tecnologías

- **Python:** lógica del servidor.
- **Flask:** aplicación web y API REST.
- **SQLite:** almacenamiento de conversaciones, ejercicios e intentos.
- **OpenAI API:** generación de explicaciones, ejercicios y correcciones.
- **HTML, CSS y JavaScript:** interfaz de usuario.
- **Marked, DOMPurify y Highlight.js:** representación segura de Markdown y resaltado de código.

## Requisitos

- Python 3.11 o superior, con una versión compatible con las dependencias.
- Git.
- Una clave de API de OpenAI.
- Conexión a Internet para las funcionalidades de inteligencia artificial.

## Instalación

1. Clonar el repositorio:

```bash
git clone URL_DEL_REPOSITORIO
cd CodeMentorIA
```

2. Crear un entorno virtual:

```bash
python -m venv venv
```

3. Activar el entorno virtual.

En Windows con Git Bash:

```bash
source venv/Scripts/activate
```

En Windows con PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

En Linux o macOS:

```bash
source venv/bin/activate
```

4. Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

5. Crear el archivo `.env` a partir de `.env.example` e introducir la clave personal de OpenAI:

```env
OPENAI_API_KEY=tu_clave_real
```

6. Iniciar la aplicación:

```bash
python app.py
```

7. Abrir en el navegador:

http://127.0.0.1:8081

La base de datos SQLite se crea automáticamente cuando se inicia la aplicación.

## Pruebas automatizadas

Para ejecutar las pruebas:

```bash
python -m unittest discover -s tests -v
```

Las pruebas utilizan una base de datos temporal y simulan las respuestas de OpenAI, por lo que no realizan llamadas reales a la API.

## Seguridad y limitaciones

- La clave de OpenAI se configura mediante variables de entorno y no debe publicarse.
- Las soluciones del estudiante se analizan como texto; la aplicación no ejecuta el código enviado.
- Las correcciones y soluciones generadas por IA pueden contener errores y no sustituyen pruebas automáticas de ejecución.
- El proyecto está pensado para aprendizaje y uso local. No incluye autenticación ni aislamiento de datos entre usuarios.
- El servidor de desarrollo de Flask no debe exponerse directamente a Internet.

## Estructura del proyecto

```text
CodeMentorIA/
├── app.py
├── ia.py
├── database.py
├── prompts.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── tests/
│   └── test_app.py
└── instance/
    └── codementor.db
```

Los archivos `.env`, `venv/` y `instance/codementor.db` son locales y no deben incluirse en el repositorio.

## Posibles mejoras futuras

- Autenticación y cuentas de usuario.
- Tests automáticos para comprobar el código del estudiante.
- Más lenguajes de programación.
- Ejercicios organizados por itinerarios de aprendizaje.
- Despliegue en un servidor de producción.

## Estado del proyecto

Proyecto educativo en desarrollo, con pruebas automatizadas para sus principales operaciones.

## Licencia

Pendiente de definir.

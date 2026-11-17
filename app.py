
from flask import (
    Flask,
    render_template,
    request,
    jsonify, redirect, url_for, session, flash, g
)

from ia import (
    preguntar_tutor,
    generar_ejercicio,
    corregir_ejercicio,
    obtener_solucion_completa
)

from database import (
    crear_usuario, obtener_usuario_por_email, obtener_usuario_por_id,
    inicializar_db,
    crear_conversacion,
    existe_conversacion,
    listar_conversaciones,
    obtener_conversacion,
    eliminar_conversacion,
    obtener_mensajes,
    obtener_contexto,
    guardar_intercambio,
    guardar_ejercicio,
    obtener_ejercicio,
    listar_ejercicios,
    guardar_intento,
    obtener_intentos,
    obtener_estadisticas,
    obtener_actividad_reciente
)


import os
import re
import sqlite3
from functools import wraps
from secrets import token_urlsafe
from werkzeug.security import generate_password_hash, check_password_hash
from flask import abort
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    # Solo desarrollo local: en producción debe definirse SECRET_KEY en .env.
    if os.environ.get("PYTHONANYWHERE_DOMAIN"):
        raise RuntimeError("Configura SECRET_KEY en el archivo .env")
    app.secret_key = token_urlsafe(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=not app.debug and os.environ.get("COOKIE_SECURE", "1") == "1")

@app.before_request
def cargar_usuario():
    g.usuario = obtener_usuario_por_id(session["usuario_id"]) if session.get("usuario_id") else None
    if session.get("usuario_id") and g.usuario is None:
        session.clear()
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
            abort(403)
        # Same-origin JSON requests and HTML forms require a CSRF token.
        token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not session.get("csrf_token") or token != session["csrf_token"]:
            abort(400, description="Token de seguridad no válido. Recarga la página.")


def login_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if g.usuario is None:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Inicia sesión para continuar."}), 401
            return redirect(url_for("acceso"))
        return func(*args, **kwargs)
    return wrapped


@app.route("/acceso", methods=["GET", "POST"])
def acceso():
    if g.usuario:
        return redirect(url_for("inicio"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        clave = request.form.get("password", "")
        usuario = obtener_usuario_por_email(email)
        if usuario and check_password_hash(usuario["password_hash"], clave):
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["csrf_token"] = token_urlsafe(32)
            return redirect(url_for("inicio"))
        flash("Correo o contraseña incorrectos.", "error")
    return render_template("auth.html", registro=False, csrf_token=session.setdefault("csrf_token", token_urlsafe(32)))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if g.usuario:
        return redirect(url_for("inicio"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        clave = request.form.get("password", "")
        confirmacion = request.form.get("confirm_password", "")
        if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            flash("Introduce un correo electrónico válido.", "error")
        elif len(clave) < 12 or len(clave) > 128:
            flash("La contraseña debe tener entre 12 y 128 caracteres.", "error")
        elif clave != confirmacion:
            flash("Las contraseñas no coinciden.", "error")
        else:
            try:
                usuario_id = crear_usuario(email, generate_password_hash(clave))
            except sqlite3.IntegrityError:
                flash("Ya existe una cuenta con ese correo.", "error")
            else:
                session.clear()
                session["usuario_id"] = usuario_id
                session["csrf_token"] = token_urlsafe(32)
                return redirect(url_for("inicio"))
    return render_template("auth.html", registro=True, csrf_token=session.setdefault("csrf_token", token_urlsafe(32)))


@app.route("/salir", methods=["POST"])
@login_required
def salir():
    session.clear()
    return redirect(url_for("acceso"))


inicializar_db()


TEMAS_VALIDOS = {
    "variables",
    "condicionales",
    "bucles",
    "funciones",
    "listas",
    "diccionarios"
}

NIVELES_VALIDOS = {
    "basico",
    "intermedio",
    "avanzado"
}


def leer_json():
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else None


# ==========================================
# PÁGINA PRINCIPAL
# ==========================================

@app.route("/")
@login_required
def inicio():
    return render_template("index.html", usuario=g.usuario, csrf_token=session["csrf_token"])


# ==========================================
# CONVERSACIONES
# ==========================================

@app.route("/api/conversaciones", methods=["GET"])
@login_required
def api_listar_conversaciones():
    return jsonify(listar_conversaciones(g.usuario["id"]))


@app.route("/api/conversaciones", methods=["POST"])
@login_required
def api_crear_conversacion():
    conversacion_id = crear_conversacion(g.usuario["id"])

    return jsonify({
        "id": conversacion_id,
        "titulo": "Nueva conversación"
    }), 201


@app.route(
    "/api/conversaciones/<int:conversacion_id>",
    methods=["GET"]
)
@login_required
def api_obtener_conversacion(conversacion_id):
    conversacion = obtener_conversacion(conversacion_id, g.usuario["id"])

    if conversacion is None:
        return jsonify({
            "error": "Conversación no encontrada."
        }), 404

    return jsonify({
        "conversacion": conversacion,
        "mensajes": obtener_mensajes(conversacion_id, g.usuario["id"])
    })


# ==========================================
# ELIMINAR CONVERSACIÓN
# ==========================================

@app.route(
    "/api/conversaciones/<int:conversacion_id>",
    methods=["DELETE"]
)
@login_required
def api_eliminar_conversacion(conversacion_id):
    eliminada = eliminar_conversacion(conversacion_id, g.usuario["id"])

    if not eliminada:
        return jsonify({
            "error": "Conversación no encontrada."
        }), 404

    return jsonify({
        "mensaje": "Conversación eliminada correctamente.",
        "conversacion_id": conversacion_id
    })


# ==========================================
# CHAT CON MEMORIA
# ==========================================

@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    datos = leer_json()

    if datos is None:
        return jsonify({
            "error": "Debes enviar un JSON válido."
        }), 400

    pregunta = datos.get("mensaje")
    conversacion_id = datos.get("conversacion_id")

    if not isinstance(pregunta, str) or not pregunta.strip():
        return jsonify({
            "error": "La pregunta no puede estar vacía."
        }), 400

    pregunta = pregunta.strip()

    if len(pregunta) > 10000:
        return jsonify({
            "error": "La pregunta es demasiado larga."
        }), 400

    if type(conversacion_id) is not int:
        return jsonify({
            "error": "Identificador de conversación no válido."
        }), 400

    if not existe_conversacion(conversacion_id, g.usuario["id"]):
        return jsonify({
            "error": "Conversación no encontrada."
        }), 404

    try:
        contexto = obtener_contexto(
            conversacion_id, g.usuario["id"],
            limite=9
        )

        contexto.append({
            "role": "user",
            "content": pregunta
        })

        respuesta = preguntar_tutor(contexto)

        guardar_intercambio(
            conversacion_id,
            pregunta,
            respuesta, g.usuario["id"]
        )

        return jsonify({
            "respuesta": respuesta,
            "conversacion_id": conversacion_id
        })

    except Exception:
        app.logger.exception("Error en el chat")

        return jsonify({
            "error": "No se pudo obtener la respuesta de la IA."
        }), 502


# ==========================================
# GENERAR EJERCICIO
# ==========================================

@app.route(
    "/api/ejercicios/generar",
    methods=["POST"]
)
@login_required
def api_generar_ejercicio():
    datos = leer_json()

    if datos is None:
        return jsonify({
            "error": "Debes enviar un JSON válido."
        }), 400

    tema = datos.get("tema")
    nivel = datos.get("nivel")

    if not isinstance(tema, str) or tema not in TEMAS_VALIDOS:
        return jsonify({
            "error": "Tema no válido."
        }), 400

    if not isinstance(nivel, str) or nivel not in NIVELES_VALIDOS:
        return jsonify({
            "error": "Nivel no válido."
        }), 400

    try:
        ejercicio = generar_ejercicio(tema, nivel)

        ejercicio_id = guardar_ejercicio(
            tema,
            nivel,
            ejercicio, g.usuario["id"]
        )

        return jsonify({
            "ejercicio": obtener_ejercicio(ejercicio_id, g.usuario["id"])
        }), 201

    except Exception:
        app.logger.exception("Error generando ejercicio")

        return jsonify({
            "error": "No se pudo generar el ejercicio."
        }), 502


# ==========================================
# RECUPERAR EJERCICIOS
# ==========================================

@app.route("/api/ejercicios", methods=["GET"])
@login_required
def api_listar_ejercicios():
    return jsonify(listar_ejercicios(g.usuario["id"]))


@app.route(
    "/api/ejercicios/<int:ejercicio_id>",
    methods=["GET"]
)
@login_required
def api_obtener_ejercicio(ejercicio_id):
    ejercicio = obtener_ejercicio(ejercicio_id, g.usuario["id"])

    if ejercicio is None:
        return jsonify({
            "error": "Ejercicio no encontrado."
        }), 404

    return jsonify({
        "ejercicio": ejercicio,
        "intentos": obtener_intentos(ejercicio_id, g.usuario["id"])
    })


# ==========================================
# CORREGIR EJERCICIO
# ==========================================

@app.route(
    "/api/ejercicios/corregir",
    methods=["POST"]
)
@login_required
def api_corregir_ejercicio():
    datos = leer_json()

    if datos is None:
        return jsonify({
            "error": "Debes enviar un JSON válido."
        }), 400

    ejercicio_id = datos.get("ejercicio_id")
    codigo = datos.get("codigo")

    if type(ejercicio_id) is not int:
        return jsonify({
            "error": "Identificador de ejercicio no válido."
        }), 400

    ejercicio = obtener_ejercicio(ejercicio_id, g.usuario["id"])

    if ejercicio is None:
        return jsonify({
            "error": "Ejercicio no encontrado."
        }), 404

    if not isinstance(codigo, str) or not codigo.strip():
        return jsonify({
            "error": "Escribe tu solución antes de corregir."
        }), 400

    if len(codigo) > 20000:
        return jsonify({
            "error": "El código es demasiado largo."
        }), 400

    try:
        correccion = corregir_ejercicio(
            ejercicio={
                "titulo": ejercicio["titulo"],
                "enunciado": ejercicio["enunciado"],
                "requisitos": ejercicio["requisitos"]
            },
            codigo=codigo
        )

        intento_id = guardar_intento(
            ejercicio_id,
            codigo,
            correccion, g.usuario["id"]
        )

        return jsonify({
            "intento_id": intento_id,
            "correccion": correccion
        })

    except Exception:
        app.logger.exception("Error corrigiendo ejercicio")

        return jsonify({
            "error": "No se pudo corregir el ejercicio."
        }), 502


# ==========================================
# MOSTRAR SOLUCIÓN COMPLETA
# ==========================================

@app.route(
    "/api/ejercicios/<int:ejercicio_id>/solucion",
    methods=["POST"]
)
@login_required
def api_solucion_completa(ejercicio_id):
    ejercicio = obtener_ejercicio(ejercicio_id, g.usuario["id"])

    if ejercicio is None:
        return jsonify({
            "error": "Ejercicio no encontrado."
        }), 404

    # Solo permitimos solicitar la solución
    # después de haber corregido un intento.
    intentos = obtener_intentos(ejercicio_id, g.usuario["id"])

    if not intentos:
        return jsonify({
            "error": (
                "Primero debes enviar una solución "
                "para que CodeMentor la corrija."
            )
        }), 400

    try:
        solucion = obtener_solucion_completa(ejercicio)

        return jsonify({
            "ejercicio_id": ejercicio_id,
            "solucion": solucion
        })

    except Exception:
        app.logger.exception(
            "Error generando solución completa"
        )

        return jsonify({
            "error": (
                "No se pudo generar la solución completa. "
                "Inténtalo de nuevo."
            )
        }), 502


# ==========================================
# PROGRESO
# ==========================================

@app.route("/api/progreso", methods=["GET"])
@login_required
def api_progreso():
    return jsonify({
        "estadisticas": obtener_estadisticas(g.usuario["id"]),
        "actividad": obtener_actividad_reciente(g.usuario["id"])
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8081,
        debug=True
    )

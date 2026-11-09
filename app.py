
from flask import (
    Flask,
    render_template,
    request,
    jsonify
)

from ia import (
    preguntar_tutor,
    generar_ejercicio,
    corregir_ejercicio,
    obtener_solucion_completa
)

from database import (
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


app = Flask(__name__)

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
def inicio():
    return render_template("index.html")


# ==========================================
# CONVERSACIONES
# ==========================================

@app.route("/api/conversaciones", methods=["GET"])
def api_listar_conversaciones():
    return jsonify(listar_conversaciones())


@app.route("/api/conversaciones", methods=["POST"])
def api_crear_conversacion():
    conversacion_id = crear_conversacion()

    return jsonify({
        "id": conversacion_id,
        "titulo": "Nueva conversación"
    }), 201


@app.route(
    "/api/conversaciones/<int:conversacion_id>",
    methods=["GET"]
)
def api_obtener_conversacion(conversacion_id):
    conversacion = obtener_conversacion(conversacion_id)

    if conversacion is None:
        return jsonify({
            "error": "Conversación no encontrada."
        }), 404

    return jsonify({
        "conversacion": conversacion,
        "mensajes": obtener_mensajes(conversacion_id)
    })


# ==========================================
# ELIMINAR CONVERSACIÓN
# ==========================================

@app.route(
    "/api/conversaciones/<int:conversacion_id>",
    methods=["DELETE"]
)
def api_eliminar_conversacion(conversacion_id):
    eliminada = eliminar_conversacion(conversacion_id)

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

    if not existe_conversacion(conversacion_id):
        return jsonify({
            "error": "Conversación no encontrada."
        }), 404

    try:
        contexto = obtener_contexto(
            conversacion_id,
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
            respuesta
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
            ejercicio
        )

        return jsonify({
            "ejercicio": obtener_ejercicio(ejercicio_id)
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
def api_listar_ejercicios():
    return jsonify(listar_ejercicios())


@app.route(
    "/api/ejercicios/<int:ejercicio_id>",
    methods=["GET"]
)
def api_obtener_ejercicio(ejercicio_id):
    ejercicio = obtener_ejercicio(ejercicio_id)

    if ejercicio is None:
        return jsonify({
            "error": "Ejercicio no encontrado."
        }), 404

    return jsonify({
        "ejercicio": ejercicio,
        "intentos": obtener_intentos(ejercicio_id)
    })


# ==========================================
# CORREGIR EJERCICIO
# ==========================================

@app.route(
    "/api/ejercicios/corregir",
    methods=["POST"]
)
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

    ejercicio = obtener_ejercicio(ejercicio_id)

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
            correccion
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
def api_solucion_completa(ejercicio_id):
    ejercicio = obtener_ejercicio(ejercicio_id)

    if ejercicio is None:
        return jsonify({
            "error": "Ejercicio no encontrado."
        }), 404

    # Solo permitimos solicitar la solución
    # después de haber corregido un intento.
    intentos = obtener_intentos(ejercicio_id)

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
def api_progreso():
    return jsonify({
        "estadisticas": obtener_estadisticas(),
        "actividad": obtener_actividad_reciente()
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8081,
        debug=True
    )

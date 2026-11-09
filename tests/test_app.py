import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from app import app


EJERCICIO_FALSO = {
    "titulo": "Sumar dos números",
    "enunciado": "Crea una función que sume dos números.",
    "requisitos": [
        "Utiliza una función",
        "Devuelve el resultado"
    ],
    "pista": "Utiliza la palabra clave return."
}

CORRECCION_FALSA = {
    "estado": "mejorar",
    "resumen": "La solución necesita mejoras.",
    "aciertos": ["Has definido una función."],
    "mejoras": ["Debes devolver el resultado."],
    "sugerencia": "Revisa el uso de return."
}


class PruebasCodeMentor(unittest.TestCase):

    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.ruta_original = database.DATABASE

        database.DATABASE = (
            Path(self.directorio.name) / "pruebas.db"
        )

        database.inicializar_db()

        app.config["TESTING"] = True
        self.cliente = app.test_client()

    def tearDown(self):
        database.DATABASE = self.ruta_original
        self.directorio.cleanup()

    def crear_conversacion(self):
        respuesta = self.cliente.post(
            "/api/conversaciones"
        )

        self.assertEqual(respuesta.status_code, 201)

        return respuesta.get_json()["id"]

    def crear_ejercicio(self):
        with patch(
            "app.generar_ejercicio",
            return_value=EJERCICIO_FALSO
        ):
            respuesta = self.cliente.post(
                "/api/ejercicios/generar",
                json={
                    "tema": "funciones",
                    "nivel": "basico"
                }
            )

        self.assertEqual(respuesta.status_code, 201)

        return respuesta.get_json()["ejercicio"]["id"]

    def test_pagina_principal(self):
        respuesta = self.cliente.get("/")

        self.assertEqual(respuesta.status_code, 200)

    def test_crear_conversacion(self):
        conversacion_id = self.crear_conversacion()

        respuesta = self.cliente.get(
            f"/api/conversaciones/{conversacion_id}"
        )

        self.assertEqual(respuesta.status_code, 200)

    def test_listar_conversaciones(self):
        self.crear_conversacion()

        respuesta = self.cliente.get(
            "/api/conversaciones"
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.get_json()), 1)

    def test_eliminar_conversacion(self):
        conversacion_id = self.crear_conversacion()

        respuesta = self.cliente.delete(
            f"/api/conversaciones/{conversacion_id}"
        )

        self.assertEqual(respuesta.status_code, 200)

        consulta = self.cliente.get(
            f"/api/conversaciones/{conversacion_id}"
        )

        self.assertEqual(consulta.status_code, 404)

    def test_eliminar_conversacion_inexistente(self):
        respuesta = self.cliente.delete(
            "/api/conversaciones/999999"
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_chat_rechaza_pregunta_vacia(self):
        conversacion_id = self.crear_conversacion()

        respuesta = self.cliente.post(
            "/api/chat",
            json={
                "mensaje": "   ",
                "conversacion_id": conversacion_id
            }
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_chat_guarda_mensajes(self):
        conversacion_id = self.crear_conversacion()

        with patch(
            "app.preguntar_tutor",
            return_value="Una lista almacena elementos."
        ):
            respuesta = self.cliente.post(
                "/api/chat",
                json={
                    "mensaje": "¿Qué es una lista?",
                    "conversacion_id": conversacion_id
                }
            )

        self.assertEqual(respuesta.status_code, 200)

        consulta = self.cliente.get(
            f"/api/conversaciones/{conversacion_id}"
        )

        mensajes = consulta.get_json()["mensajes"]

        self.assertEqual(len(mensajes), 2)
        self.assertEqual(mensajes[0]["rol"], "user")
        self.assertEqual(mensajes[1]["rol"], "assistant")

    def test_eliminar_conversacion_borra_mensajes(self):
        conversacion_id = self.crear_conversacion()

        database.guardar_mensaje(
            conversacion_id,
            "user",
            "Hola"
        )

        self.cliente.delete(
            f"/api/conversaciones/{conversacion_id}"
        )

        self.assertEqual(
            database.obtener_mensajes(conversacion_id),
            []
        )

    def test_generar_ejercicio(self):
        ejercicio_id = self.crear_ejercicio()

        respuesta = self.cliente.get(
            f"/api/ejercicios/{ejercicio_id}"
        )

        self.assertEqual(respuesta.status_code, 200)

        ejercicio = respuesta.get_json()["ejercicio"]

        self.assertEqual(
            ejercicio["titulo"],
            "Sumar dos números"
        )

    def test_generar_ejercicio_tema_invalido(self):
        respuesta = self.cliente.post(
            "/api/ejercicios/generar",
            json={
                "tema": "tema_inventado",
                "nivel": "basico"
            }
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_corregir_ejercicio(self):
        ejercicio_id = self.crear_ejercicio()

        with patch(
            "app.corregir_ejercicio",
            return_value=CORRECCION_FALSA
        ):
            respuesta = self.cliente.post(
                "/api/ejercicios/corregir",
                json={
                    "ejercicio_id": ejercicio_id,
                    "codigo": (
                        "def sumar(a, b):\n"
                        "    print(a + b)"
                    )
                }
            )

        self.assertEqual(respuesta.status_code, 200)

        consulta = self.cliente.get(
            f"/api/ejercicios/{ejercicio_id}"
        )

        intentos = consulta.get_json()["intentos"]

        self.assertEqual(len(intentos), 1)
        self.assertEqual(
            intentos[0]["estado"],
            "mejorar"
        )

    def test_solucion_requiere_intento(self):
        ejercicio_id = self.crear_ejercicio()

        respuesta = self.cliente.post(
            f"/api/ejercicios/{ejercicio_id}/solucion"
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_solucion_completa(self):
        ejercicio_id = self.crear_ejercicio()

        database.guardar_intento(
            ejercicio_id,
            "print('hola')",
            CORRECCION_FALSA
        )

        solucion_falsa = (
            "```python\n"
            "def sumar(a, b):\n"
            "    return a + b\n"
            "```"
        )

        with patch(
            "app.obtener_solucion_completa",
            return_value=solucion_falsa
        ):
            respuesta = self.cliente.post(
                f"/api/ejercicios/{ejercicio_id}/solucion"
            )

        self.assertEqual(respuesta.status_code, 200)

        self.assertIn(
            "return a + b",
            respuesta.get_json()["solucion"]
        )

    def test_estadisticas(self):
        self.crear_conversacion()
        self.crear_ejercicio()

        respuesta = self.cliente.get("/api/progreso")

        self.assertEqual(respuesta.status_code, 200)

        estadisticas = respuesta.get_json()["estadisticas"]

        self.assertEqual(
            estadisticas["conversaciones"],
            1
        )

        self.assertEqual(
            estadisticas["total_ejercicios"],
            1
        )


if __name__ == "__main__":
    unittest.main()

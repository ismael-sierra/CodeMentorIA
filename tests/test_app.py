import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from app import app
from werkzeug.security import generate_password_hash
from database import crear_usuario


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
        app.config["SESSION_COOKIE_SECURE"] = False
        cliente_real = app.test_client()
        usuario_id = crear_usuario("pruebas@example.com", generate_password_hash("clave-segura-123"))
        self.usuario_id = usuario_id
        with cliente_real.session_transaction() as sesion:
            sesion["usuario_id"] = usuario_id
            sesion["csrf_token"] = "token-pruebas"

        class ClienteConCSRF:
            def __init__(self, cliente):
                self.cliente = cliente
            def get(self, *args, **kwargs):
                return self.cliente.get(*args, **kwargs)
            def post(self, *args, **kwargs):
                kwargs.setdefault("headers", {})["X-CSRF-Token"] = "token-pruebas"
                return self.cliente.post(*args, **kwargs)
            def delete(self, *args, **kwargs):
                kwargs.setdefault("headers", {})["X-CSRF-Token"] = "token-pruebas"
                return self.cliente.delete(*args, **kwargs)

        self.cliente = ClienteConCSRF(cliente_real)

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
            "Hola",
            self.usuario_id
        )

        self.cliente.delete(
            f"/api/conversaciones/{conversacion_id}"
        )

        self.assertEqual(
            database.obtener_mensajes(conversacion_id, self.usuario_id) if database.existe_conversacion(conversacion_id, self.usuario_id) else [],
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
            CORRECCION_FALSA,
            self.usuario_id
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

class PruebasAislamientoUsuarios(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.ruta_original = database.DATABASE
        database.DATABASE = Path(self.directorio.name) / "aislamiento.db"
        database.inicializar_db()
        app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
        self.cliente = app.test_client()

    def tearDown(self):
        database.DATABASE = self.ruta_original
        self.directorio.cleanup()

    def registrar(self, email):
        self.cliente.get('/registro')
        with self.cliente.session_transaction() as sesion:
            token = sesion['csrf_token']
        respuesta = self.cliente.post('/registro', data={
            'email': email, 'password': 'clave-segura-12345',
            'confirm_password': 'clave-segura-12345', 'csrf_token': token
        })
        self.assertEqual(respuesta.status_code, 302)
        with self.cliente.session_transaction() as sesion:
            return sesion['csrf_token']

    def test_api_requiere_sesion(self):
        self.assertEqual(self.cliente.get('/api/conversaciones').status_code, 401)
        self.assertEqual(self.cliente.get('/').status_code, 302)

    def test_conversaciones_y_ejercicios_aislados(self):
        token = self.registrar('uno@example.com')
        cabeceras = {'X-CSRF-Token': token}
        chat = self.cliente.post('/api/conversaciones', headers=cabeceras).get_json()['id']
        with patch('app.generar_ejercicio', return_value=EJERCICIO_FALSO):
            ejercicio = self.cliente.post('/api/ejercicios/generar', json={
                'tema': 'funciones', 'nivel': 'basico'
            }, headers=cabeceras).get_json()['ejercicio']['id']
        self.cliente.post('/salir', data={'csrf_token': token})
        token = self.registrar('dos@example.com')
        cabeceras = {'X-CSRF-Token': token}
        self.assertEqual(self.cliente.get('/api/conversaciones').get_json(), [])
        self.assertEqual(self.cliente.get('/api/ejercicios').get_json(), [])
        self.assertEqual(self.cliente.get(f'/api/conversaciones/{chat}').status_code, 404)
        self.assertEqual(self.cliente.get(f'/api/ejercicios/{ejercicio}').status_code, 404)
        self.assertEqual(self.cliente.delete(f'/api/conversaciones/{chat}', headers=cabeceras).status_code, 404)
        self.assertEqual(self.cliente.post('/api/chat', json={
            'conversacion_id': chat, 'mensaje': 'Hola'
        }, headers=cabeceras).status_code, 404)
        self.assertEqual(self.cliente.post('/api/ejercicios/corregir', json={
            'ejercicio_id': ejercicio, 'codigo': 'print(1)'
        }, headers=cabeceras).status_code, 404)

    def test_csrf_y_registro_duplicado(self):
        self.registrar('uno@example.com')
        self.assertEqual(self.cliente.post('/api/conversaciones').status_code, 400)
        self.cliente.post('/salir', data={'csrf_token': 'incorrecto'})
        with self.cliente.session_transaction() as sesion:
            self.assertIn('usuario_id', sesion)

    def test_datos_antiguos_se_conservan_sin_propietario(self):
        with database.conectar() as db:
            db.execute("INSERT INTO conversaciones (titulo) VALUES ('Chat anterior')")
            db.execute("INSERT INTO ejercicios (tema,nivel,titulo,enunciado,requisitos,pista) VALUES ('variables','basico','Anterior','Enunciado','[]','Pista')")
        self.registrar('uno@example.com')
        self.assertEqual(self.cliente.get('/api/conversaciones').get_json(), [])
        self.assertEqual(self.cliente.get('/api/ejercicios').get_json(), [])
        with database.conectar() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM conversaciones').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ejercicios').fetchone()[0], 1)

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "instance" / "codementor.db"


@contextmanager
def conectar():
    """
    Abre una conexión SQLite y garantiza su cierre.

    - Si todo va bien, confirma los cambios.
    - Si ocurre un error, revierte la transacción.
    - Siempre cierra la conexión.
    """
    DATABASE.parent.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(DATABASE)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")

    try:
        yield conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


# ==========================================
# INICIALIZACIÓN
# ==========================================

def inicializar_db():
    with conectar() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS conversaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL
                    DEFAULT 'Nueva conversación',
                fecha_creacion TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversacion_id INTEGER NOT NULL,
                rol TEXT NOT NULL
                    CHECK (rol IN ('user', 'assistant')),
                contenido TEXT NOT NULL,
                fecha TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversacion_id)
                    REFERENCES conversaciones(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion
            ON mensajes(conversacion_id, id);

            CREATE TABLE IF NOT EXISTS ejercicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tema TEXT NOT NULL,
                nivel TEXT NOT NULL,
                titulo TEXT NOT NULL,
                enunciado TEXT NOT NULL,
                requisitos TEXT NOT NULL,
                pista TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS intentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ejercicio_id INTEGER NOT NULL,
                codigo TEXT NOT NULL,
                estado TEXT NOT NULL
                    CHECK (
                        estado IN (
                            'correcto',
                            'mejorar',
                            'incorrecto'
                        )
                    ),
                correccion TEXT NOT NULL,
                fecha TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ejercicio_id)
                    REFERENCES ejercicios(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_intentos_ejercicio
            ON intentos(ejercicio_id, id);
        """)


# ==========================================
# CONVERSACIONES
# ==========================================

def crear_conversacion():
    with conectar() as db:
        cursor = db.execute(
            "INSERT INTO conversaciones DEFAULT VALUES"
        )
        return cursor.lastrowid


def existe_conversacion(conversacion_id):
    with conectar() as db:
        fila = db.execute("""
            SELECT id
            FROM conversaciones
            WHERE id = ?
        """, (conversacion_id,)).fetchone()

        return fila is not None


def listar_conversaciones():
    with conectar() as db:
        filas = db.execute("""
            SELECT id, titulo, fecha_creacion
            FROM conversaciones
            ORDER BY id DESC
        """).fetchall()

        return [dict(fila) for fila in filas]


def obtener_conversacion(conversacion_id):
    with conectar() as db:
        fila = db.execute("""
            SELECT id, titulo, fecha_creacion
            FROM conversaciones
            WHERE id = ?
        """, (conversacion_id,)).fetchone()

        return dict(fila) if fila else None


def eliminar_conversacion(conversacion_id):
    """
    Elimina una conversación y sus mensajes.
    Devuelve True si existía.
    """
    with conectar() as db:
        cursor = db.execute("""
            DELETE FROM conversaciones
            WHERE id = ?
        """, (conversacion_id,))

        return cursor.rowcount > 0


def actualizar_titulo(conversacion_id, titulo):
    with conectar() as db:
        db.execute("""
            UPDATE conversaciones
            SET titulo = ?
            WHERE id = ?
        """, (titulo[:80], conversacion_id))


def guardar_intercambio(conversacion_id, pregunta, respuesta):
    with conectar() as db:
        db.executemany("""
            INSERT INTO mensajes (
                conversacion_id,
                rol,
                contenido
            )
            VALUES (?, ?, ?)
        """, [
            (conversacion_id, "user", pregunta),
            (conversacion_id, "assistant", respuesta)
        ])

        cantidad = db.execute("""
            SELECT COUNT(*)
            FROM mensajes
            WHERE conversacion_id = ?
        """, (conversacion_id,)).fetchone()[0]

        if cantidad == 2:
            db.execute("""
                UPDATE conversaciones
                SET titulo = ?
                WHERE id = ?
            """, (pregunta[:60], conversacion_id))


def guardar_mensaje(conversacion_id, rol, contenido):
    if rol not in ("user", "assistant"):
        raise ValueError("Rol de mensaje no válido.")

    with conectar() as db:
        db.execute("""
            INSERT INTO mensajes (
                conversacion_id,
                rol,
                contenido
            )
            VALUES (?, ?, ?)
        """, (conversacion_id, rol, contenido))


def obtener_mensajes(conversacion_id):
    with conectar() as db:
        filas = db.execute("""
            SELECT id, rol, contenido, fecha
            FROM mensajes
            WHERE conversacion_id = ?
            ORDER BY id ASC
        """, (conversacion_id,)).fetchall()

        return [dict(fila) for fila in filas]


def obtener_contexto(conversacion_id, limite=10):
    with conectar() as db:
        filas = db.execute("""
            SELECT rol, contenido
            FROM mensajes
            WHERE conversacion_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (conversacion_id, limite)).fetchall()

    filas.reverse()

    return [
        {
            "role": fila["rol"],
            "content": fila["contenido"]
        }
        for fila in filas
    ]


# ==========================================
# EJERCICIOS
# ==========================================

def guardar_ejercicio(tema, nivel, ejercicio):
    with conectar() as db:
        cursor = db.execute("""
            INSERT INTO ejercicios (
                tema,
                nivel,
                titulo,
                enunciado,
                requisitos,
                pista
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tema,
            nivel,
            ejercicio["titulo"],
            ejercicio["enunciado"],
            json.dumps(
                ejercicio["requisitos"],
                ensure_ascii=False
            ),
            ejercicio["pista"]
        ))

        return cursor.lastrowid


def convertir_ejercicio(fila):
    if fila is None:
        return None

    ejercicio = dict(fila)

    ejercicio["requisitos"] = json.loads(
        ejercicio["requisitos"]
    )

    return ejercicio


def obtener_ejercicio(ejercicio_id):
    with conectar() as db:
        fila = db.execute("""
            SELECT *
            FROM ejercicios
            WHERE id = ?
        """, (ejercicio_id,)).fetchone()

        return convertir_ejercicio(fila)


def listar_ejercicios():
    with conectar() as db:
        filas = db.execute("""
            SELECT *
            FROM ejercicios
            ORDER BY id DESC
        """).fetchall()

        return [
            convertir_ejercicio(fila)
            for fila in filas
        ]


# ==========================================
# INTENTOS Y CORRECCIONES
# ==========================================

def guardar_intento(ejercicio_id, codigo, correccion):
    with conectar() as db:
        cursor = db.execute("""
            INSERT INTO intentos (
                ejercicio_id,
                codigo,
                estado,
                correccion
            )
            VALUES (?, ?, ?, ?)
        """, (
            ejercicio_id,
            codigo,
            correccion["estado"],
            json.dumps(
                correccion,
                ensure_ascii=False
            )
        ))

        return cursor.lastrowid


def obtener_intentos(ejercicio_id):
    with conectar() as db:
        filas = db.execute("""
            SELECT *
            FROM intentos
            WHERE ejercicio_id = ?
            ORDER BY id DESC
        """, (ejercicio_id,)).fetchall()

        intentos = []

        for fila in filas:
            intento = dict(fila)

            intento["correccion"] = json.loads(
                intento["correccion"]
            )

            intentos.append(intento)

        return intentos


# ==========================================
# ESTADÍSTICAS
# ==========================================

def obtener_estadisticas():
    with conectar() as db:
        total_ejercicios = db.execute("""
            SELECT COUNT(*)
            FROM ejercicios
        """).fetchone()[0]

        completados = db.execute("""
            SELECT COUNT(DISTINCT ejercicio_id)
            FROM intentos
            WHERE estado = 'correcto'
        """).fetchone()[0]

        conversaciones = db.execute("""
            SELECT COUNT(*)
            FROM conversaciones
        """).fetchone()[0]

        intentos = db.execute("""
            SELECT COUNT(*)
            FROM intentos
        """).fetchone()[0]

    return {
        "total_ejercicios": total_ejercicios,
        "completados": completados,
        "conversaciones": conversaciones,
        "intentos": intentos
    }


def obtener_actividad_reciente(limite=10):
    with conectar() as db:
        filas = db.execute("""
            SELECT
                i.id,
                i.ejercicio_id,
                e.titulo,
                e.tema,
                e.nivel,
                i.estado,
                i.fecha
            FROM intentos i
            JOIN ejercicios e
                ON e.id = i.ejercicio_id
            ORDER BY i.id DESC
            LIMIT ?
        """, (limite,)).fetchall()

        return [dict(fila) for fila in filas]

"""Asigna datos antiguos sin propietario a una cuenta existente.

Uso (después de crear tu cuenta en la web):
    python migrar_datos.py tu_correo@ejemplo.com

Haz una copia de seguridad de instance/codementor.db antes de ejecutarlo.
No cambia datos ya asociados a otros usuarios.
"""
import sys
from database import conectar, inicializar_db, obtener_usuario_por_email


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python migrar_datos.py correo@ejemplo.com")
    inicializar_db()
    usuario = obtener_usuario_por_email(sys.argv[1].strip().lower())
    if not usuario:
        raise SystemExit("Cuenta no encontrada. Regístrate primero en la web.")
    with conectar() as db:
        chats = db.execute("UPDATE conversaciones SET usuario_id = ? WHERE usuario_id IS NULL", (usuario["id"],)).rowcount
        ejercicios = db.execute("UPDATE ejercicios SET usuario_id = ? WHERE usuario_id IS NULL", (usuario["id"],)).rowcount
    print(f"Asignados {chats} chats y {ejercicios} ejercicios a {usuario['email']}.")


if __name__ == "__main__":
    main()

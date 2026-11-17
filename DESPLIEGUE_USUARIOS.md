# Despliegue de CodeMentor IA con cuentas de usuario

## Importante antes de actualizar

- **No subas** `.env`, `.git`, `venv` ni `instance/codementor.db` a GitHub.
- **Haz una copia de seguridad** de la base de datos de PythonAnywhere. En Bash:
  `cp ~/CodeMentorIA/instance/codementor.db ~/codementor_backup_antes_usuarios.db`
- La migración añade una tabla `usuarios` y una columna `usuario_id` a `conversaciones` y `ejercicios`. **No borra** las conversaciones ni los ejercicios antiguos.
- Los datos antiguos quedan inicialmente sin propietario y **no son visibles** para ningún usuario hasta asignarlos expresamente.
- Las contraseñas se guardan como hashes de Werkzeug. No se envían correos de verificación ni recuperación de contraseña en esta versión.

## Instalación

1. Actualiza el código en tu ordenador y publícalo en GitHub. No sobrescribas tu base de datos existente.
2. En PythonAnywhere, entra en `~/CodeMentorIA`, activa `source venv/bin/activate` y ejecuta `git pull origin main` y `python -m pip install -r requirements.txt`.
3. Genera un secreto aleatorio **en la consola privada de PythonAnywhere**: `python -c "import secrets; print(secrets.token_hex(32))"`.
4. Añade al `.env` privado de PythonAnywhere una línea `SECRET_KEY=valor_aleatorio_generado`, conservando `OPENAI_API_KEY`. No compartas ni publiques ese valor. **Usa un secreto persistente**, no uno nuevo en cada reinicio.
5. En la pestaña **Web**, pulsa **Reload**. La aplicación ejecuta la migración no destructiva al iniciarse.
6. Visita `/registro` y crea tu propia cuenta con correo y contraseña (mínimo 12 caracteres).
7. Si quieres recuperar tus chats y ejercicios anteriores, desde la consola de PythonAnywhere ejecuta `python migrar_datos.py tu_correo@ejemplo.com` con tu correo real. Hazlo **solo después de crear tu cuenta** y verificar que el backup existe.
8. Recarga la página y comprueba que aparecen tus datos. Registra otra cuenta de prueba y verifica que no puede acceder a tus chats.

## Seguridad y limitaciones

- Todos los endpoints de datos exigen sesión y verifican propiedad en el servidor; los formularios y peticiones mutantes incluyen protección CSRF.
- La web usa cookies `HttpOnly`, `SameSite=Lax` y `Secure` por defecto (requiere HTTPS). En desarrollo local por HTTP, establece `COOKIE_SECURE=0` en `.env`.
- **Antes de abrir el registro a público** conviene añadir verificación de correo, recuperación de contraseña, límites de intentos de login, límites de llamadas a OpenAI y mecanismos contra abuso. Esta versión no incorpora esos controles.
- No ejecutes el servidor Flask de desarrollo en producción. Conserva la configuración WSGI de PythonAnywhere.
- No reemplaces la base de datos del servidor por una base vacía del ZIP: este paquete **no incluye** base de datos.

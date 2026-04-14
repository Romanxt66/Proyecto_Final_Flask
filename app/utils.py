"""
Utilidades compartidas: decoradores de roles, auditoría y helpers.
"""
from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user
from app import db
from datetime import datetime, timezone


# ─────────────────────────────────────────────
# Decorador de rol
# ─────────────────────────────────────────────
def role_required(*roles):
    """Protege una ruta para que solo usuarios con alguno de los roles dados puedan acceder."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Inicia sesión para continuar.', 'warning')
                return redirect(url_for('auth.login'))
            user_roles = {ur.rol.nombre.lower() for ur in current_user.roles}
            required = {r.lower() for r in roles}
            if not user_roles.intersection(required):
                flash('No tienes permiso para acceder a esa sección.', 'danger')
                return abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ─────────────────────────────────────────────
# Helper: detectar rol principal del usuario
# ─────────────────────────────────────────────
def get_user_role(usuario):
    """Devuelve el rol principal como string ('superusuario' > 'instructor' > 'aprendiz')."""
    nombres = {ur.rol.nombre.lower() for ur in usuario.roles}
    if 'superusuario' in nombres:
        return 'superusuario'
    if 'instructor' in nombres:
        return 'instructor'
    if 'aprendiz' in nombres:
        return 'aprendiz'
    return 'sin_rol'


# ─────────────────────────────────────────────
# Helper: registrar auditoría en historial
# ─────────────────────────────────────────────
def log_historial(usuario, modulo: str, accion: str, descripcion: str = ''):
    """Crea un registro de auditoría en historial_cambios."""
    from app.models.historial_cambios import HistorialCambios
    entry = HistorialCambios(
        id_usuario=usuario.id_usuario,
        modulo=modulo,
        accion=accion.upper(),
        descripcion=descripcion,
        fecha=datetime.now(timezone.utc)
    )
    db.session.add(entry)
    # No hacemos commit aquí; el caller lo hace junto con su transacción principal

"""
Blueprint de Autenticación:
  GET  /           → landing page
  GET/POST /login  → iniciar sesión
  GET/POST /registro → registro solo aprendices
  GET  /logout     → cerrar sesión
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol
from app.models.aprendiz import Aprendiz
from app.utils import get_user_role

bp = Blueprint('auth', __name__)


# ─── Landing page ─────────────────────────────
@bp.route('/')
def landing():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)
    return render_template('auth/landing.html')


# ─── Login ────────────────────────────────────
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == 'POST':
        correo   = request.form.get('correo', '').strip().lower()
        password = request.form.get('password', '')

        usuario = Usuario.query.filter_by(correo=correo).first()

        if not usuario:
            flash('Correo no encontrado.', 'danger')
            return render_template('auth/login.html')

        if not usuario.estado:
            flash('Tu cuenta está desactivada. Contacta al administrador.', 'warning')
            return render_template('auth/login.html')

        if not check_password_hash(usuario.password_hash, password):
            flash('Contraseña incorrecta.', 'danger')
            return render_template('auth/login.html')

        login_user(usuario, remember=True)
        flash(f'¡Bienvenido, {usuario.nombres}!', 'success')
        return _redirect_by_role(usuario)

    return render_template('auth/login.html')


# ─── Registro (solo aprendices) ───────────────
@bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == 'POST':
        datos = {
            'tipo_documento':   request.form.get('tipo_documento', '').strip(),
            'numero_documento': request.form.get('numero_documento', '').strip(),
            'nombres':          request.form.get('nombres', '').strip(),
            'apellidos':        request.form.get('apellidos', '').strip(),
            'correo':           request.form.get('correo', '').strip().lower(),
            'telefono':         request.form.get('telefono', '').strip(),
            'password':         request.form.get('password', ''),
            'confirm_password': request.form.get('confirm_password', ''),
        }

        # Validaciones básicas
        if not all([datos['nombres'], datos['apellidos'], datos['correo'], datos['password']]):
            flash('Completa todos los campos obligatorios.', 'danger')
            return render_template('auth/registro.html')

        if datos['password'] != datos['confirm_password']:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/registro.html')

        if len(datos['password']) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('auth/registro.html')

        if Usuario.query.filter_by(correo=datos['correo']).first():
            flash('Ya existe una cuenta con ese correo.', 'warning')
            return render_template('auth/registro.html')

        # Crear usuario
        nuevo_usuario = Usuario(
            tipo_documento=datos['tipo_documento'],
            numero_documento=datos['numero_documento'],
            nombres=datos['nombres'],
            apellidos=datos['apellidos'],
            correo=datos['correo'],
            telefono=datos['telefono'],
            password_hash=generate_password_hash(datos['password']),
            estado=True
        )
        db.session.add(nuevo_usuario)
        db.session.flush()  # obtener id_usuario sin commit

        # Asignar rol aprendiz
        rol_aprendiz = Rol.query.filter_by(nombre='aprendiz').first()
        if rol_aprendiz:
            db.session.add(UsuarioRol(id_usuario=nuevo_usuario.id_usuario, id_rol=rol_aprendiz.id_rol))

        # Crear registro en tabla aprendiz
        aprendiz = Aprendiz(
            id_usuario=nuevo_usuario.id_usuario,
            estado_practica='En proceso',
            horas_requeridas=880,
            horas_cumplidas=0
        )
        db.session.add(aprendiz)
        db.session.commit()

        flash('Cuenta creada correctamente. Inicia sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html')


# ─── Logout ───────────────────────────────────
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('auth.landing'))


# ─── Helper: redirigir según rol ──────────────
def _redirect_by_role(usuario):
    rol = get_user_role(usuario)
    if rol == 'superusuario':
        return redirect(url_for('admin.dashboard'))
    if rol == 'instructor':
        return redirect(url_for('instructor.dashboard'))
    return redirect(url_for('aprendiz.dashboard'))

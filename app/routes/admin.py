"""
Blueprint Admin/Superusuario — 7 módulos:
  /admin/dashboard
  /admin/usuarios
  /admin/roles
  /admin/instructores
  /admin/empresas
  /admin/historial
  /admin/backup
"""
import io
import json
from datetime import datetime, timezone
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, send_file)
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash
from app import db
from app.utils import role_required, log_historial
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol
from app.models.instructor import Instructor
from app.models.aprendiz import Aprendiz
from app.models.empresa import Empresa
from app.models.historial_cambios import HistorialCambios

bp = Blueprint('admin', __name__, url_prefix='/admin')


# ─── Dashboard ────────────────────────────────
@bp.route('/dashboard')
@login_required
@role_required('superusuario')
def dashboard():
    total_usuarios    = Usuario.query.count()
    total_aprendices  = Aprendiz.query.count()
    total_instructores = Instructor.query.count()
    total_empresas    = Empresa.query.filter_by(activa=True).count()
    cambios_recientes = (HistorialCambios.query
                         .order_by(HistorialCambios.fecha.desc())
                         .limit(10).all())
    return render_template('admin/dashboard.html',
                           total_usuarios=total_usuarios,
                           total_aprendices=total_aprendices,
                           total_instructores=total_instructores,
                           total_empresas=total_empresas,
                           cambios_recientes=cambios_recientes)


# ─── Gestionar Usuarios ───────────────────────
@bp.route('/usuarios')
@login_required
@role_required('superusuario')
def usuarios():
    q = request.args.get('q', '').strip()
    query = Usuario.query
    if q:
        query = query.filter(
            (Usuario.nombres.ilike(f'%{q}%')) |
            (Usuario.apellidos.ilike(f'%{q}%')) |
            (Usuario.correo.ilike(f'%{q}%'))
        )
    lista = query.order_by(Usuario.fecha_creacion.desc()).all()
    roles = Rol.query.all()
    return render_template('admin/usuarios.html', usuarios=lista, roles=roles, q=q)


@bp.route('/usuarios/crear', methods=['POST'])
@login_required
@role_required('superusuario')
def crear_usuario():
    nombres   = request.form.get('nombres', '').strip()
    apellidos = request.form.get('apellidos', '').strip()
    correo    = request.form.get('correo', '').strip().lower()
    password  = request.form.get('password', '')
    id_rol    = request.form.get('id_rol', type=int)

    if Usuario.query.filter_by(correo=correo).first():
        flash('Ya existe un usuario con ese correo.', 'warning')
        return redirect(url_for('admin.usuarios'))

    u = Usuario(nombres=nombres, apellidos=apellidos, correo=correo,
                password_hash=generate_password_hash(password), estado=True)
    db.session.add(u)
    db.session.flush()

    if id_rol:
        db.session.add(UsuarioRol(id_usuario=u.id_usuario, id_rol=id_rol))

    # Si es aprendiz, crear registro
    rol = Rol.query.get(id_rol)
    if rol and rol.nombre == 'aprendiz':
        db.session.add(Aprendiz(id_usuario=u.id_usuario,
                                estado_practica='En proceso',
                                horas_requeridas=880, horas_cumplidas=0))
    elif rol and rol.nombre == 'instructor':
        db.session.add(Instructor(id_usuario=u.id_usuario, activo=True))

    log_historial(current_user, 'Usuarios', 'CREAR', f'Usuario {correo} creado')
    db.session.commit()
    flash(f'Usuario {nombres} {apellidos} creado.', 'success')
    return redirect(url_for('admin.usuarios'))


@bp.route('/usuarios/<int:id_usuario>/toggle', methods=['POST'])
@login_required
@role_required('superusuario')
def toggle_usuario(id_usuario):
    u = Usuario.query.get_or_404(id_usuario)
    u.estado = not u.estado
    estado_str = 'activado' if u.estado else 'desactivado'
    log_historial(current_user, 'Usuarios', 'MODIFICAR',
                  f'Usuario {u.correo} {estado_str}')
    db.session.commit()
    flash(f'Usuario {estado_str}.', 'success')
    return redirect(url_for('admin.usuarios'))


# ─── Asignar Roles ────────────────────────────
@bp.route('/roles')
@login_required
@role_required('superusuario')
def roles():
    usuarios = Usuario.query.order_by(Usuario.nombres).all()
    roles_disponibles = Rol.query.all()
    return render_template('admin/roles.html',
                           usuarios=usuarios,
                           roles=roles_disponibles)


@bp.route('/roles/asignar', methods=['POST'])
@login_required
@role_required('superusuario')
def asignar_rol():
    id_usuario = request.form.get('id_usuario', type=int)
    id_rol     = request.form.get('id_rol', type=int)
    if not id_usuario or not id_rol:
        flash('Datos incompletos.', 'danger')
        return redirect(url_for('admin.roles'))

    existe = UsuarioRol.query.filter_by(id_usuario=id_usuario, id_rol=id_rol).first()
    if existe:
        flash('El usuario ya tiene ese rol.', 'warning')
        return redirect(url_for('admin.roles'))

    db.session.add(UsuarioRol(id_usuario=id_usuario, id_rol=id_rol))
    # Crear perfil si no existe
    rol = Rol.query.get(id_rol)
    if rol.nombre == 'aprendiz' and not Aprendiz.query.filter_by(id_usuario=id_usuario).first():
        db.session.add(Aprendiz(id_usuario=id_usuario,
                                estado_practica='En proceso',
                                horas_requeridas=880, horas_cumplidas=0))
    elif rol.nombre == 'instructor' and not Instructor.query.filter_by(id_usuario=id_usuario).first():
        db.session.add(Instructor(id_usuario=id_usuario, activo=True))

    log_historial(current_user, 'Roles', 'MODIFICAR',
                  f'Rol {rol.nombre} asignado a usuario {id_usuario}')
    db.session.commit()
    flash(f'Rol "{rol.nombre}" asignado.', 'success')
    return redirect(url_for('admin.roles'))


@bp.route('/roles/quitar', methods=['POST'])
@login_required
@role_required('superusuario')
def quitar_rol():
    id_usuario = request.form.get('id_usuario', type=int)
    id_rol     = request.form.get('id_rol', type=int)
    ur = UsuarioRol.query.filter_by(id_usuario=id_usuario, id_rol=id_rol).first()
    if ur:
        db.session.delete(ur)
        log_historial(current_user, 'Roles', 'ELIMINAR',
                      f'Rol {id_rol} quitado a usuario {id_usuario}')
        db.session.commit()
        flash('Rol removido.', 'success')
    return redirect(url_for('admin.roles'))


# ─── Gestionar Instructores ───────────────────
@bp.route('/instructores')
@login_required
@role_required('superusuario')
def instructores():
    lista = Instructor.query.join(Usuario).order_by(Usuario.nombres).all()
    return render_template('admin/instructores.html', instructores=lista)


@bp.route('/instructores/<int:id_instructor>/toggle', methods=['POST'])
@login_required
@role_required('superusuario')
def toggle_instructor(id_instructor):
    inst = Instructor.query.get_or_404(id_instructor)
    inst.activo = not inst.activo
    log_historial(current_user, 'Instructores', 'MODIFICAR',
                  f'Instructor {id_instructor} {"activado" if inst.activo else "desactivado"}')
    db.session.commit()
    flash('Estado del instructor actualizado.', 'success')
    return redirect(url_for('admin.instructores'))


@bp.route('/instructores/<int:id_instructor>/area', methods=['POST'])
@login_required
@role_required('superusuario')
def editar_area_instructor(id_instructor):
    inst = Instructor.query.get_or_404(id_instructor)
    inst.area_formacion = request.form.get('area_formacion', '').strip()
    log_historial(current_user, 'Instructores', 'MODIFICAR',
                  f'Área instructor {id_instructor}: {inst.area_formacion}')
    db.session.commit()
    flash('Área de formación actualizada.', 'success')
    return redirect(url_for('admin.instructores'))


# ─── Gestionar Empresas ───────────────────────
@bp.route('/empresas')
@login_required
@role_required('superusuario')
def empresas():
    lista = Empresa.query.order_by(Empresa.nombre).all()
    return render_template('admin/empresas.html', empresas=lista)


@bp.route('/empresas/crear', methods=['POST'])
@login_required
@role_required('superusuario')
def crear_empresa():
    nombre = request.form.get('nombre', '').strip()
    if not nombre:
        flash('El nombre es obligatorio.', 'danger')
        return redirect(url_for('admin.empresas'))
    e = Empresa(
        nombre=nombre,
        nit=request.form.get('nit', '').strip(),
        direccion=request.form.get('direccion', '').strip(),
        telefono=request.form.get('telefono', '').strip(),
        contacto=request.form.get('contacto', '').strip(),
        persona_contacto=request.form.get('persona_contacto', '').strip(),
        activa=True
    )
    db.session.add(e)
    log_historial(current_user, 'Empresas', 'CREAR', f'Empresa {nombre} creada')
    db.session.commit()
    flash(f'Empresa "{nombre}" creada.', 'success')
    return redirect(url_for('admin.empresas'))


@bp.route('/empresas/<int:id_empresa>/editar', methods=['POST'])
@login_required
@role_required('superusuario')
def editar_empresa(id_empresa):
    e = Empresa.query.get_or_404(id_empresa)
    e.nombre           = request.form.get('nombre', e.nombre).strip()
    e.nit              = request.form.get('nit', e.nit or '').strip()
    e.direccion        = request.form.get('direccion', e.direccion or '').strip()
    e.telefono         = request.form.get('telefono', e.telefono or '').strip()
    e.contacto         = request.form.get('contacto', e.contacto or '').strip()
    e.persona_contacto = request.form.get('persona_contacto', e.persona_contacto or '').strip()
    e.activa           = 'activa' in request.form
    log_historial(current_user, 'Empresas', 'MODIFICAR', f'Empresa {id_empresa} editada')
    db.session.commit()
    flash('Empresa actualizada.', 'success')
    return redirect(url_for('admin.empresas'))


# ─── Historial / Auditoría ────────────────────
@bp.route('/historial')
@login_required
@role_required('superusuario')
def historial():
    page = request.args.get('page', 1, type=int)
    registros = (HistorialCambios.query
                 .order_by(HistorialCambios.fecha.desc())
                 .paginate(page=page, per_page=30, error_out=False))
    return render_template('admin/historial.html', registros=registros)


# ─── Backup y Reportes (exportar Excel) ───────
@bp.route('/backup')
@login_required
@role_required('superusuario')
def backup():
    aprendices  = Aprendiz.query.all()
    instructores = Instructor.query.all()
    empresas    = Empresa.query.all()
    return render_template('admin/backup.html',
                           aprendices=aprendices,
                           instructores=instructores,
                           empresas=empresas)


@bp.route('/backup/exportar/<string:tipo>')
@login_required
@role_required('superusuario')
def exportar_excel(tipo):
    try:
        import openpyxl
    except ImportError:
        flash('Instala openpyxl: pip install openpyxl', 'danger')
        return redirect(url_for('admin.backup'))

    wb = openpyxl.Workbook()
    ws = wb.active

    if tipo == 'aprendices':
        ws.title = 'Aprendices'
        ws.append(['ID', 'Nombres', 'Apellidos', 'Correo', 'Ficha',
                   'Estado Práctica', 'Horas Requeridas', 'Horas Cumplidas', 'Empresa'])
        for ap in Aprendiz.query.all():
            ws.append([
                ap.id_aprendiz,
                ap.usuario.nombres,
                ap.usuario.apellidos,
                ap.usuario.correo,
                ap.ficha or '',
                ap.estado_practica or '',
                ap.horas_requeridas or 0,
                ap.horas_cumplidas or 0,
                ap.empresa.nombre if ap.empresa else ''
            ])
        filename = 'aprendices.xlsx'

    elif tipo == 'instructores':
        ws.title = 'Instructores'
        ws.append(['ID', 'Nombres', 'Apellidos', 'Correo', 'Área Formación', 'Activo'])
        for inst in Instructor.query.all():
            ws.append([
                inst.id_instructor,
                inst.usuario.nombres,
                inst.usuario.apellidos,
                inst.usuario.correo,
                inst.area_formacion or '',
                'Sí' if inst.activo else 'No'
            ])
        filename = 'instructores.xlsx'

    elif tipo == 'empresas':
        ws.title = 'Empresas'
        ws.append(['ID', 'Nombre', 'NIT', 'Dirección', 'Teléfono', 'Contacto', 'Persona', 'Activa'])
        for e in Empresa.query.all():
            ws.append([
                e.id_empresa, e.nombre, e.nit or '',
                e.direccion or '', e.telefono or '',
                e.contacto or '', e.persona_contacto or '',
                'Sí' if e.activa else 'No'
            ])
        filename = 'empresas.xlsx'

    elif tipo == 'historial':
        ws.title = 'Historial'
        ws.append(['ID', 'Usuario', 'Módulo', 'Acción', 'Descripción', 'Fecha'])
        for h in HistorialCambios.query.order_by(HistorialCambios.fecha.desc()).all():
            ws.append([
                h.id_historial,
                f'{h.usuario.nombres} {h.usuario.apellidos}',
                h.modulo or '',
                h.accion or '',
                h.descripcion or '',
                h.fecha.strftime('%Y-%m-%d %H:%M:%S') if h.fecha else ''
            ])
        filename = 'historial.xlsx'
    else:
        flash('Tipo de exportación no válido.', 'danger')
        return redirect(url_for('admin.backup'))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    log_historial(current_user, 'Backup', 'CREAR', f'Exportación Excel: {tipo}')
    db.session.commit()
    return send_file(buf, download_name=filename,
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

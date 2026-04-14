import sys
from app import create_app, db
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.usuario_rol import UsuarioRol
from werkzeug.security import generate_password_hash

def seed_data():
    """Crea los roles básicos y un usuario superusuario si la base de datos está vacía."""
    print("Iniciando Seed...")
    
    # 1. Crear roles
    roles = ['aprendiz', 'instructor', 'superusuario']
    for r in roles:
         if not Rol.query.filter_by(nombre=r).first():
             db.session.add(Rol(nombre=r, descripcion=f'Rol de {r} en el sistema'))
             print(f"Rol '{r}' creado.")
    
    db.session.commit()

    # 2. Crear superusuario inicial
    correo_admin = 'admin@sena.edu.co'
    admin_user = Usuario.query.filter_by(correo=correo_admin).first()
    
    if not admin_user:
        admin_user = Usuario(
            tipo_documento='CC',
            numero_documento='1234567890',
            nombres='Administrador',
            apellidos='Sistema SENA',
            correo=correo_admin,
            password_hash=generate_password_hash('Admin123!'),
            estado=True
        )
        db.session.add(admin_user)
        db.session.flush() # Para tener su ID disponible sin comitear
        
        # Asignar rol superusuario
        rol_super = Rol.query.filter_by(nombre='superusuario').first()
        if rol_super:
            db.session.add(UsuarioRol(id_usuario=admin_user.id_usuario, id_rol=rol_super.id_rol))
            print(f"Superusuario '{correo_admin}' (pass: Admin123!) creado correctamente.")
        
        db.session.commit()
    else:
        print("El superusuario ya existe. Omitiendo la creación.")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_data()
    print("Seed finalizado.")

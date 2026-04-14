from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():

    app = Flask(__name__)    
    app.config.from_object('config.Config')
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(id_usuario):
        from .models.usuario import Usuario
        return Usuario.query.get(int(id_usuario))

    # Importar modelos para que SQLAlchemy los registre
    with app.app_context():
        from app.models import (
            usuario, rol, usuario_rol, instructor,
            aprendiz, curso, curso_instructor, curso_aprendiz,
            evidencia, progreso_aprendiz, empresa,
            historial_cambios, notificacion, aprendiz_backup
        )

    # Register blueprints
    from app.routes import (
        auth,
        instructor, aprendiz, curso,
        evidencia, empresa, notificacion
    )
    app.register_blueprint(auth.bp)
    app.register_blueprint(instructor.bp)
    app.register_blueprint(aprendiz.bp)
    app.register_blueprint(curso.bp)
    app.register_blueprint(evidencia.bp)
    app.register_blueprint(empresa.bp)
    app.register_blueprint(notificacion.bp)

    @app.errorhandler(Exception)
    def handle_error(e):
        print(f"An error occurred: {str(e)}")
        return {"error": str(e)}, 500

    return app
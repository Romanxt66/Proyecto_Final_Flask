from app import db

class Empresa(db.Model):
    __tablename__ = 'empresa'
    id_empresa  = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(150), nullable=False)
    nit         = db.Column(db.String(50))
    direccion   = db.Column(db.Text)
    telefono    = db.Column(db.String(20))
    activa      = db.Column(db.Boolean, default=True)
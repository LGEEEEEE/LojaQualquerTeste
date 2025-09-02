# app/models.py
from app import db
from flask_login import UserMixin
import datetime
from sqlalchemy import Numeric

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    imagem = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Produto {self.nome}>'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    # A relação para aceder facilmente aos pedidos deste utilizador.
    # O backref='user' cria automaticamente o atributo 'pedido.user' no modelo Pedido.
    pedidos = db.relationship('Pedido', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_pedido = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    status = db.Column(db.String(30), nullable=False, default='Pendente')
    total = db.Column(db.Numeric(10, 2), nullable=False)

    # A relação para aceder facilmente aos itens deste pedido
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Pedido {self.id}>'

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    produto = db.relationship('Produto')

    def __repr__(self):
        return f'<ItemPedido {self.id}>'
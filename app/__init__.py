# app/__init__.py
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
import mercadopago
import os
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_admin import Admin
from flask_babel import Babel
# NOVAS IMPORTAÇÕES
from decimal import Decimal
from flask.json.provider import JSONProvider
import json

# ======================= NOVO CÓDIGO =======================
# Esta classe vai "ensinar" o Flask a lidar com o tipo Decimal
class CustomJSONProvider(JSONProvider):
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, **kwargs, cls=self.encoder)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)
# ===================== FIM DO NOVO CÓDIGO =====================


# Carrega as variáveis de ambiente do ficheiro .env
load_dotenv()

# Cria as instâncias principais da aplicação e das extensões
app = Flask(__name__)

# ======================= NOVA LINHA =======================
# Diz ao Flask para usar nossa classe customizada para JSON
app.json_provider = CustomJSONProvider(app)
app.json_provider.encoder = CustomJSONEncoder
# ===================== FIM DA NOVA LINHA =====================

app.config.from_object('app.config.Config')

# --- CONFIGURAÇÃO DO IDIOMA ---
app.config['BABEL_DEFAULT_LOCALE'] = 'pt_BR'
babel = Babel(app)
# -----------------------------

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

# ... (O RESTO DO SEU ARQUIVO CONTINUA EXATAMENTE IGUAL) ...
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para aceder a esta página.'
login_manager.login_message_category = 'info'

from app import models

@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

from app.admin_views import SecureModelView, SecureAdminIndexView

ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    raise ValueError("A variável de ambiente MP_ACCESS_TOKEN não foi configurada.")
sdk = mercadopago.SDK(ACCESS_TOKEN)

admin = Admin(
    app,
    name='Painel da Loja',
    template_mode='bootstrap4',
    index_view=SecureAdminIndexView(endpoint='admin_home')
)

admin.add_view(SecureModelView(models.Produto, db.session, name='Produtos'))
admin.add_view(SecureModelView(models.User, db.session, name='Utilizadores'))
admin.add_view(SecureModelView(models.Pedido, db.session, name='Pedidos'))
admin.add_view(SecureModelView(models.ItemPedido, db.session, name='Itens dos Pedidos'))

with app.app_context():
    db.create_all()
    if models.Produto.query.count() == 0:
        exemplos = [
            models.Produto(nome="Camiseta Básica", preco=Decimal('59.90'), imagem="img/camiseta.jpg"),
            models.Produto(nome="Calça Jeans Skinny", preco=Decimal('129.90'), imagem="img/calca.jpg"),
            models.Produto(nome="Jaqueta de Couro", preco=Decimal('349.90'), imagem="img/jaqueta.jpg"),
        ]
        db.session.add_all(exemplos)
        db.session.commit()

@app.context_processor
def inject_cart_count():
    count = 0
    if 'cart' in session:
        count = sum(session['cart'].values())
    return dict(cart_item_count=count)

from app import routes
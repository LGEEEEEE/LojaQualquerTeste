# app/__init__.py
import os
import json
from decimal import Decimal
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_admin import Admin
from flask_babel import Babel
from flask_migrate import Migrate
from dotenv import load_dotenv
import mercadopago

# Carrega as variáveis de ambiente
load_dotenv()

# Inicialização das extensões (sem app)
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
babel = Babel()
migrate = Migrate()
from app.admin_views import SecureAdminIndexView
admin = Admin(name='Painel da Loja', template_mode='bootstrap4', index_view=SecureAdminIndexView(endpoint='admin_home'))

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

# Função de Criação da Aplicação (Application Factory)
def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('app.config.Config')
    
    app.json_encoder = CustomJSONEncoder

    # Vinculação das extensões com a aplicação
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    babel.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)

    login_manager.login_view = 'main.login' # <- Alterado para apontar para o blueprint
    login_manager.login_message = 'Por favor, faça login para aceder a esta página.'
    login_manager.login_message_category = 'info'

    with app.app_context():
        from app import models
        from app.admin_views import SecureModelView

        # Regista o Blueprint das rotas
        from .routes import main_bp
        app.register_blueprint(main_bp)

        @login_manager.user_loader
        def load_user(user_id):
            return models.User.query.get(int(user_id))

        # Configuração do Painel de Admin
        admin.add_view(SecureModelView(models.Produto, db.session, name='Produtos'))
        admin.add_view(SecureModelView(models.User, db.session, name='Utilizadores'))
        admin.add_view(SecureModelView(models.Pedido, db.session, name='Pedidos'))
        admin.add_view(SecureModelView(models.ItemPedido, db.session, name='Itens dos Pedidos'))

        # Anexa o SDK do Mercado Pago ao app
        ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
        if not ACCESS_TOKEN:
            raise ValueError("A variável de ambiente MP_ACCESS_TOKEN não foi configurada.")
        app.sdk = mercadopago.SDK(ACCESS_TOKEN)

        @app.context_processor
        def inject_cart_count():
            count = 0
            if 'cart' in session:
                count = sum(session['cart'].values())
            return dict(cart_item_count=count)

        return app
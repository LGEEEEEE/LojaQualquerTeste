# app/admin_views.py
from flask import redirect, url_for, request
from flask_admin import AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

# Classe para proteger a página principal do admin (/admin)
class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

# Classe para proteger as páginas dos modelos (produtos, utilizadores, etc.)
class SecureModelView(ModelView):
    # Dicionário para traduzir os nomes das colunas que aparecem no painel
    column_labels = {
        # Para o modelo Produto
        'nome': 'Nome do Produto',
        'preco': 'Preço (R$)',
        'imagem': 'Ficheiro da Imagem',

        # Para o modelo User
        'username': 'Nome de Utilizador',
        'email': 'E-mail',
        'password_hash': 'Senha Criptografada',
        'is_admin': 'É Administrador?',
        'pedidos': 'Pedidos do Utilizador',

        # Para os modelos Pedido e ItemPedido
        'user_id': 'ID do Utilizador',
        'data_pedido': 'Data do Pedido',
        'status': 'Estado',
        'total': 'Valor Total (R$)',
        'itens': 'Itens',
        'user': 'Cliente',
        'pedido_id': 'ID do Pedido',
        'produto_id': 'ID do Produto',
        'quantidade': 'Quantidade',
        'preco_unitario': 'Preço Unitário (R$)',
        'produto': 'Produto'
    }

    # Esta função é chamada para verificar se o utilizador pode aceder à página
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    # Esta função é chamada se a verificação acima falhar
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))
# app/routes.py
from flask import (render_template, request, jsonify, url_for, flash, 
                   redirect, session, Blueprint, current_app)
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import Produto, User, Pedido, ItemPedido
from app.forms import RegistrationForm, LoginForm
import os
import secrets
from decimal import Decimal
import time

# Cria um Blueprint chamado 'main'
main_bp = Blueprint('main', __name__)

# --- Rotas de Autenticação e Utilizador ---

@main_bp.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.homepage'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('A sua conta foi criada! Já pode fazer login.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Registrar', form=form)

@main_bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.homepage'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.homepage'))
        else:
            flash('Login sem sucesso. Por favor, verifique o e-mail e a senha.', 'danger')
    return render_template('login.html', title='Login', form=form)

@main_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.homepage'))

@main_bp.route("/minha_conta")
@login_required
def minha_conta():
    pedidos = Pedido.query.filter_by(user_id=current_user.id).order_by(Pedido.data_pedido.desc()).all()
    return render_template('minha_conta.html', title='Minha Conta', pedidos=pedidos)

# --- Rotas da Loja e Carrinho ---

@main_bp.route("/")
def homepage():
    produtos = Produto.query.all()
    return render_template("index.html", produtos=produtos)

@main_bp.route("/add_to_cart/<int:produto_id>", methods=['POST'])
def add_to_cart(produto_id):
    if 'cart' not in session:
        session['cart'] = {}
    cart = session['cart']
    produto_id_str = str(produto_id)
    cart[produto_id_str] = cart.get(produto_id_str, 0) + 1
    session.modified = True
    flash('Produto adicionado ao carrinho!', 'success')
    return redirect(url_for('main.homepage'))

@main_bp.route("/cart")
@login_required
def cart():
    if 'cart' not in session or not session['cart']:
        flash('O seu carrinho está vazio.', 'info')
        return redirect(url_for('main.homepage'))
    
    ids_produtos = [int(id) for id in session['cart'].keys()]
    produtos_no_carrinho = Produto.query.filter(Produto.id.in_(ids_produtos)).all()
    
    total = sum(p.preco * session['cart'][str(p.id)] for p in produtos_no_carrinho)
    
    return render_template('cart.html', produtos=produtos_no_carrinho, total=total, cart=session['cart'])

@main_bp.route("/remove_from_cart/<int:produto_id>", methods=['POST'])
@login_required
def remove_from_cart(produto_id):
    produto_id_str = str(produto_id)
    if 'cart' in session and produto_id_str in session['cart']:
        session['cart'].pop(produto_id_str)
        session.modified = True
        flash('Produto removido do carrinho.', 'success')
    return redirect(url_for('main.cart'))

@main_bp.route("/update_cart/<int:produto_id>", methods=['POST'])
@login_required
def update_cart(produto_id):
    produto_id_str = str(produto_id)
    quantidade = request.form.get('quantidade', type=int)
    if 'cart' in session and produto_id_str in session['cart']:
        if quantidade is not None and quantidade > 0:
            session['cart'][produto_id_str] = quantidade
            session.modified = True
            flash('Quantidade atualizada com sucesso.', 'success')
        elif quantidade is not None and quantidade <= 0:
            session['cart'].pop(produto_id_str)
            session.modified = True
            flash('Produto removido do carrinho.', 'success')
    return redirect(url_for('main.cart'))

# --- Rota de Checkout e Pagamento ---

@main_bp.route("/checkout", methods=['GET'])
@login_required
def checkout():
    sdk = current_app.sdk
    if 'cart' not in session or not session['cart']:
        flash('Seu carrinho está vazio.', 'info')
        return redirect(url_for('main.homepage'))

    ids_produtos = [int(id) for id in session['cart'].keys()]
    produtos = Produto.query.filter(Produto.id.in_(ids_produtos)).all()
    
    total_final = sum(p.preco * session['cart'][str(p.id)] for p in produtos)
    
    items_para_pagamento = []
    for produto in produtos:
        quantidade = session['cart'][str(produto.id)]
        items_para_pagamento.append({
            "title": produto.nome, 
            "quantity": quantidade, 
            "unit_price": float(produto.preco),
            "currency_id": "BRL"
        })
    try:
        # Cria o pedido no banco de dados com status 'Pendente'
        novo_pedido = Pedido(user_id=current_user.id, total=total_final, status='Pendente', token=secrets.token_hex(16))
        db.session.add(novo_pedido)
        db.session.flush() # Para obter o ID do novo_pedido antes do commit

        for produto in produtos:
            quantidade = session['cart'][str(produto.id)]
            item = ItemPedido(
                pedido_id=novo_pedido.id, 
                produto_id=produto.id, 
                quantidade=quantidade, 
                preco_unitario=produto.preco
            )
            db.session.add(item)
        
        # URL base para os retornos (importante para o Render)
        base_url = os.getenv("SITE_URL") or request.url_root
        if not base_url:
            raise ValueError("Nenhuma URL base (SITE_URL) foi configurada.")
        if base_url.endswith('/'):
            base_url = base_url[:-1]

        back_urls = {
            "success": f"{base_url}{url_for('main.compra_certa', token=novo_pedido.token)}",
            "failure": f"{base_url}{url_for('main.compra_errada')}",
            "pending": f"{base_url}{url_for('main.minha_conta')}"
        }
        
        # Cria a preferência de pagamento
        preference_data = {
            "items": items_para_pagamento,
            "back_urls": back_urls,
            "auto_return": "approved",
            "payer": { "email": current_user.email },
            "notification_url": f"{base_url}{url_for('main.receber_notificacao_webhook')}",
            "external_reference": f"{novo_pedido.id}-{int(time.time())}",
        }
        
        preference_response = sdk.preference().create(preference_data)

        if preference_response and preference_response.get("status") == 201:
            preference_id = preference_response["response"]["id"]
            db.session.commit()
            session.pop('cart', None) # Limpa o carrinho
            
            # Renderiza a página de pagamento em vez de redirecionar
            return render_template("pagamento.html", 
                                   preference_id=preference_id, 
                                   public_key=os.getenv("MP_PUBLIC_KEY"),
                                   pedido_id=novo_pedido.id,
                                   total=total_final)
        else:
            print("🚨 ERRO AO CRIAR PREFERÊNCIA:", preference_response)
            raise ValueError("A resposta do Mercado Pago não foi bem-sucedida.")

    except Exception as e:
        db.session.rollback()
        print(f"🚨 ERRO CRÍTICO NO CHECKOUT: {e}")
        flash('Ocorreu um erro inesperado ao processar seu pedido. Por favor, tente novamente.', 'danger')
        return redirect(url_for('main.cart'))


# --- Rotas de Webhook e Retorno do Pagamento ---

@main_bp.route("/verificar_pagamento/<int:pedido_id>")
@login_required
def verificar_pagamento(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.user_id != current_user.id:
        return jsonify({'error': 'Acesso não autorizado'}), 403
    return jsonify({'status': pedido.status})

@main_bp.route("/receber_notificacao_webhook", methods=["POST"])
def receber_notificacao_webhook():
    sdk = current_app.sdk
    data = request.json
    if data and data.get("type") == "payment":
        payment_id = data.get("data", {}).get("id")
        if payment_id:
            try:
                payment_info_response = sdk.payment().get(payment_id)
                payment_info = payment_info_response.get("response", {})
                
                if payment_info.get("status") == "approved" and payment_info.get("external_reference"):
                    pedido_id_str = payment_info["external_reference"].split('-')[0]
                    pedido_id = int(pedido_id_str)

                    # Usar o app_context para acessar o banco de dados fora de uma requisição normal
                    with current_app.app_context():
                        pedido = Pedido.query.get(pedido_id)
                        if pedido and pedido.status != "Pago":
                            pedido.status = "Pago"
                            db.session.commit()
                            print(f"✅ Pedido {pedido_id} atualizado para 'Pago' via Webhook.")
            except Exception as e:
                print(f"🚨 Erro ao processar notificação de pagamento via Webhook: {e}")
    return jsonify({"status": "ok"}), 200

@main_bp.route("/compra_certa")
@login_required
def compra_certa():
    token = request.args.get('token')
    pedido_id_timestamp = request.args.get('external_reference')
    
    if not all([token, pedido_id_timestamp]):
        flash("Informações de retorno inválidas.", "danger")
        return redirect(url_for('main.minha_conta'))
        
    pedido_id = int(pedido_id_timestamp.split('-')[0])
    pedido = Pedido.query.filter_by(id=pedido_id, token=token).first_or_404()
    
    if pedido.user_id != current_user.id:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('main.homepage'))

    # Atualiza o status caso o webhook ainda não tenha processado
    if pedido.status != 'Pago':
        pedido.status = 'Pago'
        db.session.commit()

    flash("Pagamento aprovado com sucesso!", "success")
    return redirect(url_for('main.minha_conta'))


@main_bp.route("/compra_errada")
def compra_errada():
    flash("O pagamento falhou ou foi cancelado. Tente novamente.", "danger")
    return redirect(url_for('main.cart'))
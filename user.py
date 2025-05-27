from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.user import db, User, UserPlan
from datetime import datetime, timedelta
import os
import secrets

user_bp = Blueprint('user', __name__)

# Função para gerar token simples
def generate_token():
    return secrets.token_hex(32)

# Dicionário para armazenar tokens (em produção, usar Redis ou similar)
tokens = {}

# Decorador para verificar autenticação
def token_required(f):
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token or token not in tokens:
            return jsonify({'message': 'Token não fornecido ou inválido!'}), 401
            
        current_user = User.query.filter_by(id=tokens[token]).first()
        if not current_user:
            return jsonify({'message': 'Usuário não encontrado!'}), 401
            
        return f(current_user, *args, **kwargs)
    
    decorated.__name__ = f.__name__
    return decorated

# Rota para cadastro de usuário
@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Verificar se todos os campos obrigatórios estão presentes
    required_fields = ['name', 'email', 'password', 'phone', 'cpf']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Campo {field} é obrigatório!'}), 400
    
    # Verificar se o e-mail já está em uso
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'E-mail já cadastrado!'}), 400
    
    # Verificar se o CPF já está em uso
    if User.query.filter_by(cpf=data['cpf']).first():
        return jsonify({'message': 'CPF já cadastrado!'}), 400
    
    # Criar novo usuário
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(
        name=data['name'],
        email=data['email'],
        password=hashed_password,
        phone=data['phone'],
        cpf=data['cpf']
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'Usuário cadastrado com sucesso!'}), 201

# Rota para login
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'E-mail e senha são obrigatórios!'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        return jsonify({'message': 'Usuário não encontrado!'}), 404
    
    if check_password_hash(user.password, data['password']):
        token = generate_token()
        tokens[token] = user.id
        
        return jsonify({
            'message': 'Login realizado com sucesso!',
            'token': token,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email
            }
        }), 200
    
    return jsonify({'message': 'Senha incorreta!'}), 401

# Rota para obter informações do usuário
@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    # Verificar se o usuário tem plano ativo
    active_plan = UserPlan.query.filter_by(
        user_id=current_user.id, 
        status='active'
    ).filter(
        UserPlan.end_date >= datetime.utcnow()
    ).first()
    
    has_active_plan = bool(active_plan)
    plan_end_date = active_plan.end_date if active_plan else None
    
    return jsonify({
        'user': {
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
            'phone': current_user.phone,
            'cpf': current_user.cpf,
            'created_at': current_user.created_at
        },
        'plan': {
            'active': has_active_plan,
            'end_date': plan_end_date
        }
    }), 200

# Rota para adquirir plano
@user_bp.route('/plan/purchase', methods=['POST'])
@token_required
def purchase_plan(current_user):
    # Verificar se já existe um plano ativo
    active_plan = UserPlan.query.filter_by(
        user_id=current_user.id, 
        status='active'
    ).filter(
        UserPlan.end_date >= datetime.utcnow()
    ).first()
    
    if active_plan:
        return jsonify({'message': 'Você já possui um plano ativo!'}), 400
    
    # Simulação de processamento de pagamento
    # Em produção, integraria com gateway de pagamento
    payment_id = f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Criar novo plano
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=30)
    
    new_plan = UserPlan(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        status='active',
        payment_id=payment_id
    )
    
    db.session.add(new_plan)
    db.session.commit()
    
    return jsonify({
        'message': 'Plano adquirido com sucesso!',
        'plan': {
            'id': new_plan.id,
            'start_date': new_plan.start_date,
            'end_date': new_plan.end_date,
            'status': new_plan.status,
            'payment_id': new_plan.payment_id
        }
    }), 201

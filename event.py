from flask import Blueprint, request, jsonify
from src.models.user import db, Event, Bet, Winner
from datetime import datetime
import random

event_bp = Blueprint('event', __name__)

@event_bp.route('/create', methods=['POST'])
def create_event():
    data = request.get_json()
    
    # Verificar se todos os campos obrigatórios estão presentes
    required_fields = ['creator_id', 'title', 'reveal_date']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Campo {field} é obrigatório!'}), 400
    
    # Criar novo evento
    new_event = Event(
        creator_id=data['creator_id'],
        title=data['title'],
        description=data.get('description', ''),
        reveal_date=datetime.strptime(data['reveal_date'], '%Y-%m-%d %H:%M:%S')
    )
    
    db.session.add(new_event)
    db.session.commit()
    
    return jsonify({
        'message': 'Evento criado com sucesso!',
        'event': {
            'id': new_event.id,
            'title': new_event.title,
            'reveal_date': new_event.reveal_date.strftime('%Y-%m-%d %H:%M:%S')
        }
    }), 201

@event_bp.route('/list', methods=['GET'])
def list_events():
    events = Event.query.filter_by(status='active').all()
    
    events_list = []
    for event in events:
        events_list.append({
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'reveal_date': event.reveal_date.strftime('%Y-%m-%d %H:%M:%S'),
            'creator_id': event.creator_id,
            'creator_name': event.creator.name,
            'status': event.status,
            'total_raised': event.total_raised,
            'boy_bets_count': event.boy_bets_count,
            'girl_bets_count': event.girl_bets_count,
            'boy_percentage': event.get_boy_percentage(),
            'girl_percentage': event.get_girl_percentage(),
            'prize_pool': event.get_prize_pool(),
            'estimated_winner_prize': event.get_estimated_winner_prize(),
            'estimated_parents_prize': event.get_estimated_parents_prize()
        })
    
    return jsonify({'events': events_list}), 200

@event_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    return jsonify({
        'event': {
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'reveal_date': event.reveal_date.strftime('%Y-%m-%d %H:%M:%S'),
            'creator_id': event.creator_id,
            'creator_name': event.creator.name,
            'status': event.status,
            'total_raised': event.total_raised,
            'boy_bets_count': event.boy_bets_count,
            'girl_bets_count': event.girl_bets_count,
            'boy_percentage': event.get_boy_percentage(),
            'girl_percentage': event.get_girl_percentage(),
            'prize_pool': event.get_prize_pool(),
            'estimated_winner_prize': event.get_estimated_winner_prize(),
            'estimated_parents_prize': event.get_estimated_parents_prize()
        }
    }), 200

@event_bp.route('/bet', methods=['POST'])
def place_bet():
    data = request.get_json()
    
    # Verificar se todos os campos obrigatórios estão presentes
    required_fields = ['user_id', 'event_id', 'gender_guess']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Campo {field} é obrigatório!'}), 400
    
    # Verificar se o evento existe e está ativo
    event = Event.query.get_or_404(data['event_id'])
    if event.status != 'active':
        return jsonify({'message': 'Este evento não está mais ativo!'}), 400
    
    # Verificar se o usuário já apostou neste evento
    existing_bet = Bet.query.filter_by(
        user_id=data['user_id'],
        event_id=data['event_id']
    ).first()
    
    if existing_bet:
        return jsonify({'message': 'Você já apostou neste evento!'}), 400
    
    # Criar nova aposta
    new_bet = Bet(
        user_id=data['user_id'],
        event_id=data['event_id'],
        gender_guess=data['gender_guess']
    )
    
    # Atualizar estatísticas do evento
    event.total_raised += 15.0  # R$15 por aposta
    
    if data['gender_guess'] == 'boy':
        event.boy_bets_count += 1
    elif data['gender_guess'] == 'girl':
        event.girl_bets_count += 1
    
    db.session.add(new_bet)
    db.session.commit()
    
    return jsonify({
        'message': 'Aposta realizada com sucesso!',
        'bet': {
            'id': new_bet.id,
            'event_id': new_bet.event_id,
            'gender_guess': new_bet.gender_guess
        }
    }), 201

@event_bp.route('/reveal/<int:event_id>', methods=['POST'])
def reveal_gender(event_id):
    data = request.get_json()
    
    if 'gender' not in data:
        return jsonify({'message': 'O sexo do bebê é obrigatório!'}), 400
    
    event = Event.query.get_or_404(event_id)
    
    # Verificar se o evento já foi revelado
    if event.baby_gender:
        return jsonify({'message': 'Este evento já teve o sexo revelado!'}), 400
    
    # Atualizar o sexo do bebê
    event.baby_gender = data['gender']
    event.status = 'completed'
    
    # Encontrar apostas corretas
    correct_bets = Bet.query.filter_by(
        event_id=event_id,
        gender_guess=data['gender']
    ).all()
    
    # Se houver apostas corretas, sortear um vencedor
    if correct_bets:
        winner_bet = random.choice(correct_bets)
        
        # Calcular o prêmio (50% do valor arrecadado para sorteio)
        prize_pool = event.get_prize_pool()
        winner_prize = prize_pool * 0.5
        
        # Registrar o vencedor
        new_winner = Winner(
            event_id=event_id,
            user_id=winner_bet.user_id,
            prize_amount=winner_prize
        )
        
        db.session.add(new_winner)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Sexo revelado com sucesso!',
        'event': {
            'id': event.id,
            'title': event.title,
            'baby_gender': event.baby_gender,
            'winner_id': new_winner.user_id if correct_bets else None,
            'winner_prize': winner_prize if correct_bets else 0
        }
    }), 200

@event_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_events(user_id):
    # Eventos criados pelo usuário
    created_events = Event.query.filter_by(creator_id=user_id).all()
    
    # Eventos em que o usuário apostou
    bet_events = db.session.query(Event).join(Bet).filter(Bet.user_id == user_id).all()
    
    created_list = []
    for event in created_events:
        created_list.append({
            'id': event.id,
            'title': event.title,
            'reveal_date': event.reveal_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': event.status,
            'total_raised': event.total_raised,
            'boy_bets_count': event.boy_bets_count,
            'girl_bets_count': event.girl_bets_count,
            'prize_pool': event.get_prize_pool(),
            'estimated_parents_prize': event.get_estimated_parents_prize()
        })
    
    bet_list = []
    for event in bet_events:
        user_bet = Bet.query.filter_by(user_id=user_id, event_id=event.id).first()
        bet_list.append({
            'id': event.id,
            'title': event.title,
            'reveal_date': event.reveal_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': event.status,
            'gender_guess': user_bet.gender_guess,
            'baby_gender': event.baby_gender,
            'is_correct': user_bet.gender_guess == event.baby_gender if event.baby_gender else None
        })
    
    return jsonify({
        'created_events': created_list,
        'bet_events': bet_list
    }), 200

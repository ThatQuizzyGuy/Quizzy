from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import random
import string
from threading import Lock
from time import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dda90a19d5db316ebf8cee2757d7db4f'
socketio = SocketIO(app)

ROOMS = {}
lock = Lock()

QUESTIONS = [
    {"question": "What is the capital of France?", "answers": ["Paris", "London", "Berlin", "Madrid"], "correct": 0},
    {"question": "What is 5 + 7?", "answers": ["10", "12", "11", "14"], "correct": 1},
    {"question": "Which planet is closest to the Sun?", "answers": ["Earth", "Venus", "Mercury", "Mars"], "correct": 2}
]

@app.route('/')
def index():
    return render_template('index.html')

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

@socketio.on('create_room')
def create_room(data):
    name = data['name']
    code = generate_code()

    with lock:
        ROOMS[code] = {
            'players': {},
            'admin_sid': request.sid,
            'questions': QUESTIONS.copy(),
            'current_question': -1
        }
        ROOMS[code]['players'][request.sid] = {
            'name': name,
            'score': 0,
            'is_admin': True
        }
    join_room(code)
    emit('room_joined', {'room': code, 'is_admin': True}, room=request.sid)

@socketio.on('join_room')
def join(data):
    code = data['room'].upper()
    name = data['name']

    if code in ROOMS:
        with lock:
            ROOMS[code]['players'][request.sid] = {
                'name': name,
                'score': 0,
                'is_admin': False
            }
        join_room(code)
        emit('room_joined', {'room': code, 'is_admin': False}, room=request.sid)
        emit('player_joined', {'name': name}, room=code)
    else:
        emit('error', {'message': 'Room not found'}, room=request.sid)

@socketio.on('start_quiz')
def start_quiz(data):
    code = data['room']
    room = ROOMS.get(code)
    if room:
        room['current_question'] = -1
        send_next_question(code)

def send_next_question(code):
    room = ROOMS.get(code)
    if not room:
        return
    room['current_question'] += 1
    if room['current_question'] >= len(room['questions']):
        emit('quiz_ended', {}, room=code)
        return

    q = room['questions'][room['current_question']]
    emit('new_question', {
        'question': q['question'],
        'answers': q['answers']
    }, room=code)
    emit('show_leaderboard', get_leaderboard(code), room=room['admin_sid'])

@socketio.on('submit_answer')
def submit_answer(data):
    code = data['room']
    answer_index = data['answer']
    sid = request.sid
    room = ROOMS.get(code)
    if room:
        current_q = room['questions'][room['current_question']]
        correct = current_q['correct']
        if answer_index == correct:
            room['players'][sid]['score'] += 1
            emit('answer_result', {'correct': True})
        else:
            emit('answer_result', {'correct': False})

@socketio.on('next_question')
def next_question(data):
    send_next_question(data['room'])

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    with lock:
        for code, room in list(ROOMS.items()):
            if sid in room['players']:
                is_admin = room['players'][sid]['is_admin']
                del room['players'][sid]
                if is_admin and room['players']:
                    new_admin_sid = next(iter(room['players']))
                    room['admin_sid'] = new_admin_sid
                    room['players'][new_admin_sid]['is_admin'] = True
                    emit('new_admin', {'sid': new_admin_sid}, room=code)
                elif not room['players']:
                    del ROOMS[code]
                break

def get_leaderboard(code):
    room = ROOMS.get(code)
    if not room:
        return []
    return sorted(
        [{'name': p['name'], 'score': p['score']} for p in room['players'].values()],
        key=lambda x: x['score'], reverse=True
    )

if __name__ == '__main__':
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)

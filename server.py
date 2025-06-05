from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from threading import Lock
from time import time
import random
import string

app = Flask(__name__)
socketio = SocketIO(app)
ROOMS = {}
lock = Lock()

QUESTIONS = [
    {"q": "What is the capital of France?", "answers": ["Paris", "London", "Berlin", "Rome"], "correct": 0},
    {"q": "What color do you get when you mix red and white?", "answers": ["Pink", "Purple", "Brown", "Orange"], "correct": 0},
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory('static', path)

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

@socketio.on('create_room')
def on_create(data):
    code = generate_code()
    sid = request.sid
    with lock:
        ROOMS[code] = {
            'players': {sid: {'name': data['name'], 'score': 0, 'is_admin': True}},
            'admin_sid': sid,
            'started': False,
            'question_index': 0,
            'last_active': time()
        }
    join_room(code)
    emit('room_created', {'room': code, 'is_admin': True})
    emit('player_list', {'players': get_players(code)}, room=code)

@socketio.on('join_room')
def on_join(data):
    code = data['room'].upper()
    sid = request.sid
    with lock:
        if code in ROOMS and not ROOMS[code]['started']:
            ROOMS[code]['players'][sid] = {'name': data['name'], 'score': 0, 'is_admin': False}
            join_room(code)
            emit('room_joined', {'room': code, 'is_admin': False})
            emit('player_list', {'players': get_players(code)}, room=code)
        else:
            emit('error', {'message': 'Room not found or already started'})

@socketio.on('start_quiz')
def start_quiz():
    sid = request.sid
    with lock:
        for code, room in ROOMS.items():
            if room['admin_sid'] == sid:
                room['started'] = True
                room['question_index'] = 0
                send_question(code)
                break

def send_question(code):
    room = ROOMS[code]
    idx = room['question_index']
    if idx < len(QUESTIONS):
        question = QUESTIONS[idx]
        emit('new_question', {
            'question': question['q'],
            'answers': question['answers']
        }, room=code)
    else:
        emit('game_over', {}, room=code)

@socketio.on('submit_answer')
def handle_answer(data):
    sid = request.sid
    code = data['room']
    answer = data['answer']
    with lock:
        room = ROOMS[code]
        q = QUESTIONS[room['question_index']]
        correct = q['correct']
        if answer == correct:
            room['players'][sid]['score'] += 1
        emit('answer_result', {'correct': answer == correct})
        if 'responses' not in room:
            room['responses'] = set()
        room['responses'].add(sid)
        if len(room['responses']) >= len(room['players']) - 1:
            show_leaderboard(code)

def show_leaderboard(code):
    room = ROOMS[code]
    leaderboard = sorted([
        {'name': p['name'], 'score': p['score']}
        for p in room['players'].values()
    ], key=lambda x: x['score'], reverse=True)
    emit('leaderboard', {'leaderboard': leaderboard}, room=room['admin_sid'])
    room['responses'] = set()

@socketio.on('next_question')
def next_q():
    sid = request.sid
    for code, room in ROOMS.items():
        if room['admin_sid'] == sid:
            room['question_index'] += 1
            send_question(code)
            break

def get_players(code):
    return [{'name': p['name'], 'score': p['score'], 'is_admin': p['is_admin']} for p in ROOMS[code]['players'].values()]

@socketio.on('disconnect')
def disconnect_handler():
    sid = request.sid
    with lock:
        for code, room in list(ROOMS.items()):
            if sid in room['players']:
                del room['players'][sid]
                if sid == room['admin_sid']:
                    if room['players']:
                        new_sid = next(iter(room['players']))
                        room['admin_sid'] = new_sid
                        room['players'][new_sid]['is_admin'] = True
                        emit('new_admin', {'sid': new_sid}, room=code)
                    else:
                        del ROOMS[code]
                emit('player_list', {'players': get_players(code)}, room=code)
                break

if __name__ == '__main__':
    socketio.run(app, debug=True)

from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
import random
import string
from threading import Lock
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='threading')

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
def on_create_room(data):
    name = data['name']
    code = generate_code()
    with lock:
        ROOMS[code] = {
            'players': {},
            'current_question': 0,
            'answers': {},
            'scores': {},
            'host': request.sid
        }
        ROOMS[code]['players'][request.sid] = name
    join_room(code)
    emit('room_created', {'code': code, 'players': list(ROOMS[code]['players'].values())}, room=code)

@socketio.on('join_room')
def on_join_room(data):
    name = data['name']
    code = data['code'].upper()
    if code in ROOMS:
        with lock:
            ROOMS[code]['players'][request.sid] = name
        join_room(code)
        emit('player_joined', {'players': list(ROOMS[code]['players'].values())}, room=code)
    else:
        emit('error', {'message': 'Room not found'})

@socketio.on('start_game')
def on_start_game(data):
    code = data['code']
    if code in ROOMS:
        socketio.start_background_task(run_game, code)

def run_game(code):
    room = ROOMS[code]
    total_questions = len(QUESTIONS)
    
    for index in range(total_questions):
        room['current_question'] = index
        room['answers'] = {}
        question = QUESTIONS[index]

        # Show question
        socketio.emit('show_question', {
            'question': question['question'],
            'answers': question['answers'],
            'index': index + 1,
            'total': total_questions
        }, room=code)

        # Wait for players to answer
        socketio.sleep(10)  # wait 10 seconds for responses

        # Show correct answer
        correct_index = question['correct']
        socketio.emit('show_correct', {'correct': correct_index}, room=code)

        # Update scores
        for sid, answer in room['answers'].items():
            if answer == correct_index:
                room['scores'][sid] = room['scores'].get(sid, 0) + 100

        # Wait before showing leaderboard
        socketio.sleep(3)

        # Show leaderboard
        leaderboard = sorted(
            [(room['players'][sid], score) for sid, score in room['scores'].items()],
            key=lambda x: x[1], reverse=True
        )
        socketio.emit('show_leaderboard', {'leaderboard': leaderboard}, room=code)

        socketio.sleep(3)

    # End game
    socketio.emit('game_over', room=code)

@socketio.on('submit_answer')
def on_submit_answer(data):
    code = data['code']
    answer = data['answer']
    if code in ROOMS and request.sid in ROOMS[code]['players']:
        ROOMS[code]['answers'][request.sid] = answer

@socketio.on('disconnect')
def on_disconnect():
    for code, room in ROOMS.items():
        if request.sid in room['players']:
            name = room['players'].pop(request.sid)
            room['scores'].pop(request.sid, None)
            emit('player_left', {'name': name}, room=code)
            break

if __name__ == '__main__':
    socketio.run(app, debug=True)

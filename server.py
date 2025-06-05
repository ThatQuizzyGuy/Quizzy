from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import random, string
from threading import Lock
from time import time

app = Flask(__name__)
socketio = SocketIO(app)
lock = Lock()

ROOMS = {}
QUESTIONS = [
    {"question": "What is the capital of France?", "answers": ["Paris", "Rome", "Berlin", "Madrid"], "correct": 0},
    {"question": "Which planet is known as the Red Planet?", "answers": ["Earth", "Mars", "Venus", "Jupiter"], "correct": 1},
    {"question": "Who wrote 'Hamlet'?", "answers": ["Charles Dickens", "Leo Tolstoy", "William Shakespeare", "Mark Twain"], "correct": 2}
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

@socketio.on("create_room")
def handle_create(data):
    code = generate_room_code()
    sid = request.sid
    with lock:
        ROOMS[code] = {
            "admin_sid": sid,
            "players": {},
            "current_q": 0,
            "answers": {},
            "last_active": time(),
        }
        ROOMS[code]["players"][sid] = {"name": data["name"], "score": 0, "is_admin": True}
        join_room(code)
    emit("room_created", {"room": code, "is_host": True})
    emit("player_list", get_players(code), room=code)

@socketio.on("join_room")
def handle_join(data):
    code = data["room"].upper()
    sid = request.sid
    if code not in ROOMS:
        emit("join_failed", {"reason": "Room not found."})
        return
    with lock:
        ROOMS[code]["players"][sid] = {"name": data["name"], "score": 0, "is_admin": False}
        ROOMS[code]["last_active"] = time()
        join_room(code)
    emit("room_joined", {"room": code, "is_host": False})
    emit("player_list", get_players(code), room=code)

@socketio.on("start_quiz")
def handle_start(data):
    code = data["room"]
    with lock:
        room = ROOMS.get(code)
        if not room: return
        room["current_q"] = 0
        room["answers"] = {}
    send_question(code)

def send_question(code):
    room = ROOMS.get(code)
    if not room: return
    q_index = room["current_q"]
    if q_index >= len(QUESTIONS):
        socketio.emit("quiz_end", room=code)
        return
    question = QUESTIONS[q_index]
    socketio.emit("new_question", {
        "text": question["question"],
        "answers": question["answers"],
        "index": q_index
    }, room=code)
    socketio.start_background_task(timer_countdown, code)

def timer_countdown(code):
    seconds = 10
    for i in range(seconds, -1, -1):
        socketio.emit("timer_update", {"time": i}, room=code)
        socketio.sleep(1)
    handle_skip({"room": code})

@socketio.on("answer")
def handle_answer(data):
    code = data["room"]
    sid = request.sid
    answer = data["answer"]
    room = ROOMS.get(code)
    if not room or sid not in room["players"]: return

    if sid in room["answers"]: return
    room["answers"][sid] = answer
    correct = QUESTIONS[room["current_q"]]["correct"]
    if answer == correct:
        room["players"][sid]["score"] += 1
        emit("answer_feedback", {"correct": True})
    else:
        emit("answer_feedback", {"correct": False})

    if len(room["answers"]) == len(room["players"]) - 1:  # host doesn't answer
        show_leaderboard(code)

@socketio.on("skip_question")
def handle_skip(data):
    code = data["room"]
    room = ROOMS.get(code)
    if not room: return
    show_leaderboard(code)

def show_leaderboard(code):
    room = ROOMS.get(code)
    if not room: return
    leaderboard = sorted([
        {"name": p["name"], "score": p["score"]}
        for p in room["players"].values()
    ], key=lambda x: x["score"], reverse=True)
    socketio.emit("show_leaderboard", {"board": leaderboard}, room=code)

@socketio.on("next_question")
def next_q(data):
    code = data["room"]
    room = ROOMS.get(code)
    if not room: return
    room["current_q"] += 1
    room["answers"] = {}
    send_question(code)

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    with lock:
        for code, room in list(ROOMS.items()):
            if sid in room["players"]:
                del room["players"][sid]
                emit("player_list", get_players(code), room=code)
                if room["admin_sid"] == sid:
                    if room["players"]:
                        new_admin = next(iter(room["players"]))
                        room["admin_sid"] = new_admin
                        room["players"][new_admin]["is_admin"] = True
                        emit("new_admin", {"sid": new_admin}, room=code)
                    else:
                        del ROOMS[code]
                break

def get_players(code):
    return [
        {"sid": sid, "name": info["name"], "score": info["score"], "is_admin": info["is_admin"]}
        for sid, info in ROOMS[code]["players"].items()
    ]

if __name__ == "__main__":
    socketio.run(app, debug=True)

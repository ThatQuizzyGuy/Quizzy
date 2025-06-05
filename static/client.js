const socket = io();

let currentRoom = null;
let isHost = false;
let hasAnswered = false;

// Elements
const nameInput = document.getElementById('nameInput');
const roomInput = document.getElementById('roomInput');
const joinBtn = document.getElementById('joinBtn');
const createBtn = document.getElementById('createBtn');
const hostControls = document.getElementById('hostControls');
const hostRoomCode = document.getElementById('hostRoomCode');
const startBtn = document.getElementById('startBtn');
const nextBtn = document.getElementById('nextBtn');
const quizArea = document.getElementById('quizArea');
const questionText = document.getElementById('questionText');
const answersDiv = document.getElementById('answers');
const feedbackDiv = document.getElementById('feedback');
const leaderboardDiv = document.getElementById('leaderboard');
const leaderboardList = document.getElementById('leaderboardList');
const entryFrame = document.getElementById('entryFrame');
const notificationArea = document.getElementById('notificationArea');

function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';

    const img = document.createElement('img');
    img.src = 'static/Images/notification.png';

    const text = document.createElement('span');
    text.textContent = message;

    const close = document.createElement('span');
    close.textContent = '×';
    close.className = 'close';
    close.onclick = () => notification.remove();

    notification.appendChild(img);
    notification.appendChild(text);
    notification.appendChild(close);

    notificationArea.appendChild(notification);
}

createBtn.onclick = () => {
    const name = nameInput.value.trim();
    if (!name) return showNotification("Enter your name first!");
    socket.emit('create_room', {});
};

joinBtn.onclick = () => {
    const name = nameInput.value.trim();
    const room = roomInput.value.trim();
    if (!name || !room) return showNotification("Name or room missing.");
    socket.emit('join_room', { name, room });
};

startBtn.onclick = () => {
    socket.emit('start_quiz', { room: currentRoom });
    hostControls.style.display = 'none';
};

nextBtn.onclick = () => {
    socket.emit('next_question', { room: currentRoom });
    leaderboardDiv.style.display = 'none';
};

socket.on('room_created', ({ room }) => {
    currentRoom = room;
    isHost = true;
    showNotification(`Room created: ${room}`);
    hostRoomCode.textContent = room;
    hostControls.style.display = 'block';
    entryFrame.style.display = 'none';
});

socket.on('joined', ({ room, is_host }) => {
    currentRoom = room;
    isHost = is_host;
    showNotification(`Joined room: ${room}`);
    if (isHost) {
        hostRoomCode.textContent = room;
        hostControls.style.display = 'block';
    }
    entryFrame.style.display = 'none';
});

socket.on('question', ({ question, answers }) => {
    hasAnswered = false;
    quizArea.style.display = 'block';
    leaderboardDiv.style.display = 'none';
    feedbackDiv.innerHTML = '';
    questionText.textContent = question;
    answersDiv.innerHTML = '';
    answers.forEach((answer, i) => {
        const btn = document.createElement('button');
        btn.textContent = answer;
        btn.onclick = () => {
            if (hasAnswered || isHost) return;
            hasAnswered = true;
            socket.emit('answer', { room: currentRoom, index: i });
        };
        answersDiv.appendChild(btn);
    });
});

socket.on('answer_result', ({ correct }) => {
    feedbackDiv.textContent = correct ? "✅ Correct!" : "❌ Incorrect.";
});

socket.on('leaderboard', ({ players }) => {
    leaderboardList.innerHTML = '';
    players.forEach(player => {
        const li = document.createElement('li');
        li.textContent = `${player.name}: ${player.score}`;
        leaderboardList.appendChild(li);
    });
    if (isHost) {
        leaderboardDiv.style.display = 'block';
    } else {
        feedbackDiv.style.display = 'block';
    }
});

socket.on('quiz_end', () => {
    questionText.textContent = "Quiz Over!";
    answersDiv.innerHTML = '';
    feedbackDiv.innerHTML = '';
    leaderboardDiv.style.display = 'block';
});

const socket = io();

// Sound effects
const correctSound = new Audio('/static/sounds/correct.mp3');
const wrongSound = new Audio('/static/sounds/wrong.mp3');
const countdownSound = new Audio('/static/sounds/countdown.mp3');

// Notification system
function notify(message) {
    const container = document.getElementById('notificationContainer');
    const note = document.createElement('div');
    note.className = 'notification';
    note.innerHTML = `${message} <span class="close" onclick="this.parentElement.remove()">×</span>`;
    container.appendChild(note);
    setTimeout(() => {
        note.remove();
    }, 5000);
}

// Countdown timer
let countdownInterval;
function startCountdown(duration) {
    let timeLeft = duration;
    const timerDisplay = document.getElementById('timerDisplay');
    timerDisplay.innerText = `Time Left: ${timeLeft}s`;
    countdownSound.play();

    countdownInterval = setInterval(() => {
        timeLeft--;
        timerDisplay.innerText = `Time Left: ${timeLeft}s`;
        if (timeLeft <= 0) {
            clearInterval(countdownInterval);
            timerDisplay.innerText = 'Time\'s up!';
        }
    }, 1000);
}

// Confetti celebration
function launchConfetti() {
    // Simple confetti effect using emojis
    const confettiContainer = document.createElement('div');
    confettiContainer.className = 'confetti-container';
    document.body.appendChild(confettiContainer);

    for (let i = 0; i < 100; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.innerText = '🎉';
        confetti.style.left = Math.random() * 100 + 'vw';
        confetti.style.animationDelay = Math.random() * 2 + 's';
        confettiContainer.appendChild(confetti);
    }

    setTimeout(() => {
        confettiContainer.remove();
    }, 5000);
}

// Popup modal
function showPopup(title, message) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h2>${title}</h2>
            <p>${message}</p>
            <button onclick="this.parentElement.parentElement.remove()">Close</button>
        </div>
    `;
    document.body.appendChild(modal);
}

// Event listeners
document.getElementById('joinBtn').addEventListener('click', () => {
    const name = document.getElementById('nameInput').value.trim();
    const room = document.getElementById('roomInput').value.trim().toUpperCase();
    if (name && room) {
        socket.emit('join_room', { name, room });
    } else {
        notify('Please enter your name and room code.');
    }
});

document.getElementById('createBtn').addEventListener('click', () => {
    const name = document.getElementById('nameInput').value.trim();
    if (name) {
        socket.emit('create_room', { name });
    } else {
        notify('Please enter your name.');
    }
});

document.getElementById('startBtn').addEventListener('click', () => {
    socket.emit('start_quiz');
});

document.getElementById('skipBtn').addEventListener('click', () => {
    socket.emit('skip_question');
});

// Socket.io event handlers
socket.on('room_created', data => {
    document.getElementById('lobby').style.display = 'none';
    document.getElementById('hostControls').style.display = 'block';
    document.getElementById('hostRoomCode').innerText = data.room;
    notify(`Room ${data.room} created. Share the code with players.`);
});

socket.on('room_joined', data => {
    document.getElementById('lobby').style.display = 'none';
    document.getElementById('playerArea').style.display = 'block';
    notify(`Joined room ${data.room}.`);
});

socket.on('new_question', data => {
    document.getElementById('questionText').innerText = data.question;
    const answersDiv = document.getElementById('answers');
    answersDiv.innerHTML = '';
    data.answers.forEach((answer, index) => {
        const btn = document.createElement('button');
        btn.className = 'img-button';
        btn.innerText = answer;
        btn.addEventListener('click', () => {
            socket.emit('submit_answer', { answer: index });
        });
        answersDiv.appendChild(btn);
    });
    document.getElementById('feedback').innerText = '';
    startCountdown(data.time);
});

socket.on('answer_result', data => {
    const feedback = document.getElementById('feedback');
    if (data.correct) {
        feedback.innerText = 'Correct!';
        correctSound.play();
        launchConfetti();
    } else {
        feedback.innerText = 'Wrong!';
        wrongSound.play();
    }
});

socket.on('show_leaderboard', data => {
    const leaderboardList = document.getElementById('leaderboardList');
    leaderboardList.innerHTML = '';
    data.forEach(player => {
        const li = document.createElement('li');
        li.innerText = `${player.name}: ${player.score}`;
        leaderboardList.appendChild(li);
    });
    document.getElementById('leaderboardArea').style.display = 'block';
});

socket.on('game_over', data => {
    showPopup('Game Over', `The winner is ${data.winner.name} with ${data.winner.score} points!`);
});

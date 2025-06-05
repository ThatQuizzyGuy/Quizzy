const socket = io();

let currentRoom = "";
let isHost = false;

const nameInput = document.getElementById("nameInput");
const roomInput = document.getElementById("roomInput");
const createBtn = document.getElementById("createBtn");
const joinBtn = document.getElementById("joinBtn");
const startBtn = document.getElementById("startBtn");
const skipBtn = document.getElementById("skipBtn");
const nextBtn = document.getElementById("nextBtn");
const questionText = document.getElementById("questionText");
const answers = document.getElementById("answers");
const feedback = document.getElementById("feedback");
const timerDisplay = document.getElementById("timerDisplay");
const leaderboardArea = document.getElementById("leaderboardArea");
const leaderboardList = document.getElementById("leaderboardList");
const hostControls = document.getElementById("hostControls");
const questionContainer = document.getElementById("questionContainer");

function showNotification(message) {
  const box = document.getElementById("notificationBox");
  const text = document.getElementById("notificationText");
  text.innerText = message;
  box.classList.remove("hidden");
  playSound("notify");
}
function hideNotification() {
  document.getElementById("notificationBox").classList.add("hidden");
}

function playSound(name) {
  const audio = new Audio(`/static/sounds/${name}.mp3`);
  audio.play();
}

createBtn.onclick = () => {
  socket.emit("create_room", { name: nameInput.value });
};

joinBtn.onclick = () => {
  socket.emit("join_room", { name: nameInput.value, room: roomInput.value });
};

startBtn.onclick = () => socket.emit("start_quiz", { room: currentRoom });
skipBtn.onclick = () => socket.emit("skip_question", { room: currentRoom });
nextBtn.onclick = () => socket.emit("next_question", { room: currentRoom });

socket.on("room_created", (data) => {
  isHost = data.is_host;
  currentRoom = data.room;
  hostControls.style.display = "block";
  showNotification(`Room ${currentRoom} created`);
});

socket.on("room_joined", (data) => {
  isHost = data.is_host;
  currentRoom = data.room;
  showNotification(`Joined room ${currentRoom}`);
});

socket.on("new_question", (data) => {
  questionText.innerText = data.text;
  answers.innerHTML = "";
  data.answers.forEach((ans, idx) => {
    const btn = document.createElement("button");
    btn.innerText = ans;
    btn.onclick = () => socket.emit("answer", { room: currentRoom, answer: idx });
    answers.appendChild(btn);
  });
  feedback.innerText = "";
  questionContainer.style.display = "block";
  leaderboardArea.style.display = "none";
});

socket.on("answer_feedback", (data) => {
  feedback.innerText = data.correct ? "Correct!" : "Wrong!";
  playSound(data.correct ? "correct" : "wrong");
});

socket.on("show_leaderboard", (data) => {
  leaderboardList.innerHTML = "";
  data.board.forEach(p => {
    const li = document.createElement("li");
    li.innerText = `${p.name}: ${p.score}`;
    leaderboardList.appendChild(li);
  });
  leaderboardArea.style.display = isHost ? "block" : "none";
  questionContainer.style.display = isHost ? "none" : "block";
});

socket.on("timer_update", (data) => {
  timerDisplay.innerText = `Time left: ${data.time}`;
});

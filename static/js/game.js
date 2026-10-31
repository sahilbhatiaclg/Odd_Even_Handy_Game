const socket = io();
const roomId = document.body.dataset.room;
const $ = (id) => document.getElementById(id);
let mySelection = null, deadline = null, timerInterval = null, myPlayerId = null, latestState = null;

socket.on("connect", () => {
  const token = sessionStorage.getItem(`hc:${roomId}`);
  if (token) socket.emit("reconnect_player", {room_id: roomId, player_token: token});
});
socket.on("state_update", state => {
  latestState = state;
  $("players").innerHTML = state.players.map(p => `<div><strong>${escapeHtml(p.name)}</strong><br><small>${p.odd_even.toUpperCase()}</small></div>`).join("");
  $("phase").textContent = state.phase.replaceAll("_"," ");
  $("instruction").textContent = state.message;
  if (state.deadline) startLocalDisplay(state.deadline);
  else stopLocalDisplay();
  const choices = $("inningsChoices");
  choices.classList.toggle("hidden", state.phase !== "choose_innings");
  const gridOpen = ["toss","innings_1","innings_2"].includes(state.phase) && !!state.deadline;
  $("numberGrid").classList.toggle("hidden", !gridOpen);
  $("scoreboard").innerHTML = state.score ? Object.entries(state.score.scores).map(([id,score],i) =>
    `<div><small>PLAYER ${i+1}</small><div class="score">${score}</div></div>`).join("") : "";
});
socket.on("your_selection", ({number}) => {
  mySelection = number;
  document.querySelectorAll("[data-number]").forEach(b => b.classList.toggle("selected", Number(b.dataset.number) === number));
});
socket.on("round_reveal", result => {
  const nums = result.numbers ? Object.values(result.numbers).join("  vs  ") : "";
  $("reveal").textContent = result.phase === "toss"
    ? `Toss: ${nums} | Sum: ${result.sum} (${result.result}) | ${result.winner_name} won`
    : result.phase === "timeout"
      ? result.message
      : `${nums} — ${result.out ? "OUT!" : `${result.runs} run(s)`}`;
  mySelection = null;
  document.querySelectorAll("[data-number]").forEach(b => b.classList.remove("selected"));
});
socket.on("match_over", result => {
  $("reveal").textContent = result.message;
  $("instruction").textContent = "Match complete.";
});
socket.on("game_message", ({message}) => $("instruction").textContent = message);
socket.on("error_message", ({message}) => $("gameError").textContent = message);

document.querySelectorAll("[data-number]").forEach(button => {
  button.addEventListener("click", () => {
    if (!latestState || !latestState.deadline) return;
    mySelection = Number(button.dataset.number);
    document.querySelectorAll("[data-number]").forEach(b => b.classList.toggle("selected", b === button));
    socket.emit("select_number", {room_id: roomId, number: mySelection});
  });
});
document.querySelectorAll("[data-choice]").forEach(button => {
  button.addEventListener("click", () => socket.emit("choose_innings", {room_id: roomId, choice: button.dataset.choice}));
});
$("copyRoom").addEventListener("click", async () => {
  await navigator.clipboard.writeText(location.href);
  $("copyRoom").textContent = "Copied!";
});
function startLocalDisplay(serverDeadline) {
  deadline = serverDeadline;
  stopLocalDisplay();
  timerInterval = setInterval(() => {
    const remaining = Math.max(0, Math.ceil(deadline - Date.now()/1000));
    $("timerValue").textContent = remaining;
  }, 100);
}
function stopLocalDisplay() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
  $("timerValue").textContent = "--";
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

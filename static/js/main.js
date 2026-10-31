const socket = io();
const $ = (id) => document.getElementById(id);
let createdRoom = false;

$("createBtn").addEventListener("click", () => {
  socket.emit("create_room", {
    name: $("playerName").value || "Player 1",
    timer_seconds: Number($("timer").value || 10),
    odd_even: $("oddEven").value
  });
});
$("joinBtn").addEventListener("click", () => {
  const room_id = $("roomId").value.trim().toUpperCase();
  if (!room_id) { $("error").textContent = "Enter a room ID."; return; }
  socket.emit("join_room", { room_id, name: $("playerName").value || "Player 2" });
});
socket.on("room_created", ({room_id, player_token}) => {
  sessionStorage.setItem(`hc:${room_id}`, player_token);
  location.href = `/game/${room_id}`;
});
socket.on("joined_room", ({room_id, player_token}) => {
  sessionStorage.setItem(`hc:${room_id}`, player_token);
  location.href = `/game/${room_id}`;
});
socket.on("error_message", ({message}) => $("error").textContent = message);

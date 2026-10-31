const $ = (id) => document.getElementById(id);

function setStatus(text, bad = false) {
  $("status").textContent = text;
  $("status").classList.toggle("bad", bad);
}
function setButtons(enabled) {
  $("createBtn").disabled = !enabled;
  $("joinBtn").disabled = !enabled;
}

// If the socket.io client could not be loaded (offline / CDN blocked), say so clearly.
if (typeof io === "undefined") {
  setStatus("Could not load the Socket.IO client from cdn.socket.io. Check your internet connection and reload.", true);
} else {
  const socket = io();
  let waiting = null;

  // Invite links look like /?room=ABC123
  const invited = new URLSearchParams(location.search).get("room");
  if (invited) $("roomId").value = invited.toUpperCase().slice(0, 6);
  $("roomId").addEventListener("input", (e) => { e.target.value = e.target.value.toUpperCase(); });

  function request(event, payload) {
    $("error").textContent = "";
    setButtons(false);
    socket.emit(event, payload);
    clearTimeout(waiting);
    waiting = setTimeout(() => {
      $("error").textContent = "The server did not reply. Is it still running?";
      setButtons(socket.connected);
    }, 6000);
  }

  socket.on("connect", () => { setStatus("Connected. Ready to play."); setButtons(true); });
  socket.on("disconnect", () => { setStatus("Connection lost. Trying to reconnect...", true); setButtons(false); });
  socket.on("connect_error", () => {
    setStatus("Cannot reach the game server. Make sure `python app.py` is running, then reload.", true);
    setButtons(false);
  });

  $("createBtn").addEventListener("click", () => {
    const timer = Math.max(5, Math.min(60, parseInt($("timer").value, 10) || 10));
    $("timer").value = timer;
    request("create_room", {
      name: $("playerName").value.trim() || "Player 1",
      timer_seconds: timer,
      odd_even: $("oddEven").value,
    });
  });

  $("joinBtn").addEventListener("click", () => {
    const room_id = $("roomId").value.trim().toUpperCase();
    if (!room_id) { $("error").textContent = "Enter a room ID."; return; }
    request("join_room", { room_id, name: $("playerName").value.trim() || "Player 2" });
  });

  function enterRoom({ room_id, player_token }) {
    clearTimeout(waiting);
    sessionStorage.setItem(`hc:${room_id}`, player_token);
    location.href = `/game/${room_id}`;
  }
  socket.on("room_created", enterRoom);
  socket.on("joined_room", enterRoom);
  socket.on("error_message", ({ message }) => {
    clearTimeout(waiting);
    $("error").textContent = message;
    setButtons(true);
  });
}
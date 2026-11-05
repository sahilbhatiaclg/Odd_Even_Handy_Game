(function () {
  const $ = (id) => document.getElementById(id);
  const roomId = document.body.dataset.room;
  const token = sessionStorage.getItem(`hc:${roomId}`);

  // Connection messages go in a banner at the TOP of the card so they can't be missed.
  function showBanner(message, withRetry = false) {
    $("connectionBanner").textContent = message || "";
    $("connectionBanner").classList.toggle("hidden", !message);
    $("retryBtn").classList.toggle("hidden", !(message && withRetry));
  }
  // Any unexpected script error is shown instead of leaving the page stuck on "Connecting...".
  window.addEventListener("error", (e) => showBanner(`Page error: ${e.message}`));

  // Opened an invite link (or a new tab) with no player session: go to the join form.
  if (!token) { location.replace(`/?room=${roomId}`); return; }
  if (typeof io === "undefined") {
    showBanner("Could not load the Socket.IO client. Check static/js/socket.io.min.js exists, or your internet connection, then reload.");
    return;
  }

  const socket = io(); // default transports and unlimited reconnect attempts are the most reliable
  let me = null;            // 0 or 1: which player this browser is
  let state = null;         // latest public state from the server
  let lastRound = -1;
  let localDeadline = null; // only used to draw the countdown; the server decides the real deadline
  let tick = null;
  let joined = false, joinTimer = null, joinTries = 0;

  const PHASES = {
    waiting: "Waiting for players", toss: "Toss", choose_innings: "Toss decision",
    innings_1: "First innings", innings_2: "Second innings", finished: "Match over",
  };

  // Tell the server which player this socket is. Repeats until the server answers,
  // so one lost message can never leave the page stuck.
  function joinRoom() {
    joined = false;
    clearTimeout(joinTimer);
    socket.emit("reconnect_player", { room_id: roomId, player_token: token });
    joinTimer = setTimeout(() => {
      if (joined || !socket.connected) return;
      if (++joinTries >= 3) showBanner("Connected, but the server is not answering. Is it still running?", true);
      joinRoom();
    }, 3000);
  }

  // Still not connected after 5 seconds? Say so.
  setTimeout(() => { if (!socket.connected) showBanner("Still trying to reach the game server...", true); }, 5000);

  // ---------------------------------------------------------- socket events
  socket.on("connect", () => { joinTries = 0; joinRoom(); });
  socket.on("connect_error", (err) =>
    showBanner(`Cannot reach the game server (${err.message}). Make sure python app.py is running.`, true));
  socket.on("disconnect", () => showBanner("Connection lost. Reconnecting...", true));
  socket.on("reconnected", ({ you }) => { joined = true; clearTimeout(joinTimer); showBanner(""); me = you; render(); });

  socket.on("state_update", (s) => {
    if (s.round_no !== lastRound) { lastRound = s.round_no; clearSelection(); }
    state = s;
    render();
  });

  socket.on("your_selection", ({ number }) => {
    markSelected(number);
    $("selectionStatus").textContent = `You picked ${number}. You can change it until time runs out.`;
  });

  socket.on("round_reveal", showReveal);
  socket.on("match_over", (r) => {
    const scores = r.scores.map((p) => `${esc(p.name)}: ${p.score}`).join(" &nbsp;|&nbsp; ");
    $("reveal").innerHTML += `<p class="verdict win">${esc(r.message)}</p><p>${scores}</p>`;
  });

  socket.on("error_message", ({ message, code }) => {
    $("gameError").textContent = message;
    if (code === "session_invalid") {
      joined = true; clearTimeout(joinTimer);
      sessionStorage.removeItem(`hc:${roomId}`);
      $("instruction").textContent = "This room is no longer available. Go back and create or join a new one.";
    }
  });

  $("retryBtn").addEventListener("click", () => {
    showBanner("Retrying...");
    if (socket.connected) joinRoom(); else socket.connect();
  });

  // ---------------------------------------------------------------- inputs
  document.querySelectorAll("[data-number]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!state || state.seconds_left === null) return;
      $("gameError").textContent = "";
      socket.emit("select_number", { room_id: roomId, number: Number(button.dataset.number) });
    });
  });
  document.querySelectorAll("[data-choice]").forEach((button) => {
    button.addEventListener("click", () => {
      $("gameError").textContent = "";
      socket.emit("choose_innings", { room_id: roomId, choice: button.dataset.choice });
    });
  });
  $("leaveBtn").addEventListener("click", () => { location.href = "/"; });

  // ------------------------------------------------------------- rendering
  function render() {
    if (!state) return;
    const open = state.seconds_left !== null && ["toss", "innings_1", "innings_2"].includes(state.phase);

    $("phase").textContent = PHASES[state.phase] || state.phase;
    $("target").textContent = state.score && state.score.target ? `Target: ${state.score.target}` : "";
    $("notice").textContent = state.notice || "";
    renderPlayers();
    $("instruction").textContent = instructionText(open);
    const waitingOnOther = state.phase === "choose_innings" && state.toss_winner !== me;
    $("waitDots").classList.toggle("hidden", !(state.phase === "waiting" || waitingOnOther));

    $("numberGrid").classList.toggle("hidden", !open);
    if (!open) $("selectionStatus").textContent = "";
    else if (!document.querySelector("[data-number].selected")) $("selectionStatus").textContent = "Pick a number. You can change it until time runs out.";

    const myTossDecision = state.phase === "choose_innings" && state.toss_winner === me;
    $("inningsChoices").classList.toggle("hidden", !myTossDecision);

    if (open) startCountdown(state.seconds_left); else stopCountdown();
  }

  function renderPlayers() {
    const list = state.score ? state.score.players : state.players.map((p) => ({ name: p.name, score: 0, role: null }));
    $("scoreboard").innerHTML = list.map((p, i) => {
      const info = state.players[i] || {};
      const role = p.role ? `<span class="role ${p.role}">${p.role === "bat" ? "Batting" : "Bowling"}</span>` : "";
      const tag = `${(info.odd_even || "").toUpperCase()}${i === me ? " - YOU" : ""}`;
      return `<div class="player ${info.connected === false ? "off" : ""}">
        <div class="pname"><span class="nametag p${i}">${esc(p.name)}</span></div><div class="tag">${tag}</div>
        <div class="score">${p.score}</div>${role}</div>`;
    }).join("");
  }

  function instructionText(open) {
    const me_ = state.score && state.score.players[me];
    if (state.phase === "choose_innings") {
      const winner = state.players[state.toss_winner];
      return state.toss_winner === me ? "You won the toss! Bat or bowl first?" : `${winner ? winner.name : "The winner"} is choosing bat or bowl...`;
    }
    if (open && me_ && me_.role) return me_.role === "bat" ? "You are BATTING. Pick a number!" : "You are BOWLING. Match the batsman to get him out!";
    if (state.phase.startsWith("innings") && !open) return "Next ball coming up...";
    return state.message;
  }

  function showReveal(r) {
    const pick = (name, n, label) => `<div class="pick"><small>${esc(label || name)}</small><b>${n}</b></div>`;
    let html = "";
    if (r.kind === "toss") {
      html = `<div class="picks">${r.numbers.map((p) => pick(p.name, p.number)).join("")}</div><p class="verdict">${esc(r.message)}</p>`;
    } else if (r.kind === "ball") {
      html = `<div class="picks">${pick(r.batsman.name, r.batsman.number, `${r.batsman.name} (bat)`)}${pick(r.bowler.name, r.bowler.number, `${r.bowler.name} (bowl)`)}</div>` +
        (r.out ? `<p class="verdict out">OUT!</p><p>${esc(r.message)}</p>` : `<p class="verdict">+${r.runs} run${r.runs === 1 ? "" : "s"}. ${esc(r.message)}</p>`);
    } else {
      html = `<p class="verdict out">Time's up!</p><p>${esc(r.message)}</p>`;
    }
    $("reveal").innerHTML = html;
    clearSelection();
  }

  // ----------------------------------------------------------- selection UI
  function markSelected(number) {
    document.querySelectorAll("[data-number]").forEach((b) => b.classList.toggle("selected", Number(b.dataset.number) === number));
  }
  function clearSelection() {
    markSelected(null);
    $("selectionStatus").textContent = "";
  }

  // ------------------------------------------------------------- countdown
  // The server sends "seconds_left" (its own clock), so the visible timer is right even if
  // this computer's clock is off. It is display only: the server decides when the round ends.
  function startCountdown(secondsLeft) {
    localDeadline = Date.now() + secondsLeft * 1000;
    if (tick) clearInterval(tick);
    const draw = () => {
      const remaining = Math.max(0, Math.ceil((localDeadline - Date.now()) / 1000));
      $("timerValue").textContent = remaining;
      $("timerValue").classList.toggle("low", remaining <= 3);
    };
    draw();
    tick = setInterval(draw, 100);
  }
  function stopCountdown() {
    if (tick) clearInterval(tick);
    tick = null;
    $("timerValue").textContent = "--";
    $("timerValue").classList.remove("low");
  }

  function esc(value) {
    return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
})();
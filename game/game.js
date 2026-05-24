// ============================================================
// Edge Wars — 2-player hot-seat prototype
// ============================================================

const GRID = 6;                 // 6x6 squares -> 7x7 points
const POINTS = GRID + 1;
const PLACE_COUNT = 4;          // edges each player places
const DICE_MIN = 1;
const DICE_MAX = 6;

function rollDice() {
  return Math.floor(Math.random() * (DICE_MAX - DICE_MIN + 1)) + DICE_MIN;
}

const canvas = document.getElementById('board');
const ctx = canvas.getContext('2d');

const statusEl = document.getElementById('status');
const countsEl = document.getElementById('counts');
const readyBtn = document.getElementById('ready-btn');
const endTurnBtn = document.getElementById('endturn-btn');
const endGameBtn = document.getElementById('endgame-btn');
const resetBtn = document.getElementById('reset-btn');

// Colors
const COL_GRID = '#2a313c';
const COL_DIVIDER = '#3a4250';
const COL_POINT = '#4a5260';
const COL_P1 = '#ff6b6b';
const COL_P2 = '#4dabf7';
const COL_GHOST = 'rgba(255,255,255,0.18)';
const COL_SELECT = '#f7c948';
const COL_VALID = 'rgba(247,201,72,0.35)';
const COL_HALF_P1 = 'rgba(255,107,107,0.04)';
const COL_HALF_P2 = 'rgba(77,171,247,0.04)';

// Canvas geometry
function computeGeometry() {
  const size = Math.min(canvas.width, canvas.height);
  const padding = 30;
  const cell = (size - padding * 2) / GRID;
  return { padding, cell, size };
}

function gridToPx(gx, gy) {
  const { padding, cell } = computeGeometry();
  return { x: padding + gx * cell, y: padding + gy * cell };
}

function pxToGrid(px, py) {
  const { padding, cell } = computeGeometry();
  return { x: (px - padding) / cell, y: (py - padding) / cell };
}

// ============================================================
// Edge model
// ============================================================
// An edge is { id, player: 1|2, a:{x,y}, b:{x,y} } with canonical (a,b) ordering.

function canonical(a, b) {
  if (a.y < b.y || (a.y === b.y && a.x < b.x)) return [a, b];
  return [b, a];
}
function key(a, b) {
  const [p, q] = canonical(a, b);
  return `${p.x},${p.y}-${q.x},${q.y}`;
}
function pointEq(a, b) { return a.x === b.x && a.y === b.y; }

function inGrid(p) {
  return p.x >= 0 && p.x <= GRID && p.y >= 0 && p.y <= GRID;
}

// 8 king-move neighbors that form a valid unit edge.
function neighbors(p) {
  const out = [];
  for (let dx = -1; dx <= 1; dx++) {
    for (let dy = -1; dy <= 1; dy++) {
      if (dx === 0 && dy === 0) continue;
      const q = { x: p.x + dx, y: p.y + dy };
      if (inGrid(q)) out.push(q);
    }
  }
  return out;
}

// All valid unit-edge slots on the grid.
function allSlots() {
  const seen = new Set();
  const slots = [];
  for (let x = 0; x <= GRID; x++) {
    for (let y = 0; y <= GRID; y++) {
      const p = { x, y };
      for (const q of neighbors(p)) {
        const k = key(p, q);
        if (!seen.has(k)) {
          seen.add(k);
          const [a, b] = canonical(p, q);
          slots.push({ a, b, key: k });
        }
      }
    }
  }
  return slots;
}
const ALL_SLOTS = allSlots();

// ============================================================
// Game state
// ============================================================
let state;

function newGame() {
  state = {
    phase: 'setup-p1',        // setup-p1 | setup-p2 | play | gameover
    edges: [],                // {id, player, a, b}
    nextId: 1,
    currentPlayer: 1,
    dice: 0,                  // dice value rolled at start of this turn
    movesLeft: 0,             // moves remaining in the current turn
    selectedId: null,
    hover: null,              // {a,b} of the nearest slot under cursor (during setup)
    message: '',
  };
  render();
  updateUI();
}

function edgeAt(slot) {
  const k = key(slot.a, slot.b);
  return state.edges.find(e => key(e.a, e.b) === k);
}

function playerHalfOk(slot, player) {
  const my = (slot.a.y + slot.b.y) / 2;
  if (player === 1) return my < GRID / 2;
  return my > GRID / 2;
}

function placedCount(player) {
  return state.edges.filter(e => e.player === player).length;
}

// ============================================================
// Hit testing: find nearest slot to mouse
// ============================================================
function nearestSlot(mx, my) {
  const { cell } = computeGeometry();
  // Convert to grid space and find slot whose midpoint is closest.
  let best = null, bestD = Infinity;
  for (const s of ALL_SLOTS) {
    const m = gridToPx((s.a.x + s.b.x) / 2, (s.a.y + s.b.y) / 2);
    const dx = m.x - mx, dy = m.y - my;
    const d = dx * dx + dy * dy;
    if (d < bestD) { bestD = d; best = s; }
  }
  // Reject if too far (more than half a cell).
  if (Math.sqrt(bestD) > cell * 0.55) return null;
  return best;
}

// ============================================================
// Movement
// ============================================================
// Valid destinations for an edge owned by `player`: slots that share at least
// one endpoint with the current edge, are not the current slot, and are not
// occupied by one of the player's own edges.
function validMoves(edge) {
  const results = [];
  const seen = new Set();
  const cur = key(edge.a, edge.b);
  for (const pivot of [edge.a, edge.b]) {
    for (const q of neighbors(pivot)) {
      if (pointEq(q, edge.a) || pointEq(q, edge.b)) {
        // Either same edge (skip) or other endpoint (would give zero-length).
        // The "other endpoint" check skips reusing the same slot.
      }
      const [a, b] = canonical(pivot, q);
      const k = key(a, b);
      if (k === cur) continue;
      if (seen.has(k)) continue;
      seen.add(k);
      const target = state.edges.find(e => key(e.a, e.b) === k);
      if (target && target.player === edge.player) continue;
      results.push({ a, b, key: k, capture: target ? target : null });
    }
  }
  return results;
}

// ============================================================
// Rendering
// ============================================================
function render() {
  const { padding, cell, size } = computeGeometry();
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Player half tinting
  ctx.fillStyle = COL_HALF_P1;
  ctx.fillRect(padding, padding, GRID * cell, (GRID / 2) * cell);
  ctx.fillStyle = COL_HALF_P2;
  ctx.fillRect(padding, padding + (GRID / 2) * cell, GRID * cell, (GRID / 2) * cell);

  // Grid lines (square sides only — diagonals are implied)
  ctx.strokeStyle = COL_GRID;
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= GRID; i++) {
    const a = gridToPx(0, i), b = gridToPx(GRID, i);
    ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
    const c = gridToPx(i, 0), d = gridToPx(i, GRID);
    ctx.moveTo(c.x, c.y); ctx.lineTo(c.x, d.y);
  }
  ctx.stroke();

  // Diagonals (faint, to make valid placements obvious)
  ctx.strokeStyle = 'rgba(74,82,96,0.35)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 0; x < GRID; x++) {
    for (let y = 0; y < GRID; y++) {
      const a = gridToPx(x, y), b = gridToPx(x + 1, y + 1);
      const c = gridToPx(x + 1, y), d = gridToPx(x, y + 1);
      ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
      ctx.moveTo(c.x, c.y); ctx.lineTo(d.x, d.y);
    }
  }
  ctx.stroke();

  // Midline divider
  ctx.strokeStyle = COL_DIVIDER;
  ctx.lineWidth = 2;
  ctx.beginPath();
  const m1 = gridToPx(0, GRID / 2);
  const m2 = gridToPx(GRID, GRID / 2);
  ctx.moveTo(m1.x, m1.y); ctx.lineTo(m2.x, m2.y);
  ctx.stroke();

  // Grid points
  ctx.fillStyle = COL_POINT;
  for (let x = 0; x <= GRID; x++) {
    for (let y = 0; y <= GRID; y++) {
      const p = gridToPx(x, y);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // Edges — respect hidden state during setup-p2
  for (const e of state.edges) {
    const hide = state.phase === 'setup-p2' && e.player === 1;
    if (hide) continue;
    drawEdge(e.a, e.b, e.player === 1 ? COL_P1 : COL_P2);
  }

  // Selected edge highlight
  if (state.selectedId != null) {
    const e = state.edges.find(x => x.id === state.selectedId);
    if (e) drawEdge(e.a, e.b, COL_SELECT, 6);
  }

  // Valid moves preview during play
  if (state.phase === 'play' && state.selectedId != null) {
    const e = state.edges.find(x => x.id === state.selectedId);
    if (e) {
      for (const v of validMoves(e)) {
        drawEdge(v.a, v.b, v.capture ? 'rgba(255,107,107,0.55)' : COL_VALID, 5);
      }
    }
  }

  // Hover ghost during setup
  if ((state.phase === 'setup-p1' || state.phase === 'setup-p2') && state.hover) {
    const taken = edgeAt(state.hover);
    const player = state.phase === 'setup-p1' ? 1 : 2;
    const ok = !taken && playerHalfOk(state.hover, player) && placedCount(player) < PLACE_COUNT;
    drawEdge(state.hover.a, state.hover.b, ok ? COL_GHOST : 'rgba(255,80,80,0.25)', 5);
  }
}

function drawEdge(a, b, color, width = 5) {
  const pa = gridToPx(a.x, a.y);
  const pb = gridToPx(b.x, b.y);
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(pa.x, pa.y);
  ctx.lineTo(pb.x, pb.y);
  ctx.stroke();

  // Endpoint dots
  ctx.fillStyle = color;
  for (const p of [pa, pb]) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, width / 2 + 0.5, 0, Math.PI * 2);
    ctx.fill();
  }
}

// ============================================================
// UI updates
// ============================================================
function updateUI() {
  const p1Count = placedCount(1);
  const p2Count = placedCount(2);
  countsEl.innerHTML = `<span class="p1">P1: ${p1Count}</span><span class="p2">P2: ${p2Count}</span>`;

  switch (state.phase) {
    case 'setup-p1':
      statusEl.textContent = `Player 1 — place edges on the TOP half (${p1Count}/${PLACE_COUNT}).`;
      readyBtn.disabled = p1Count !== PLACE_COUNT;
      readyBtn.textContent = 'Ready (pass phone)';
      endTurnBtn.disabled = true;
      break;
    case 'setup-p2':
      statusEl.textContent = `Player 2 — place edges on the BOTTOM half (${p2Count}/${PLACE_COUNT}). P1's edges are hidden.`;
      readyBtn.disabled = p2Count !== PLACE_COUNT;
      readyBtn.textContent = 'Ready (start game)';
      endTurnBtn.disabled = true;
      break;
    case 'play': {
      const who = state.currentPlayer;
      statusEl.textContent = `Player ${who}'s turn — rolled ${state.dice}, moves left: ${state.movesLeft}. Click your edge, then a highlighted destination.`;
      readyBtn.disabled = true;
      readyBtn.textContent = 'Ready';
      endTurnBtn.disabled = false;
      break;
    }
    case 'gameover': {
      const winner = p1Count === p2Count ? 'Draw!' :
                     p1Count > p2Count   ? 'Player 1 wins!' : 'Player 2 wins!';
      statusEl.textContent = `Game over — ${winner} (P1: ${p1Count}, P2: ${p2Count})`;
      readyBtn.disabled = true;
      endTurnBtn.disabled = true;
      break;
    }
  }
}

// ============================================================
// Input handling
// ============================================================
function eventToCanvas(ev) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const cx = (ev.clientX - rect.left) * scaleX;
  const cy = (ev.clientY - rect.top) * scaleY;
  return { x: cx, y: cy };
}

canvas.addEventListener('mousemove', (ev) => {
  const { x, y } = eventToCanvas(ev);
  if (state.phase === 'setup-p1' || state.phase === 'setup-p2') {
    state.hover = nearestSlot(x, y);
    render();
  }
});

canvas.addEventListener('mouseleave', () => {
  if (state.hover) { state.hover = null; render(); }
});

canvas.addEventListener('click', (ev) => {
  const { x, y } = eventToCanvas(ev);
  onClick(x, y);
});

function onClick(mx, my) {
  if (state.phase === 'setup-p1' || state.phase === 'setup-p2') {
    handleSetupClick(mx, my);
  } else if (state.phase === 'play') {
    handlePlayClick(mx, my);
  }
}

function handleSetupClick(mx, my) {
  const slot = nearestSlot(mx, my);
  if (!slot) return;

  const player = state.phase === 'setup-p1' ? 1 : 2;
  const existing = edgeAt(slot);

  // Toggle: if it's one of your own, remove it (lets player fix mistakes).
  if (existing && existing.player === player) {
    state.edges = state.edges.filter(e => e.id !== existing.id);
    render();
    updateUI();
    return;
  }

  if (existing) return; // occupied by other player — shouldn't happen given halves, but guard.
  if (!playerHalfOk(slot, player)) return;
  if (placedCount(player) >= PLACE_COUNT) return;

  state.edges.push({
    id: state.nextId++,
    player,
    a: slot.a,
    b: slot.b,
  });
  render();
  updateUI();
}

function handlePlayClick(mx, my) {
  const slot = nearestSlot(mx, my);
  if (!slot) return;
  const clicked = edgeAt(slot);

  // If nothing selected yet — must click your own edge.
  if (state.selectedId == null) {
    if (clicked && clicked.player === state.currentPlayer) {
      state.selectedId = clicked.id;
      render();
    }
    return;
  }

  const sel = state.edges.find(e => e.id === state.selectedId);
  if (!sel) { state.selectedId = null; render(); return; }

  // Reselect: clicked another of your own pieces.
  if (clicked && clicked.player === state.currentPlayer && clicked.id !== sel.id) {
    state.selectedId = clicked.id;
    render();
    return;
  }

  // Deselect: clicked the same selected piece.
  if (clicked && clicked.id === sel.id) {
    state.selectedId = null;
    render();
    return;
  }

  // Attempt move
  const moves = validMoves(sel);
  const target = moves.find(m => m.key === key(slot.a, slot.b));
  if (!target) return;

  if (target.capture) {
    state.edges = state.edges.filter(e => e.id !== target.capture.id);
  }
  sel.a = target.a;
  sel.b = target.b;
  state.movesLeft -= 1;
  state.selectedId = null;

  // Check elimination
  if (placedCount(1) === 0 || placedCount(2) === 0) {
    state.phase = 'gameover';
    render();
    updateUI();
    return;
  }

  if (state.movesLeft <= 0) {
    nextTurn();
  }
  render();
  updateUI();
}

function nextTurn() {
  state.currentPlayer = state.currentPlayer === 1 ? 2 : 1;
  state.dice = rollDice();
  state.movesLeft = state.dice;
  state.selectedId = null;
}

// ============================================================
// Buttons
// ============================================================
readyBtn.addEventListener('click', () => {
  if (state.phase === 'setup-p1' && placedCount(1) === PLACE_COUNT) {
    state.phase = 'setup-p2';
    state.hover = null;
    render();
    updateUI();
  } else if (state.phase === 'setup-p2' && placedCount(2) === PLACE_COUNT) {
    state.phase = 'play';
    state.currentPlayer = 1;
    state.dice = rollDice();
    state.movesLeft = state.dice;
    state.hover = null;
    state.selectedId = null;
    render();
    updateUI();
  }
});

endTurnBtn.addEventListener('click', () => {
  if (state.phase !== 'play') return;
  nextTurn();
  render();
  updateUI();
});

endGameBtn.addEventListener('click', () => {
  if (state.phase === 'gameover') return;
  if (!confirm('End the game now? Player with the most edges wins.')) return;
  state.phase = 'gameover';
  state.selectedId = null;
  render();
  updateUI();
});

resetBtn.addEventListener('click', () => {
  if (!confirm('Reset the game?')) return;
  newGame();
});

// Boot
newGame();

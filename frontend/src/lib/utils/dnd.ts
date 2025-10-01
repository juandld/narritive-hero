export function createDragGhost(text: string, emoji = '🎵') {
  const ghost = document.createElement('div');
  ghost.style.cssText = [
    'position:fixed',
    'top:-1000px',
    'left:-1000px',
    'padding:10px 14px',
    'background:#111',
    'color:#fff',
    'border-radius:9999px',
    'font-size:16px',
    'font-weight:700',
    'letter-spacing:.3px',
    'box-shadow:0 8px 20px rgba(0,0,0,0.35)',
    'border:2px solid rgba(255,255,255,0.85)',
    'display:flex',
    'align-items:center',
    'gap:8px',
  ].join(';');
  const icon = document.createElement('span');
  icon.textContent = emoji;
  const txt = document.createElement('span');
  txt.textContent = text;
  ghost.appendChild(icon);
  ghost.appendChild(txt);
  document.body.appendChild(ghost);
  return ghost;
}


export type PageDropOptions = {
  onFiles: (files: File[]) => void;
  overlayText?: string;
  accept?: RegExp | ((f: File) => boolean);
};

function defaultAccept(f: File): boolean {
  return (f.type && f.type.startsWith('audio/')) || /\.(wav|mp3|ogg|m4a|webm)$/i.test(f.name);
}

export function pageDrop(node: HTMLElement, options: PageDropOptions) {
  let depth = 0;
  let overlay: HTMLDivElement | null = null;
  const accept = options.accept || defaultAccept;
  const text = options.overlayText || 'Drop audio files to upload';

  function hasFiles(e: DragEvent): boolean {
    return !!e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files');
  }

  function ensureOverlay() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.style.position = 'fixed';
    overlay.style.inset = '0';
    overlay.style.background = 'rgba(59,130,246,0.06)';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';
    overlay.style.zIndex = '999';
    overlay.style.pointerEvents = 'none';
    const box = document.createElement('div');
    box.textContent = text;
    box.style.border = '2px dashed #3B82F6';
    box.style.color = '#1f2937';
    box.style.background = '#fff';
    box.style.padding = '1rem 1.25rem';
    box.style.borderRadius = '12px';
    box.style.boxShadow = '0 10px 30px rgba(0,0,0,0.15)';
    box.style.fontWeight = '600';
    overlay.appendChild(box);
    document.body.appendChild(overlay);
  }

  function hideOverlay() {
    if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
    overlay = null;
  }

  function onDragEnter(e: DragEvent) {
    if (!hasFiles(e)) return;
    depth += 1;
    ensureOverlay();
  }
  function onDragOver(e: DragEvent) {
    if (!hasFiles(e)) return;
    e.preventDefault();
  }
  function onDragLeave(e: DragEvent) {
    if (!hasFiles(e)) return;
    depth = Math.max(0, depth - 1);
    if (depth === 0) hideOverlay();
  }
  function onDrop(e: DragEvent) {
    if (!hasFiles(e)) return;
    e.preventDefault();
    depth = 0;
    hideOverlay();
    const dt = e.dataTransfer;
    if (!dt) return;
    const files = Array.from(dt.files || []).filter((f) => (accept instanceof RegExp ? accept.test(f.name) : accept(f)));
    if (files.length) options.onFiles(files);
  }

  node.addEventListener('dragenter', onDragEnter);
  node.addEventListener('dragover', onDragOver);
  node.addEventListener('dragleave', onDragLeave);
  node.addEventListener('drop', onDrop);

  return {
    destroy() {
      node.removeEventListener('dragenter', onDragEnter);
      node.removeEventListener('dragover', onDragOver);
      node.removeEventListener('dragleave', onDragLeave);
      node.removeEventListener('drop', onDrop);
      hideOverlay();
    },
  };
}


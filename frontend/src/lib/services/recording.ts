export async function getLocation(): Promise<string> {
  return new Promise((resolve, reject) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      reject(new Error('Geolocation is not supported by this browser.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const place = `Lat: ${position.coords.latitude}, Lon: ${position.coords.longitude}`;
        resolve(place);
      },
      (error) => {
        reject(new Error('Could not get your location.'));
      }
    );
  });
}

export type Recorder = {
  mediaRecorder: MediaRecorder;
  stream: MediaStream;
};

export async function start(onStop: (blob: Blob) => void): Promise<Recorder> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream);
  const chunks: BlobPart[] = [];
  mediaRecorder.ondataavailable = (event) => { if (event.data) chunks.push(event.data); };
  mediaRecorder.onstop = async () => {
    const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
    try { stream.getTracks().forEach((track) => track.stop()); } catch {}
    try { onStop(blob); } catch (e) { console.error('Error in onStop callback:', e); }
  };
  mediaRecorder.start();
  return { mediaRecorder, stream };
}

export function stop(rec: Recorder | MediaRecorder | null | undefined) {
  try {
    if (!rec) return;
    const mr = (rec as Recorder).mediaRecorder ? (rec as Recorder).mediaRecorder : (rec as MediaRecorder);
    const stream = (rec as Recorder).stream;
    mr.stop();
    if (stream) {
      try { stream.getTracks().forEach((track) => track.stop()); } catch {}
    }
  } catch (e) {
    console.error('Error stopping recorder:', e);
  }
}

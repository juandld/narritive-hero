import { writable } from 'svelte/store';
import { getLocation as recGetLocation, start as recStart, stop as recStop, type Recorder as Rec } from '$lib/services/recording';
import { uploadBlob as uploadsUploadBlob } from '$lib/services/uploads';

export const includeDate = writable<boolean>(true);
export const includePlace = writable<boolean>(false);
export const isRecording = writable<boolean>(false);
export const showPlacePrompt = writable<boolean>(false);
export const detectedPlace = writable<string>('');

let recorder: Rec | null = null;

export const uiAppActions = {
  async startRecording() {
    if (recorder !== null) {
      console.warn('Recording already in progress');
      return;
    }
    try {
      const needsPlace = getVal(includePlace);
      if (needsPlace) {
        try {
          const place = await recGetLocation();
          detectedPlace.set(place);
          showPlacePrompt.set(true);
        } catch {}
      }
      recorder = await recStart(async (blob) => {
        try {
          await uploadsUploadBlob(blob);
        } catch (error) {
          console.error('Failed to upload blob:', error);
        }
      });
      isRecording.set(true);
    } catch (e) {
      console.error('Failed to start recording:', e);
    }
  },
  stopRecording() {
    try { recStop(recorder); } catch (e) { console.error('Failed to stop recording:', e); }
    isRecording.set(false);
    recorder = null;
  },
  setIncludePlace(val: boolean){ includePlace.set(val); },
  setIncludeDate(val: boolean){ includeDate.set(val); },
};

function getVal<T>(store: { subscribe: (run: (v: T)=>void) => any }): T {
  let v!: T; const unsub = store.subscribe((x)=> v = x); unsub && (unsub as any)(); return v;
}

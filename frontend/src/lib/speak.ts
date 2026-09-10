// Voice output for Re:Route AI — "Read aloud".
//
// Calls the backend /api/voice/speak, which returns an MP3 from Amazon Polly
// when Polly is enabled, or HTTP 204 to signal "use the browser voice instead".
// So voice always works: Polly (neural) live, browser speechSynthesis as
// fallback. A tiny controller exposes speak()/stop() and an onEnd callback so a
// button can reflect play/stop state.

const API_ROOT = (import.meta.env?.VITE_API_BASE || '').replace(/\/$/, '');
const BASE = API_ROOT ? `${API_ROOT}/api` : '/api';

export interface VoiceConfig {
  polly_available: boolean;
  provider: string;
  voices: { id: string; label: string; engine: string; lang: string }[];
  default_voice: string;
  region: string;
}

export async function getVoiceConfig(): Promise<VoiceConfig | null> {
  try {
    const res = await fetch(`${BASE}/voice/config`);
    if (!res.ok) return null;
    return (await res.json()) as VoiceConfig;
  } catch {
    return null;
  }
}

let currentAudio: HTMLAudioElement | null = null;

/** Stop any in-progress speech (Polly audio or browser synthesis). */
export function stopSpeaking() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.src = '';
    currentAudio = null;
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
}

/**
 * Speak the given text. Tries Amazon Polly first; on 204 (or any failure) falls
 * back to the browser's speechSynthesis. Resolves the provider used, or null if
 * nothing could speak. `onEnd` fires when playback finishes or is stopped.
 */
export async function speak(
  text: string,
  opts: { voiceId?: string; onEnd?: () => void } = {},
): Promise<'amazon-polly' | 'browser' | null> {
  const clean = (text || '').trim();
  if (!clean) return null;
  stopSpeaking();

  // 1) Amazon Polly (MP3 bytes) when available.
  try {
    const res = await fetch(`${BASE}/voice/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: clean, voice_id: opts.voiceId }),
    });
    if (res.ok && res.status !== 204) {
      const blob = await res.blob();
      if (blob.size > 0) {
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        currentAudio = audio;
        audio.onended = () => {
          URL.revokeObjectURL(url);
          currentAudio = null;
          opts.onEnd?.();
        };
        await audio.play();
        return 'amazon-polly';
      }
    }
  } catch {
    /* fall through to browser TTS */
  }

  // 2) Browser speechSynthesis fallback.
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    const u = new SpeechSynthesisUtterance(clean);
    u.onend = () => opts.onEnd?.();
    window.speechSynthesis.speak(u);
    return 'browser';
  }

  opts.onEnd?.();
  return null;
}

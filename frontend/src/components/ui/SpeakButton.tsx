// "Read aloud" button — plays text via Amazon Polly (neural voice) with a
// browser speech-synthesis fallback. Toggles between speaker / stop while
// playing. Uses the shared speak() controller so only one thing speaks at once.
import { useEffect, useState } from 'react';
import { Volume2, Square, Loader2 } from 'lucide-react';
import { speak, stopSpeaking } from '../../lib/speak';

interface Props {
  text: string;
  voiceId?: string;
  label?: string;
  className?: string;
}

export default function SpeakButton({ text, voiceId, label, className }: Props) {
  const [state, setState] = useState<'idle' | 'loading' | 'playing'>('idle');

  // Stop audio if this button unmounts mid-playback.
  useEffect(() => () => { if (state !== 'idle') stopSpeaking(); }, [state]);

  async function onClick() {
    if (state === 'playing' || state === 'loading') {
      stopSpeaking();
      setState('idle');
      return;
    }
    setState('loading');
    const provider = await speak(text, { voiceId, onEnd: () => setState('idle') });
    setState(provider ? 'playing' : 'idle');
  }

  return (
    <button
      onClick={onClick}
      aria-label={state === 'playing' ? 'Stop reading' : 'Read aloud'}
      title={state === 'playing' ? 'Stop' : 'Read aloud (Amazon Polly)'}
      className={
        'inline-flex items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-xs text-text-secondary transition-colors hover:border-signal-500/50 hover:bg-signal-500/10 hover:text-signal-400 ' +
        (className || '')
      }
    >
      {state === 'loading' ? (
        <Loader2 size={13} className="animate-spin" />
      ) : state === 'playing' ? (
        <Square size={13} />
      ) : (
        <Volume2 size={13} />
      )}
      {label && <span>{state === 'playing' ? 'Stop' : label}</span>}
    </button>
  );
}

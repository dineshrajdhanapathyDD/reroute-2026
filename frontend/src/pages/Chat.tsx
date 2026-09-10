// The conversational first page. A newcomer lands here and simply talks to the
// Navigator: "I'm new, where do I start?" → the agent explains, finds sessions,
// gives prep advice, or builds a full route. When the agent returns a plan we
// let the user apply it and jump straight into Mission Control.
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Compass, Send, Sparkles, ArrowRight, Loader2 } from 'lucide-react';
import { api, type ChatReply, type ChatTurn, type BackendPlan, type ABCPlanEntry } from '../lib/api';
import { useMission } from '../lib/missionContext';
import Button from '../components/ui/Button';
import SpeakButton from '../components/ui/SpeakButton';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  suggestions?: string[];
  plan?: BackendPlan;
  plansABC?: ABCPlanEntry[];
  sessionsCount?: number;
}

const WELCOME: Message = {
  role: 'assistant',
  content:
    "Hi, I'm your Re:Route AI navigator for AWS re:Invent. New here? Just tell me what you want to get out of the week and I'll turn it into a realistic, walkable plan — and re-route you when a session fills up.",
  suggestions: [
    "I'm new — where do I start?",
    'What is AWS re:Invent?',
    'Give me Plan A / B / C for learning GenAI',
    'First-timer tips',
  ],
};

export default function Chat() {
  const navigate = useNavigate();
  const { applyPlan, setMission } = useMission();
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  async function send(text: string) {
    const msg = text.trim();
    if (!msg || sending) return;
    setInput('');
    const nextMessages: Message[] = [...messages, { role: 'user', content: msg }];
    setMessages(nextMessages);
    setSending(true);

    const history: ChatTurn[] = nextMessages
      .slice(-8)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const res: ChatReply = await api.chat(msg, history);
      const assistant: Message = {
        role: 'assistant',
        content: res.reply,
        suggestions: res.suggestions,
      };
      if (res.data?.kind === 'plan' && res.data.plan) {
        assistant.plan = res.data.plan;
      }
      if (res.data?.kind === 'plans_abc' && res.data.plans) {
        assistant.plansABC = res.data.plans;
        setMission(msg); // so "Compare all three" on the Plans page regenerates from this goal
      }
      if (res.data?.kind === 'plan') {
        setMission(msg);
      }
      if (res.data?.kind === 'sessions' && res.data.sessions) {
        assistant.sessionsCount = res.data.sessions.length;
      }
      setMessages((m) => [...m, assistant]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content:
            "I couldn't reach the navigator just now. You can still jump into the guided setup to build your plan.",
          suggestions: ['Open guided setup'],
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  function usePlan(plan: BackendPlan) {
    applyPlan(plan);
    navigate('/mission');
  }

  function handleSuggestion(s: string) {
    if (s === 'Open guided setup') {
      navigate('/onboarding');
      return;
    }
    if (s === 'Compare the three plans') {
      navigate('/plans');
      return;
    }
    send(s);
  }

  function usePlanEntry(p: ABCPlanEntry) {
    applyPlan(p.plan);
    navigate('/mission');
  }

  return (
    <div className="flex min-h-screen flex-col bg-void">
      {/* Header */}
      <header className="flex shrink-0 items-center justify-between border-b border-line bg-hull/70 px-5 py-4 backdrop-blur-sm">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal-500">
            <Compass size={17} className="text-void" strokeWidth={2.5} />
          </div>
          <div>
            <span className="block font-display text-sm font-bold leading-none">RE:ROUTE AI</span>
            <span className="text-[11px] text-text-muted">Your re:Invent navigator</span>
          </div>
        </div>
        <button
          onClick={() => navigate('/onboarding')}
          className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary"
        >
          Guided setup
          <ArrowRight size={13} />
        </button>
      </header>

      {/* Conversation */}
      <div ref={scrollRef} className="mx-auto w-full max-w-2xl flex-1 overflow-y-auto px-4 py-6">
        <div className="space-y-5">
          {messages.map((m, i) => (
            <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
              <div className={m.role === 'user' ? 'max-w-[85%]' : 'w-full'}>
                {m.role === 'assistant' && (
                  <div className="mb-1.5 flex items-center gap-2">
                    <span className="flex items-center gap-1.5 text-[11px] font-medium text-signal-400">
                      <Sparkles size={12} />
                      Navigator
                    </span>
                    <SpeakButton text={m.content} />
                  </div>
                )}
                <div
                  className={
                    m.role === 'user'
                      ? 'rounded-2xl rounded-br-sm bg-signal-500 px-4 py-2.5 text-sm text-void'
                      : 'whitespace-pre-line rounded-2xl rounded-bl-sm border border-line bg-surface px-4 py-3 text-sm leading-relaxed text-text-primary'
                  }
                >
                  {m.content}
                </div>

                {/* Plan action */}
                {m.plan && (
                  <div className="mt-3">
                    <Button icon={<ArrowRight size={15} />} onClick={() => usePlan(m.plan!)}>
                      View full plan in Mission Control
                    </Button>
                  </div>
                )}

                {/* Plan A / B / C comparison */}
                {m.plansABC && m.plansABC.length > 0 && (
                  <div className="mt-3">
                    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
                      {m.plansABC.map((p) => (
                        <div key={p.key} className="flex flex-col rounded-2xl border border-line bg-surface p-3.5">
                          <span className="font-display text-sm font-semibold text-text-primary">{p.label}</span>
                          <p className="mt-1 min-h-[48px] text-[11px] leading-snug text-text-muted">{p.rationale}</p>
                          <div className="mt-2 space-y-1 text-[11px]">
                            <div className="flex justify-between"><span className="text-text-muted">Sessions</span><span className="font-mono text-text-primary">{p.summary.sessions}</span></div>
                            <div className="flex justify-between"><span className="text-text-muted">Journey</span><span className="font-mono text-text-primary">{p.summary.journey_score}%</span></div>
                            <div className="flex justify-between"><span className="text-text-muted">Walking</span><span className="font-mono text-text-primary">{p.summary.walking_km} km</span></div>
                          </div>
                          <Button size="sm" className="mt-3" onClick={() => usePlanEntry(p)}>
                            Use {p.key}
                          </Button>
                        </div>
                      ))}
                    </div>
                    <button
                      onClick={() => navigate('/plans')}
                      className="mt-2.5 flex items-center gap-1.5 text-xs text-signal-400 hover:text-signal-300"
                    >
                      Compare all three in detail <ArrowRight size={13} />
                    </button>
                  </div>
                )}

                {/* Suggestion chips */}
                {m.role === 'assistant' && m.suggestions && m.suggestions.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {m.suggestions.map((s) => (
                      <button
                        key={s}
                        onClick={() => handleSuggestion(s)}
                        disabled={sending}
                        className="rounded-full border border-line bg-surface px-3.5 py-1.5 text-xs text-text-secondary transition-colors hover:border-signal-500/50 hover:bg-signal-500/10 hover:text-signal-400 disabled:opacity-40"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-line bg-surface px-4 py-3 text-sm text-text-muted">
                <Loader2 size={15} className="animate-spin text-signal-400" />
                Navigator is thinking…
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Composer */}
      <div className="shrink-0 border-t border-line bg-hull/70 backdrop-blur-sm">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="mx-auto flex w-full max-w-2xl items-end gap-2 px-4 py-4"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={1}
            placeholder="Ask the navigator anything… e.g. “I want to get production-ready with AI agents”"
            className="max-h-32 min-h-[46px] flex-1 resize-none rounded-[var(--radius-control)] border border-line bg-surface px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:border-signal-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
            aria-label="Send"
            className="flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-[var(--radius-control)] bg-signal-500 text-void transition-colors hover:bg-signal-400 disabled:opacity-40"
          >
            <Send size={17} />
          </button>
        </form>
      </div>
    </div>
  );
}

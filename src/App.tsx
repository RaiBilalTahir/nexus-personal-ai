import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleAlert,
  Clock3,
  Command,
  Cpu,
  Database,
  FileText,
  Layers3,
  Mic,
  MoreHorizontal,
  Orbit,
  PanelRight,
  Play,
  Plus,
  RotateCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  X,
  Zap,
} from 'lucide-react'

type NexusState = 'idle' | 'listening' | 'processing' | 'responding' | 'executing' | 'verifying' | 'success' | 'warning' | 'error' | 'recovery'
type Mode = 'CONVERSATION' | 'TASK' | 'RESEARCH' | 'VISION'

const stateMeta: Record<NexusState, { label: string; eyebrow: string; accent: string }> = {
  idle: { label: 'Standing by', eyebrow: 'NEXUS CORE', accent: 'cyan' },
  listening: { label: 'Listening', eyebrow: 'VOICE CHANNEL', accent: 'violet' },
  processing: { label: 'Thinking', eyebrow: 'NEURAL PROCESS', accent: 'cyan' },
  responding: { label: 'Responding', eyebrow: 'NEXUS CORE', accent: 'cyan' },
  executing: { label: 'Executing task', eyebrow: 'ACTION LAYER', accent: 'amber' },
  verifying: { label: 'Verifying result', eyebrow: 'PROVENANCE', accent: 'violet' },
  success: { label: 'Complete', eyebrow: 'SYSTEM EVENT', accent: 'emerald' },
  warning: { label: 'Needs attention', eyebrow: 'SYSTEM EVENT', accent: 'amber' },
  error: { label: 'Action blocked', eyebrow: 'SYSTEM EVENT', accent: 'rose' },
  recovery: { label: 'Recovering', eyebrow: 'RECOVERY LAYER', accent: 'cyan' },
}

const sampleSteps = [
  { label: 'Interpret request', detail: 'Intent and constraints resolved', status: 'completed' },
  { label: 'Inspect workspace', detail: 'Reading available context', status: 'completed' },
  { label: 'Prepare response', detail: 'Synthesizing grounded result', status: 'running' },
  { label: 'Verify output', detail: 'Awaiting execution state', status: 'queued' },
]

function Core({ state }: { state: NexusState }) {
  const meta = stateMeta[state]
  return (
    <div className={`core-stage core-${meta.accent} core-state-${state}`} aria-label={`Nexus Core ${meta.label}`}>
      <div className="core-orbit orbit-one" />
      <div className="core-orbit orbit-two" />
      <div className="core-orbit orbit-three" />
      <div className="core-halo" />
      <div className="core-shell">
        <div className="core-grid" />
        <div className="core-spark spark-a" />
        <div className="core-spark spark-b" />
        <div className="core-spark spark-c" />
        <div className="core-center"><Orbit size={34} strokeWidth={1.2} /></div>
      </div>
      <div className="core-caption"><span className="eyebrow">{meta.eyebrow}</span><strong>{meta.label}</strong></div>
    </div>
  )
}

function App() {
  const [state, setState] = useState<NexusState>('idle')
  const [mode, setMode] = useState<Mode>('CONVERSATION')
  const [command, setCommand] = useState('')
  const [showPanel, setShowPanel] = useState(true)
  const [showTask, setShowTask] = useState(false)
  const [response, setResponse] = useState('')
  const [time, setTime] = useState(new Date())
  const [connected, setConnected] = useState(true)

  useEffect(() => {
    const timer = window.setInterval(() => setTime(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const dateLabel = useMemo(() => time.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase(), [time])
  const timeLabel = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  const submitCommand = () => {
    if (!command.trim() || state === 'processing') return
    setState('processing')
    setResponse('')
    window.setTimeout(() => {
      setResponse('I’m ready to work through that with you. The presentation layer is connected and waiting for a Nexus Core capability to take over.')
      setState('responding')
    }, 900)
  }

  const activate = (next: NexusState) => {
    setState(next)
    if (next === 'executing') setShowTask(true)
    if (next === 'idle') setShowTask(false)
  }

  return (
    <div className="nexus-app">
      <div className="ambient ambient-a" /><div className="ambient ambient-b" /><div className="noise" />
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><Cpu size={17} /></div><div><div className="brand-name">NEXUS <span>01</span></div><div className="brand-sub">PERSONAL INTELLIGENCE SYSTEM</div></div></div>
        <div className="topbar-center"><span className="live-dot" /> CORE ONLINE <span className="topbar-divider" /> SESSION 08A4</div>
        <div className="topbar-actions"><span className="clock"><span>{dateLabel}</span>{timeLabel}</span><button className="icon-button" aria-label="Open command menu"><Command size={16} /></button><button className="icon-button" aria-label="Open settings"><MoreHorizontal size={17} /></button></div>
      </header>

      <main className="main-layout">
        <section className="hero-column">
          <div className="hero-heading"><div><div className="kicker"><span className="kicker-line" /> PERSONAL OPERATING ENVIRONMENT</div><h1>Good evening, <em>Bilal.</em></h1><p>What would you like Nexus to take care of?</p></div><div className="hero-actions"><button className="quiet-button" onClick={() => activate('listening')}><Mic size={15} /> Voice ready</button><button className="quiet-button" onClick={() => setConnected(!connected)}><span className={`status-ring ${connected ? 'is-on' : ''}`} /> {connected ? 'Connected' : 'Offline'}</button></div></div>
          <div className="core-wrap"><Core state={state} /><div className="core-side-note note-left"><span>LATENCY</span><strong>24<span>ms</span></strong><i /></div><div className="core-side-note note-right"><span>UPTIME</span><strong>99.8<span>%</span></strong><i /></div></div>
          <div className="mode-switcher"><span className="mode-label">ENVIRONMENT</span>{(['CONVERSATION', 'TASK', 'RESEARCH', 'VISION'] as Mode[]).map((item) => <button key={item} className={mode === item ? 'active' : ''} onClick={() => setMode(item)}>{item}</button>)}</div>
          <div className="command-wrap"><div className="command-meta"><span><span className="pulse-dot" /> READY FOR INPUT</span><span className="mono">⌘ K</span></div><div className="command-box"><Sparkles size={18} className="command-icon" /><input value={command} onChange={(event) => setCommand(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.nativeEvent.isComposing && event.keyCode !== 229) submitCommand() }} placeholder="Ask Nexus anything..." aria-label="Command Nexus" /><button className="mic-button" onClick={() => activate('listening')} aria-label="Start voice input"><Mic size={17} /></button><button className="send-button" onClick={submitCommand} aria-label="Send command"><Send size={16} /></button></div><div className="command-hint">Try <button onClick={() => setCommand('Summarize my current workspace')}>“Summarize my current workspace”</button> <span>or</span> <button onClick={() => setCommand('Prepare a research brief')}>“Prepare a research brief”</button></div></div>
          {response && <div className="response-card"><div className="response-top"><span><Sparkles size={14} /> NEXUS RESPONSE</span><button onClick={() => setResponse('')} aria-label="Dismiss response"><X size={14} /></button></div><p>{response}</p><div className="response-foot"><span><ShieldCheck size={13} /> Presentation layer · no external action taken</span><button onClick={() => activate('executing')}>Continue <ArrowUpRight size={13} /></button></div></div>}
        </section>

        <aside className={`context-panel ${showPanel ? '' : 'panel-hidden'}`}>
          <div className="panel-header"><div><span className="eyebrow">CONTEXT LAYER</span><h2>System overview</h2></div><button className="icon-button" onClick={() => setShowPanel(false)} aria-label="Hide context panel"><PanelRight size={16} /></button></div>
          <div className="signal-card"><div className="signal-header"><span className="signal-icon"><Activity size={15} /></span><div><strong>Core readiness</strong><span>All systems nominal</span></div><span className="signal-value">98%</span></div><div className="signal-bar"><i /></div><div className="signal-footer"><span>NEURAL ROUTER</span><span>LOW LATENCY</span></div></div>
          <div className="panel-section"><div className="section-title"><span>ACTIVE CAPABILITIES</span><button aria-label="Add capability"><Plus size={14} /></button></div><div className="capability"><span className="cap-icon"><TerminalSquare size={14} /></span><div><strong>Command interface</strong><small>Available · ready</small></div><span className="available" /></div><div className="capability"><span className="cap-icon"><Database size={14} /></span><div><strong>Workspace context</strong><small>Available · read only</small></div><span className="available" /></div><div className="capability muted"><span className="cap-icon"><Mic size={14} /></span><div><strong>Voice interaction</strong><small>Planned · not active</small></div><span className="planned" /></div></div>
          <div className="panel-section"><div className="section-title"><span>RECENT ACTIVITY</span><button aria-label="Refresh activity" onClick={() => activate('verifying')}><RotateCw size={13} /></button></div><div className="activity-row"><span className="activity-mark success"><Check size={12} /></span><div><strong>Session initialized</strong><small>Just now · Core handshake complete</small></div></div><div className="activity-row"><span className="activity-mark"><Clock3 size={12} /></span><div><strong>Awaiting your direction</strong><small>Conversation environment</small></div></div></div>
          <div className="panel-footer"><div className="privacy"><ShieldCheck size={14} /><span><strong>Privacy mode</strong><small>Local session · protected</small></span></div><button className="text-button" onClick={() => setShowTask(true)}>View details <ArrowUpRight size={13} /></button></div>
        </aside>
        {!showPanel && <button className="reveal-panel" onClick={() => setShowPanel(true)} aria-label="Show context panel"><PanelRight size={15} /></button>}
      </main>

      {showTask && <div className="task-drawer"><div className="drawer-head"><div><span className="eyebrow">TASK VISUALIZATION</span><h2>Workspace synthesis</h2></div><button className="icon-button" onClick={() => setShowTask(false)} aria-label="Close task details"><X size={16} /></button></div><div className="task-progress"><span>EXECUTION GRAPH</span><strong>3 / 4 steps</strong></div><div className="steps">{sampleSteps.map((step, index) => <div className={`step ${step.status}`} key={step.label}><span className="step-number">{step.status === 'completed' ? <Check size={12} /> : index + 1}</span><div><strong>{step.label}</strong><small>{step.detail}</small></div>{step.status === 'running' && <span className="step-spinner"><RotateCw size={13} /></span>}</div>)}</div><div className="drawer-actions"><button className="quiet-button" onClick={() => activate('recovery')}><CircleAlert size={14} /> Simulate recovery</button><button className="primary-button" onClick={() => activate('success')}><Zap size={14} /> Run verification</button></div></div>}
      <footer className="footerbar"><span><Layers3 size={13} /> NEXUS PRESENTATION LAYER</span><span>MODEL <strong>GEMINI FLASH</strong></span><span>BUILD <strong>1.1.1</strong></span><span className="footer-spacer" /><span><FileText size={13} /> PROVENANCE READY</span></footer>
    </div>
  )
}

export default App

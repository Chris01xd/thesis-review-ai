import { useState, useRef, useEffect } from 'react'
import { MessageCircle, X, Send, Mic, MicOff, Volume2, VolumeX, Loader2, Bot, User } from 'lucide-react'
import { sendChatMessage } from '../../api'
import type { ChatMessage } from '../../api'

// ── Markdown bold helper ─────────────────────────────────────────────────────
function renderMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : <span key={i}>{part}</span>
  )
}

function BotMessage({ text }: { text: string }) {
  return (
    <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-line">
      {text.split('\n').map((line, i) => (
        <p key={i} className={line.trim() === '' ? 'mt-1' : ''}>
          {renderMarkdown(line)}
        </p>
      ))}
    </div>
  )
}

// ── SpeechRecognition setup ──────────────────────────────────────────────────
type SRConstructor = new () => {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((e: any) => void) | null
  onerror:  (() => void) | null
  onend:    (() => void) | null
  start():  void
  stop():   void
}
const SR: SRConstructor | undefined =
  (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition

const SUGGESTIONS = [
  '¿Cuántas tesis hay registradas?',
  '¿Cuántos análisis IA se han realizado?',
  '¿Cuál es el puntaje promedio?',
  '¿Qué funciones tiene el sistema?',
  '¿Cuántos estudiantes hay?',
]

export function ChatBot() {
  const [open, setOpen]         = useState(false)
  const [input, setInput]       = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading]   = useState(false)
  const [recording, setRecording] = useState(false)
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const [unread, setUnread]     = useState(0)
  const bottomRef  = useRef<HTMLDivElement>(null)
  const inputRef   = useRef<HTMLInputElement>(null)
  const srRef      = useRef<any>(null)

  // Scroll al último mensaje
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Incrementar badge cuando llega un mensaje con el chat cerrado
  useEffect(() => {
    if (!open && messages.length > 0 && messages[messages.length - 1].role === 'assistant') {
      setUnread(n => n + 1)
    }
  }, [messages])

  const openChat = () => {
    setOpen(true)
    setUnread(0)
    setTimeout(() => inputRef.current?.focus(), 100)
    // Saludo inicial
    if (messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: '¡Hola! Soy el asistente de **ThesisReview AI**. 👋\n\nPuedo contarte estadísticas del sistema, explicar sus funciones o responder dudas. ¿En qué te ayudo?',
      }])
    }
  }

  // ── Enviar mensaje ────────────────────────────────────────────────────────
  const send = async (text?: string) => {
    const msg = (text ?? input).trim()
    if (!msg || loading) return
    setInput('')
    const userMsg: ChatMessage = { role: 'user', content: msg }
    const history = [...messages, userMsg]
    setMessages(history)
    setLoading(true)
    try {
      const res = await sendChatMessage(msg, messages)
      const botMsg: ChatMessage = { role: 'assistant', content: res.answer }
      setMessages([...history, botMsg])
      if (ttsEnabled) speakText(res.answer)
    } catch (err: any) {
      const status  = err?.response?.status
      const detail  = err?.response?.data?.detail || err?.message || 'sin detalle'
      const apiBase = import.meta.env.VITE_API_URL || '(vacío — misma origen)'
      console.error('[ChatBot] error /api/chat →', status, detail, err)
      const msg = status === 404
        ? `Endpoint no encontrado (404). Backend: ${apiBase}`
        : status >= 500
          ? `Error del servidor (${status}): ${detail}`
          : `No se pudo conectar. URL backend: ${apiBase} | Error: ${detail}`
      setMessages([...history, { role: 'assistant', content: msg }])
    } finally {
      setLoading(false)
    }
  }

  // ── Voz → texto ──────────────────────────────────────────────────────────
  const toggleMic = () => {
    if (!SR) return
    if (recording) {
      srRef.current?.stop()
      setRecording(false)
      return
    }
    const sr = new SR()
    sr.lang = 'es-PE'
    sr.continuous = false
    sr.interimResults = false
    sr.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setInput(transcript)
      setRecording(false)
    }
    sr.onerror = () => setRecording(false)
    sr.onend = () => setRecording(false)
    srRef.current = sr
    sr.start()
    setRecording(true)
  }

  // ── Texto → voz ──────────────────────────────────────────────────────────
  const speakText = (text: string) => {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const clean = text.replace(/\*\*/g, '').replace(/•/g, '').replace(/\n+/g, '. ')
    const utt = new SpeechSynthesisUtterance(clean)
    utt.lang = 'es-PE'
    utt.rate = 1.0
    utt.pitch = 1.0
    // Preferir voz en español si está disponible
    const voices = window.speechSynthesis.getVoices()
    const esVoice = voices.find(v => v.lang.startsWith('es'))
    if (esVoice) utt.voice = esVoice
    window.speechSynthesis.speak(utt)
  }

  const stopSpeech = () => window.speechSynthesis?.cancel()

  return (
    <>
      {/* ── Botón flotante ─────────────────────────────────────────────── */}
      <button
        onClick={openChat}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all
          ${open ? 'scale-0 opacity-0 pointer-events-none' : 'scale-100 opacity-100'}
          bg-blue-600 hover:bg-blue-700 text-white`}
        aria-label="Abrir asistente"
      >
        <MessageCircle size={26} />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
            {unread}
          </span>
        )}
      </button>

      {/* ── Panel del chat ─────────────────────────────────────────────── */}
      <div className={`fixed bottom-6 right-6 z-50 w-[360px] max-w-[calc(100vw-24px)] flex flex-col
        bg-white rounded-2xl shadow-2xl border border-gray-200 transition-all duration-300
        ${open ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8 pointer-events-none'}`}
        style={{ height: '520px' }}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 bg-blue-600 rounded-t-2xl text-white flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
            <Bot size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-sm leading-tight">Asistente ThesisReview</p>
            <p className="text-xs text-blue-200">Responde sobre el sistema · escrito o por voz</p>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => { setTtsEnabled(v => !v); stopSpeech() }}
              className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
              title={ttsEnabled ? 'Silenciar respuestas' : 'Activar voz'}
            >
              {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
            <button
              onClick={() => { setOpen(false); stopSpeech() }}
              className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
              aria-label="Cerrar"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Mensajes */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-white text-xs
                ${msg.role === 'user' ? 'bg-blue-500' : 'bg-slate-600'}`}>
                {msg.role === 'user' ? <User size={13} /> : <Bot size={13} />}
              </div>
              <div className={`max-w-[82%] rounded-xl px-3 py-2 text-sm
                ${msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-sm'
                  : 'bg-gray-100 text-gray-800 rounded-tl-sm'}`}>
                {msg.role === 'assistant'
                  ? <BotMessage text={msg.content} />
                  : <span>{msg.content}</span>}
                {msg.role === 'assistant' && ttsEnabled && (
                  <button
                    onClick={() => speakText(msg.content)}
                    className="mt-1 text-gray-400 hover:text-blue-600 transition-colors"
                    title="Reproducir en voz alta"
                  >
                    <Volume2 size={12} />
                  </button>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-2">
              <div className="w-7 h-7 rounded-full bg-slate-600 flex items-center justify-center text-white">
                <Bot size={13} />
              </div>
              <div className="bg-gray-100 rounded-xl rounded-tl-sm px-3 py-2">
                <Loader2 size={16} className="animate-spin text-gray-500" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Sugerencias (solo al inicio) */}
        {messages.length <= 1 && !loading && (
          <div className="px-4 pb-2 flex flex-wrap gap-1.5 flex-shrink-0">
            {SUGGESTIONS.map(s => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-full px-2.5 py-1 hover:bg-blue-100 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="px-3 pb-3 pt-2 border-t border-gray-100 flex-shrink-0">
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder={recording ? '🎤 Grabando...' : 'Escribe tu pregunta...'}
              className="flex-1 bg-transparent text-sm outline-none text-gray-800 placeholder-gray-400 min-w-0"
              disabled={loading}
            />
            {SR && (
              <button
                onClick={toggleMic}
                disabled={loading}
                className={`p-1.5 rounded-lg transition-colors flex-shrink-0
                  ${recording ? 'text-red-500 bg-red-50 animate-pulse' : 'text-gray-400 hover:text-blue-600 hover:bg-blue-50'}`}
                title={recording ? 'Detener grabación' : 'Hablar'}
              >
                {recording ? <MicOff size={16} /> : <Mic size={16} />}
              </button>
            )}
            <button
              onClick={() => send()}
              disabled={loading || !input.trim()}
              className="p-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white transition-colors flex-shrink-0"
              title="Enviar"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

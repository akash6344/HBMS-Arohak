import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Button, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/format'
import type { RagAskResponse } from '../lib/types'
import styles from './HotelInfoChatPage.module.scss'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  response?: RagAskResponse | null
  error?: string
  pending?: boolean
}

export function HotelInfoChatPage() {
  const [hotelId, setHotelId] = useState('')
  const [ready, setReady] = useState(false)
  const [bootError, setBootError] = useState('')
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({})
  const scrollerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setBootError('')
      try {
        const options = await api.listRagHotels()
        if (cancelled) return
        if (!options[0]) {
          setBootError('Assistant is unavailable right now.')
          setReady(false)
          return
        }
        setHotelId(options[0].hotel_id)
        setReady(true)
      } catch (err) {
        if (!cancelled) {
          setBootError(getErrorMessage(err))
          setReady(false)
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const node = scrollerRef.current
    if (!node) return
    node.scrollTop = node.scrollHeight
  }, [messages, asking])

  const resizeInput = () => {
    const node = inputRef.current
    if (!node) return
    node.style.height = 'auto'
    node.style.height = `${Math.min(node.scrollHeight, 160)}px`
  }

  const send = async () => {
    if (!hotelId || !question.trim() || asking) return

    const turnId = crypto.randomUUID()
    const asked = question.trim()
    setAsking(true)
    setQuestion('')
    requestAnimationFrame(resizeInput)

    setMessages((prev) => [
      ...prev,
      { id: `${turnId}-user`, role: 'user', content: asked },
      { id: `${turnId}-assistant`, role: 'assistant', content: '', pending: true },
    ])

    try {
      const response = await api.askRag({ hotel_id: hotelId, question: asked })
      setMessages((prev) =>
        prev.map((message) =>
          message.id === `${turnId}-assistant`
            ? {
                ...message,
                pending: false,
                content: response.answer,
                response,
              }
            : message,
        ),
      )
    } catch (err) {
      const message = getErrorMessage(err)
      setMessages((prev) =>
        prev.map((item) =>
          item.id === `${turnId}-assistant`
            ? { ...item, pending: false, content: '', error: message }
            : item,
        ),
      )
    } finally {
      setAsking(false)
      inputRef.current?.focus()
    }
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    void send()
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void send()
    }
  }

  return (
    <div className={styles.chatShell}>
      <div className={styles.thread} ref={scrollerRef}>
        {!ready && !bootError ? (
          <div className={styles.centered}>
            <Spinner />
          </div>
        ) : null}

        {bootError ? <div className={styles.centeredError}>{bootError}</div> : null}

        {ready && messages.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyMark}>HB</div>
            <p className={styles.emptyTitle}>How can I help?</p>
            <div className={styles.suggestions}>
              {[
                'What time is check-in?',
                'Is parking free?',
                'Tell me about the checkout policy',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className={styles.suggestion}
                  onClick={() => {
                    setQuestion(suggestion)
                    requestAnimationFrame(() => {
                      resizeInput()
                      inputRef.current?.focus()
                    })
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((message) => (
          <div
            key={message.id}
            className={[
              styles.row,
              message.role === 'user' ? styles.rowUser : styles.rowAssistant,
            ].join(' ')}
          >
            {message.role === 'assistant' ? (
              <div className={styles.avatar} aria-hidden>
                HB
              </div>
            ) : null}
            <div
              className={[
                styles.bubble,
                message.role === 'user' ? styles.userBubble : styles.assistantBubble,
              ].join(' ')}
            >
              {message.pending ? (
                <div className={styles.typing}>
                  <span />
                  <span />
                  <span />
                </div>
              ) : null}
              {message.error ? <p className={styles.errorText}>{message.error}</p> : null}
              {message.content ? <p className={styles.messageText}>{message.content}</p> : null}
              {message.response?.grounded && message.response.citations.length > 0 ? (
                <div className={styles.sources}>
                  <button
                    type="button"
                    className={styles.sourcesToggle}
                    onClick={() =>
                      setExpandedSources((prev) => ({
                        ...prev,
                        [message.id]: !prev[message.id],
                      }))
                    }
                  >
                    {expandedSources[message.id] ? 'Hide sources' : 'Show sources'}
                  </button>
                  {expandedSources[message.id] ? (
                    <ul className={styles.sourceList}>
                      {message.response.citations.slice(0, 3).map((citation) => (
                        <li key={`${citation.section}-${citation.page_start}-${citation.score}`}>
                          <span className={styles.sourceTitle}>{citation.section}</span>
                          <span className={styles.sourceMeta}>p{citation.page_start}</span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      <form className={styles.composerBar} onSubmit={onSubmit}>
        <div className={styles.composerInner}>
          <textarea
            ref={inputRef}
            className={styles.composerInput}
            rows={1}
            placeholder="Message…"
            value={question}
            disabled={!ready || asking}
            onChange={(event) => {
              setQuestion(event.target.value)
              resizeInput()
            }}
            onKeyDown={onKeyDown}
          />
          <Button
            type="submit"
            size="sm"
            disabled={!ready || asking || !question.trim()}
            aria-label="Send message"
          >
            Send
          </Button>
        </div>
      </form>
    </div>
  )
}

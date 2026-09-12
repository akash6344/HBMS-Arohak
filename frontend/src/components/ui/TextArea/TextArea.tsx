import type { TextareaHTMLAttributes } from 'react'
import styles from './TextArea.module.scss'

export function TextArea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={[styles.textarea, className].filter(Boolean).join(' ')} {...props} />
}

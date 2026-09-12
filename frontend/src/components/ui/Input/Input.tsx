import type { InputHTMLAttributes } from 'react'
import styles from './Input.module.scss'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
}

export function Input({ invalid = false, className, ...props }: InputProps) {
  return (
    <input
      className={[styles.input, invalid ? styles.invalid : '', className].filter(Boolean).join(' ')}
      {...props}
    />
  )
}

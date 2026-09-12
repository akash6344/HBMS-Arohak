import type { ReactNode } from 'react'
import styles from './Card.module.scss'

interface CardProps {
  children: ReactNode
  className?: string
  padded?: boolean
}

export function Card({ children, className, padded = true }: CardProps) {
  return (
    <section className={[styles.card, padded ? styles.padded : '', className].filter(Boolean).join(' ')}>
      {children}
    </section>
  )
}

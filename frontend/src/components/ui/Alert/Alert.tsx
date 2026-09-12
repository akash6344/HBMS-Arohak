import type { ReactNode } from 'react'
import styles from './Alert.module.scss'

type Tone = 'info' | 'success' | 'warning' | 'danger'

interface AlertProps {
  children: ReactNode
  tone?: Tone
}

export function Alert({ children, tone = 'info' }: AlertProps) {
  return <div className={`${styles.alert} ${styles[tone]}`}>{children}</div>
}

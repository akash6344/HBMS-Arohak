import type { CSSProperties, ReactNode } from 'react'
import styles from './Stack.module.scss'

interface StackProps {
  children: ReactNode
  gap?: 'sm' | 'md' | 'lg'
  direction?: 'vertical' | 'horizontal'
  className?: string
  style?: CSSProperties
}

export function Stack({
  children,
  gap = 'md',
  direction = 'vertical',
  className,
  style,
}: StackProps) {
  return (
    <div
      className={[styles.stack, styles[direction], styles[gap], className].filter(Boolean).join(' ')}
      style={style}
    >
      {children}
    </div>
  )
}

import type { ReactNode } from 'react'
import styles from './AuthLayout.module.scss'

interface AuthLayoutProps {
  title: string
  subtitle: string
  children: ReactNode
}

export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className={styles.layout}>
      <section className={styles.panel}>
        <div className={styles.brandRow}>
          <div className={styles.brandMark}>H</div>
          <span>HBMS</span>
        </div>
        <div className={styles.heading}>
          <h1>{title}</h1>
          <p className={styles.subtitle}>{subtitle}</p>
        </div>
        {children}
      </section>
    </div>
  )
}

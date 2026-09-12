import styles from './Spinner.module.scss'

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className={styles.wrap} role="status" aria-live="polite">
      <span className={styles.spinner} />
      <span>{label}</span>
    </div>
  )
}

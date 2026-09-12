import type { SelectHTMLAttributes } from 'react'
import styles from './Select.module.scss'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: Array<{ label: string; value: string }>
}

export function Select({ options, className, ...props }: SelectProps) {
  return (
    <select className={[styles.select, className].filter(Boolean).join(' ')} {...props}>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}

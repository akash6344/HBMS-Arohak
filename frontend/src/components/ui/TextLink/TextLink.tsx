import { Link, type LinkProps } from 'react-router-dom'
import styles from './TextLink.module.scss'

export function TextLink({ className, ...props }: LinkProps) {
  return <Link className={[styles.link, className].filter(Boolean).join(' ')} {...props} />
}

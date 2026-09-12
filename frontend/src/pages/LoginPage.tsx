import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthLayout } from '../components/layout/AuthLayout/AuthLayout'
import { Alert, Button, FormField, Input, Stack, TextLink } from '../components/ui'
import { useAuth } from '../auth/AuthContext'
import { getErrorMessage } from '../lib/format'
import type { Role } from '../lib/types'
import styles from './pages.module.scss'

function homeForRole(role: Role): string {
  if (role === 'CUSTOMER') return '/search'
  if (role === 'PRODUCT_ADMIN') return '/platform/organizations'
  return '/staff/bookings'
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('customer@hbms.example')
  const [password, setPassword] = useState('Password123!')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const principal = await login(email, password)
      navigate(homeForRole(principal.role))
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to log in'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to manage bookings across organizations.">
      <form onSubmit={onSubmit}>
        <Stack>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <FormField label="Email" htmlFor="email">
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </FormField>
          <FormField label="Password" htmlFor="password">
            <Input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </FormField>
          <Button type="submit" loading={loading}>
            Sign in
          </Button>
          <p className={styles.switchLine}>
            New here? <TextLink to="/register">Create a customer account</TextLink>
          </p>
        </Stack>
      </form>
    </AuthLayout>
  )
}

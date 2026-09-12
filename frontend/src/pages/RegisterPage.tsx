import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthLayout } from '../components/layout/AuthLayout/AuthLayout'
import { Alert, Button, FormField, Input, Stack, TextLink } from '../components/ui'
import { useAuth } from '../auth/AuthContext'
import { getErrorMessage } from '../lib/format'
import styles from './pages.module.scss'

export function RegisterPage() {
  const { register, login } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await register(name, email, password)
      await login(email, password)
      navigate('/search')
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to register'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Create account" subtitle="Customer registration for browsing and booking rooms.">
      <form onSubmit={onSubmit}>
        <Stack>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <FormField label="Name" htmlFor="name">
            <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
          </FormField>
          <FormField label="Email" htmlFor="email">
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FormField>
          <FormField label="Password" htmlFor="password" hint="Minimum 8 characters">
            <Input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </FormField>
          <Button type="submit" loading={loading}>
            Register
          </Button>
          <p className={styles.switchLine}>
            Already registered? <TextLink to="/login">Sign in</TextLink>
          </p>
        </Stack>
      </form>
    </AuthLayout>
  )
}

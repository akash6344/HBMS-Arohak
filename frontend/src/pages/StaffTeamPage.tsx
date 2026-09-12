import { useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  Alert,
  Button,
  Card,
  FormField,
  Input,
  PageHeader,
  Select,
  Stack,
} from '../components/ui'
import { useAuth } from '../auth/AuthContext'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/format'
import type { Hotel, Organization } from '../lib/types'

type StaffRoleOption = 'ORG_ADMIN' | 'RECEPTIONIST'

export function StaffTeamPage() {
  const { hasRole } = useAuth()
  const canCreateOrgAdmin = hasRole('PRODUCT_ADMIN')

  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [hotels, setHotels] = useState<Hotel[]>([])
  const [organizationId, setOrganizationId] = useState('')
  const [hotelId, setHotelId] = useState('')
  const [role, setRole] = useState<StaffRoleOption>(
    canCreateOrgAdmin ? 'ORG_ADMIN' : 'RECEPTIONIST',
  )
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: 'Password123!',
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    void (async () => {
      try {
        const orgs = await api.listOrganizations()
        setOrganizations(orgs)
        setOrganizationId(orgs[0]?._id ?? '')
      } catch (err) {
        setError(getErrorMessage(err))
      }
    })()
  }, [])

  useEffect(() => {
    if (!organizationId) return
    void (async () => {
      const hotelList = await api.listHotels(organizationId)
      setHotels(hotelList)
      setHotelId(hotelList[0]?._id ?? '')
    })()
  }, [organizationId])

  const orgOptions = useMemo(
    () => organizations.map((org) => ({ label: org.name, value: org._id })),
    [organizations],
  )
  const hotelOptions = useMemo(
    () => hotels.map((hotel) => ({ label: hotel.name, value: hotel._id })),
    [hotels],
  )
  const roleOptions = useMemo(() => {
    const options = [{ label: 'Receptionist', value: 'RECEPTIONIST' }]
    if (canCreateOrgAdmin) {
      options.unshift({ label: 'Organization Admin', value: 'ORG_ADMIN' })
    }
    return options
  }, [canCreateOrgAdmin])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)

    try {
      if (role === 'ORG_ADMIN') {
        await api.createOrgAdmin({
          organization_id: organizationId,
          name: form.name,
          email: form.email,
          password: form.password,
        })
        setMessage(`Organization admin created: ${form.email}`)
      } else {
        if (!hotelId) {
          throw new Error('Select a hotel for the receptionist.')
        }
        await api.createReceptionist({
          name: form.name,
          email: form.email,
          password: form.password,
          hotel_ids: [hotelId],
        })
        setMessage(`Receptionist created: ${form.email}`)
      }

      setForm({ name: '', email: '', password: 'Password123!' })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="Workspace"
        title="Team"
        description="Invite staff and assign them to an organization or hotel."
      />
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}

      <Card>
        <form onSubmit={(event) => void onSubmit(event)}>
          <Stack>
            <FormField label="Role" htmlFor="role">
              <Select
                id="role"
                options={roleOptions}
                value={role}
                onChange={(e) => setRole(e.target.value as StaffRoleOption)}
              />
            </FormField>

            <FormField label="Organization" htmlFor="organization">
              <Select
                id="organization"
                options={orgOptions}
                value={organizationId}
                onChange={(e) => setOrganizationId(e.target.value)}
              />
            </FormField>

            {role === 'RECEPTIONIST' ? (
              <FormField label="Hotel" htmlFor="hotel">
                <Select
                  id="hotel"
                  options={hotelOptions.length ? hotelOptions : [{ label: 'No hotels', value: '' }]}
                  value={hotelId}
                  onChange={(e) => setHotelId(e.target.value)}
                />
              </FormField>
            ) : null}

            <FormField label="Name" htmlFor="name">
              <Input
                id="name"
                required
                value={form.name}
                onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              />
            </FormField>

            <FormField label="Email" htmlFor="email">
              <Input
                id="email"
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
              />
            </FormField>

            <FormField label="Password" htmlFor="password">
              <Input
                id="password"
                type="password"
                required
                minLength={8}
                value={form.password}
                onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
              />
            </FormField>

            <Button type="submit" loading={loading} disabled={!organizationId}>
              Create team member
            </Button>
          </Stack>
        </form>
      </Card>
    </Stack>
  )
}

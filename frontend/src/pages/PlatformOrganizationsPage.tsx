import { useEffect, useState, type FormEvent } from 'react'
import {
  Alert,
  Button,
  FormField,
  Input,
  Modal,
  PageHeader,
  Spinner,
  Stack,
  Table,
  type TableColumn,
} from '../components/ui'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/format'
import type { Organization } from '../lib/types'

export function PlatformOrganizationsPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      setOrganizations(await api.listOrganizations())
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const onCreate = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await api.createOrganization({ name })
      setOpen(false)
      setName('')
      setMessage('Organization created')
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const columns: TableColumn<Organization>[] = [
    { key: 'name', header: 'Name', render: (row) => row.name },
    { key: 'status', header: 'Status', render: (row) => row.status },
    { key: 'id', header: 'ID', render: (row) => row._id },
  ]

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="Platform"
        title="Organizations"
        description="Create and review tenant organizations."
        actions={<Button onClick={() => setOpen(true)}>New organization</Button>}
      />
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}
      {loading ? (
        <Spinner />
      ) : (
        <Table columns={columns} rows={organizations} rowKey={(row) => row._id} />
      )}
      <Modal
        open={open}
        title="Create organization"
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button form="create-org" type="submit">
              Create
            </Button>
          </>
        }
      >
        <form id="create-org" onSubmit={(event) => void onCreate(event)}>
          <FormField label="Organization name" htmlFor="org_name">
            <Input id="org_name" required value={name} onChange={(e) => setName(e.target.value)} />
          </FormField>
        </form>
      </Modal>
    </Stack>
  )
}

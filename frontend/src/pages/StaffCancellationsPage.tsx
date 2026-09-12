import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  PageHeader,
  Spinner,
  Stack,
  Table,
  type TableColumn,
} from '../components/ui'
import { api } from '../lib/api'
import { formatDate, getErrorMessage } from '../lib/format'
import type { CancellationRequest } from '../lib/types'

export function StaffCancellationsPage() {
  const [requests, setRequests] = useState<CancellationRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      setRequests(await api.listCancellationRequests())
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const columns: TableColumn<CancellationRequest>[] = [
    {
      key: 'booking',
      header: 'Booking',
      render: (row) => row.booking_id,
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (row) => row.reason,
    },
    {
      key: 'created',
      header: 'Requested',
      render: (row) => formatDate(row.created_at),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <Badge
          tone={
            row.status === 'APPROVED' ? 'success' : row.status === 'REJECTED' ? 'danger' : 'warning'
          }
        >
          {row.status}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) =>
        row.status === 'PENDING' ? (
          <Stack direction="horizontal" gap="sm">
            <Button
              size="sm"
              onClick={() =>
                void (async () => {
                  try {
                    await api.approveCancellationRequest(row._id)
                    setMessage('Request approved')
                    await load()
                  } catch (err) {
                    setError(getErrorMessage(err))
                  }
                })()
              }
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() =>
                void (async () => {
                  try {
                    await api.rejectCancellationRequest(row._id)
                    setMessage('Request rejected')
                    await load()
                  } catch (err) {
                    setError(getErrorMessage(err))
                  }
                })()
              }
            >
              Reject
            </Button>
          </Stack>
        ) : (
          '—'
        ),
    },
  ]

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="Staff"
        title="Cancellation requests"
        description="Review late cancellation requests for your hotels."
      />
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}
      {loading ? (
        <Spinner />
      ) : requests.length ? (
        <Table columns={columns} rows={requests} rowKey={(row) => row._id} />
      ) : (
        <EmptyState title="No cancellation requests" />
      )}
    </Stack>
  )
}

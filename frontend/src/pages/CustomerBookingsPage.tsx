import { useEffect, useState } from 'react'
import { BookingTable } from '../components/domain/BookingTable/BookingTable'
import { Alert, Button, FormField, Modal, PageHeader, Spinner, Stack, TextArea } from '../components/ui'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/format'
import type { Booking } from '../lib/types'

export function CustomerBookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([])
  const [pendingCancellationBookingIds, setPendingCancellationBookingIds] = useState<Set<string>>(
    new Set(),
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [selected, setSelected] = useState<Booking | null>(null)
  const [reason, setReason] = useState('Need to change travel plans')
  const [submitting, setSubmitting] = useState(false)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [bookingRows, pendingRequests] = await Promise.all([
        api.listMyBookings(),
        api.listMyCancellationRequests(),
      ])
      setBookings(bookingRows)
      setPendingCancellationBookingIds(
        new Set(pendingRequests.map((request) => request.booking_id)),
      )
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const onCancel = async (booking: Booking) => {
    setError('')
    setMessage('')
    try {
      await api.cancelBooking(booking._id)
      setMessage(`Cancelled ${booking.booking_ref}`)
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const onRequestCancel = async () => {
    if (!selected) return
    setSubmitting(true)
    setError('')
    try {
      await api.createCancellationRequest(selected._id, reason)
      setMessage(`Cancellation request submitted for ${selected.booking_ref}`)
      setSelected(null)
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="Customer"
        title="My bookings"
        description="Upcoming, completed, and cancelled stays in one place."
      />
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}
      {loading ? (
        <Spinner />
      ) : (
        <BookingTable
          bookings={bookings}
          pendingCancellationBookingIds={pendingCancellationBookingIds}
          onCancel={(booking) => void onCancel(booking)}
          onRequestCancel={(booking) => setSelected(booking)}
        />
      )}
      <Modal
        open={Boolean(selected)}
        title="Request cancellation"
        onClose={() => setSelected(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSelected(null)}>
              Close
            </Button>
            <Button loading={submitting} onClick={() => void onRequestCancel()}>
              Submit request
            </Button>
          </>
        }
      >
        <Stack>
          <p>Use this when the direct cancellation window has closed.</p>
          <FormField label="Reason" htmlFor="reason">
            <TextArea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          </FormField>
        </Stack>
      </Modal>
    </Stack>
  )
}

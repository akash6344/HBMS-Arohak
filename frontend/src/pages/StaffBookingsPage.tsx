import { useEffect, useState, type FormEvent } from 'react'
import { BookingTable } from '../components/domain/BookingTable/BookingTable'
import {
  Alert,
  Button,
  Card,
  FormField,
  Input,
  PageHeader,
  Select,
  Spinner,
  Stack,
} from '../components/ui'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/format'
import type { Booking, BookingStatus } from '../lib/types'
import styles from './pages.module.scss'

export function StaffBookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [customer, setCustomer] = useState('')
  const [bookingRef, setBookingRef] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      setBookings(
        await api.listStaffBookings({
          status: (status || undefined) as BookingStatus | undefined,
          customer: customer || undefined,
          booking_ref: bookingRef || undefined,
        }),
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

  const onFilter = (event: FormEvent) => {
    event.preventDefault()
    void load()
  }

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="Operations"
        title="Bookings"
        description="Search and filter bookings in your authorized scope."
      />
      <Card>
        <form onSubmit={onFilter}>
          <div className={styles.filters}>
            <FormField label="Status" htmlFor="status">
              <Select
                id="status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                options={[
                  { label: 'All', value: '' },
                  { label: 'Confirmed', value: 'CONFIRMED' },
                  { label: 'Cancelled', value: 'CANCELLED' },
                  { label: 'Completed', value: 'COMPLETED' },
                ]}
              />
            </FormField>
            <FormField label="Customer" htmlFor="customer">
              <Input
                id="customer"
                placeholder="Name or email"
                value={customer}
                onChange={(e) => setCustomer(e.target.value)}
              />
            </FormField>
            <FormField label="Booking ref" htmlFor="booking_ref">
              <Input
                id="booking_ref"
                value={bookingRef}
                onChange={(e) => setBookingRef(e.target.value)}
              />
            </FormField>
            <Button type="submit">Apply filters</Button>
          </div>
        </form>
      </Card>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {loading ? <Spinner /> : <BookingTable bookings={bookings} />}
    </Stack>
  )
}

import { useState } from 'react'
import { RoomCard } from '../components/domain/RoomCard/RoomCard'
import {
  SearchRoomsForm,
  type RoomSearchValues,
} from '../components/domain/SearchRoomsForm/SearchRoomsForm'
import { Alert, Card, EmptyState, PageHeader, Spinner, Stack } from '../components/ui'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/format'
import type { Room } from '../lib/types'
import styles from './pages.module.scss'

export function CustomerSearchPage() {
  const [rooms, setRooms] = useState<Room[]>([])
  const [search, setSearch] = useState<RoomSearchValues | null>(null)
  const [loading, setLoading] = useState(false)
  const [bookingRoomId, setBookingRoomId] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const onSearch = async (values: RoomSearchValues) => {
    setLoading(true)
    setError('')
    setMessage('')
    setSearch(values)
    try {
      const results = await api.searchRooms({
        check_in: values.check_in,
        check_out: values.check_out,
        guests: values.guests,
        city: values.city || undefined,
      })
      setRooms(results)
    } catch (err) {
      setRooms([])
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const onBook = async (room: Room) => {
    if (!search) return
    setBookingRoomId(room._id)
    setError('')
    setMessage('')
    try {
      const booking = await api.createBooking(
        {
          room_id: room._id,
          check_in_date: search.check_in,
          check_out_date: search.check_out,
          guest_count: search.guests,
        },
        crypto.randomUUID(),
      )
      setMessage(`Booked ${booking.booking_ref}. View it under My bookings.`)
      await onSearch(search)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBookingRoomId(null)
    }
  }

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="Customer"
        title="Find a room"
        description="Search live availability by dates, guests, and city."
      />
      <Card>
        <SearchRoomsForm loading={loading} onSubmit={(values) => void onSearch(values)} />
      </Card>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}
      {loading ? <Spinner label="Searching rooms…" /> : null}
      {!loading && search && rooms.length === 0 ? (
        <EmptyState title="No rooms available" description="Try different dates or guest count." />
      ) : null}
      <div className={styles.grid}>
        {rooms.map((room) => (
          <RoomCard
            key={room._id}
            room={room}
            actionLabel="Book now"
            loading={bookingRoomId === room._id}
            onAction={(selected) => void onBook(selected)}
          />
        ))}
      </div>
    </Stack>
  )
}

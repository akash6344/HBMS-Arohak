import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { RoomCard } from '../components/domain/RoomCard/RoomCard'
import {
  Alert,
  Button,
  Card,
  FormField,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  Stack,
  TextArea,
} from '../components/ui'
import { useAuth } from '../auth/AuthContext'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/format'
import type { Hotel, Organization, Room } from '../lib/types'
import styles from './pages.module.scss'

export function StaffRoomsPage() {
  const { hasRole } = useAuth()
  const canMutate = hasRole('PRODUCT_ADMIN', 'ORG_ADMIN')
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [hotels, setHotels] = useState<Hotel[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [organizationId, setOrganizationId] = useState('')
  const [hotelId, setHotelId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    room_number: '',
    room_type: 'Deluxe',
    capacity: 2,
    price_per_night: 4500,
    description: '',
    amenities: 'WiFi, AC',
  })

  useEffect(() => {
    void (async () => {
      try {
        const orgs = await api.listOrganizations()
        setOrganizations(orgs)
        if (orgs[0]) setOrganizationId(orgs[0]._id)
      } catch (err) {
        setError(getErrorMessage(err))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  useEffect(() => {
    if (!organizationId) return
    void (async () => {
      try {
        const hotelList = await api.listHotels(organizationId)
        setHotels(hotelList)
        setHotelId(hotelList[0]?._id ?? '')
      } catch (err) {
        setError(getErrorMessage(err))
      }
    })()
  }, [organizationId])

  useEffect(() => {
    if (!hotelId) {
      setRooms([])
      return
    }
    void (async () => {
      try {
        setRooms(await api.listRooms(hotelId))
      } catch (err) {
        setError(getErrorMessage(err))
      }
    })()
  }, [hotelId])

  const orgOptions = useMemo(
    () => organizations.map((org) => ({ label: org.name, value: org._id })),
    [organizations],
  )
  const hotelOptions = useMemo(
    () => hotels.map((hotel) => ({ label: `${hotel.name} · ${hotel.city}`, value: hotel._id })),
    [hotels],
  )

  const onCreate = async (event: FormEvent) => {
    event.preventDefault()
    if (!hotelId) return
    setError('')
    try {
      await api.createRoom(hotelId, {
        room_number: form.room_number,
        room_type: form.room_type,
        capacity: form.capacity,
        price_per_night: form.price_per_night,
        currency: 'INR',
        description: form.description,
        amenities: form.amenities.split(',').map((item) => item.trim()).filter(Boolean),
      })
      setOpen(false)
      setMessage('Room created')
      setRooms(await api.listRooms(hotelId))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const onDeactivate = async (room: Room) => {
    try {
      await api.deactivateRoom(room.hotel_id, room._id)
      setMessage(`Deactivated room ${room.room_number}`)
      setRooms(await api.listRooms(hotelId))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  if (loading) return <Spinner />

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="Staff"
        title="Room inventory"
        description="Manage rooms for hotels in your organization scope."
        actions={
          canMutate ? (
            <Button onClick={() => setOpen(true)} disabled={!hotelId}>
              Add room
            </Button>
          ) : undefined
        }
      />
      <Card>
        <Stack direction="horizontal">
          <FormField label="Organization" htmlFor="organization">
            <Select
              id="organization"
              value={organizationId}
              options={orgOptions}
              onChange={(e) => setOrganizationId(e.target.value)}
            />
          </FormField>
          <FormField label="Hotel" htmlFor="hotel">
            <Select
              id="hotel"
              value={hotelId}
              options={hotelOptions.length ? hotelOptions : [{ label: 'No hotels', value: '' }]}
              onChange={(e) => setHotelId(e.target.value)}
            />
          </FormField>
        </Stack>
      </Card>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}
      <div className={styles.grid}>
        {rooms.map((room) => (
          <RoomCard
            key={room._id}
            room={room}
            actionLabel={canMutate && room.is_active ? 'Deactivate' : undefined}
            onAction={canMutate && room.is_active ? (selected) => void onDeactivate(selected) : undefined}
          />
        ))}
      </div>

      <Modal
        open={open}
        title="Add room"
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button form="create-room" type="submit">
              Save room
            </Button>
          </>
        }
      >
        <form id="create-room" onSubmit={(event) => void onCreate(event)}>
          <Stack>
            <FormField label="Room number" htmlFor="room_number">
              <Input
                id="room_number"
                required
                value={form.room_number}
                onChange={(e) => setForm((prev) => ({ ...prev, room_number: e.target.value }))}
              />
            </FormField>
            <FormField label="Room type" htmlFor="room_type">
              <Input
                id="room_type"
                required
                value={form.room_type}
                onChange={(e) => setForm((prev) => ({ ...prev, room_type: e.target.value }))}
              />
            </FormField>
            <FormField label="Capacity" htmlFor="capacity">
              <Input
                id="capacity"
                type="number"
                min={1}
                required
                value={form.capacity}
                onChange={(e) => setForm((prev) => ({ ...prev, capacity: Number(e.target.value) }))}
              />
            </FormField>
            <FormField label="Price per night" htmlFor="price">
              <Input
                id="price"
                type="number"
                min={0}
                required
                value={form.price_per_night}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, price_per_night: Number(e.target.value) }))
                }
              />
            </FormField>
            <FormField label="Description" htmlFor="description">
              <TextArea
                id="description"
                required
                value={form.description}
                onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              />
            </FormField>
            <FormField label="Amenities" htmlFor="amenities" hint="Comma separated">
              <Input
                id="amenities"
                value={form.amenities}
                onChange={(e) => setForm((prev) => ({ ...prev, amenities: e.target.value }))}
              />
            </FormField>
          </Stack>
        </form>
      </Modal>
    </Stack>
  )
}

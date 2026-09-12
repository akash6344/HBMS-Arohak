import { Badge, Button, Card } from '../../ui'
import { formatMoney } from '../../../lib/format'
import type { Room } from '../../../lib/types'
import styles from './RoomCard.module.scss'

interface RoomCardProps {
  room: Room
  actionLabel?: string
  onAction?: (room: Room) => void
  loading?: boolean
}

export function RoomCard({ room, actionLabel, onAction, loading }: RoomCardProps) {
  return (
    <Card className={styles.card} padded={false}>
      <div className={styles.body}>
        <div className={styles.top}>
          <div>
            {room.hotel_name ? (
              <p className={styles.hotel}>
                {room.hotel_name}
                {room.hotel_city ? ` · ${room.hotel_city}` : ''}
              </p>
            ) : null}
            <p className={styles.meta}>Room {room.room_number}</p>
            <h3>{room.room_type}</h3>
          </div>
          <Badge tone={room.is_active ? 'success' : 'danger'}>
            {room.availability_status}
          </Badge>
        </div>

        <p className={styles.description}>{room.description}</p>

        <p className={styles.meta}>
          {room.capacity} guests · {formatMoney(room.price_per_night, room.currency)} / night
        </p>

        <div className={styles.amenities}>
          {room.amenities.map((amenity) => (
            <Badge key={amenity}>{amenity}</Badge>
          ))}
        </div>

        {actionLabel && onAction ? (
          <div className={styles.actions}>
            <Button loading={loading} onClick={() => onAction(room)}>
              {actionLabel}
            </Button>
          </div>
        ) : null}
      </div>
    </Card>
  )
}

import { Badge } from '../../ui'
import type { BookingStatus } from '../../../lib/types'

const TONE: Record<BookingStatus, 'success' | 'danger' | 'neutral'> = {
  CONFIRMED: 'success',
  CANCELLED: 'danger',
  COMPLETED: 'neutral',
}

export function BookingStatusBadge({ status }: { status: BookingStatus }) {
  return <Badge tone={TONE[status]}>{status}</Badge>
}

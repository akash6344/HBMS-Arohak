import { Badge, Button, EmptyState, Table, type TableColumn } from '../../ui'
import { formatDate, formatMoney } from '../../../lib/format'
import type { Booking } from '../../../lib/types'
import { BookingStatusBadge } from '../BookingStatusBadge/BookingStatusBadge'

interface BookingTableProps {
  bookings: Booking[]
  emptyTitle?: string
  pendingCancellationBookingIds?: Set<string>
  onCancel?: (booking: Booking) => void
  onRequestCancel?: (booking: Booking) => void
}

function isDirectCancelAllowed(booking: Booking): boolean {
  const deadline = new Date(booking.cancellation_deadline_at)
  if (Number.isNaN(deadline.getTime())) {
    return false
  }
  return Date.now() <= deadline.getTime()
}

export function BookingTable({
  bookings,
  emptyTitle = 'No bookings yet',
  pendingCancellationBookingIds,
  onCancel,
  onRequestCancel,
}: BookingTableProps) {
  if (!bookings.length) {
    return <EmptyState title={emptyTitle} description="New bookings will appear here." />
  }

  const columns: TableColumn<Booking>[] = [
    {
      key: 'ref',
      header: 'Reference',
      render: (row) => row.booking_ref,
    },
    {
      key: 'dates',
      header: 'Stay',
      render: (row) => `${formatDate(row.check_in_date)} → ${formatDate(row.check_out_date)}`,
    },
    {
      key: 'guests',
      header: 'Guests',
      render: (row) => row.guest_count,
    },
    {
      key: 'amount',
      header: 'Total',
      render: (row) => formatMoney(row.total_amount, row.currency),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <BookingStatusBadge status={row.status} />,
    },
  ]

  if (onCancel || onRequestCancel || pendingCancellationBookingIds) {
    columns.push({
      key: 'actions',
      header: 'Actions',
      render: (row) => {
        if (row.status !== 'CONFIRMED') {
          return '—'
        }

        if (pendingCancellationBookingIds?.has(row._id)) {
          return <Badge tone="warning">Cancel requested</Badge>
        }

        if (isDirectCancelAllowed(row)) {
          return onCancel ? (
            <Button size="sm" variant="secondary" onClick={() => onCancel(row)}>
              Cancel
            </Button>
          ) : (
            '—'
          )
        }

        return onRequestCancel ? (
          <Button size="sm" variant="ghost" onClick={() => onRequestCancel(row)}>
            Request cancel
          </Button>
        ) : (
          '—'
        )
      },
    })
  }

  return <Table columns={columns} rows={bookings} rowKey={(row) => row._id} />
}

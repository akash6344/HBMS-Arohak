export type Role = 'PRODUCT_ADMIN' | 'ORG_ADMIN' | 'RECEPTIONIST' | 'CUSTOMER'

export type BookingStatus = 'CONFIRMED' | 'CANCELLED' | 'COMPLETED'
export type CancellationRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED'
export type EntityStatus = 'ACTIVE' | 'INACTIVE'
export type RoomAvailabilityStatus = 'AVAILABLE' | 'UNAVAILABLE' | 'MAINTENANCE'

export interface AuthenticatedPrincipal {
  user_id: string
  role: Role
  organization_ids: string[]
  hotel_ids: string[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Organization {
  _id: string
  name: string
  status: EntityStatus
  created_at: string
  updated_at: string
}

export interface Hotel {
  _id: string
  organization_id: string
  name: string
  address: string
  city: string
  description: string
  contact_number: string
  email: string
  timezone: string
  status: EntityStatus
  created_at: string
  updated_at: string
}

export interface Room {
  _id: string
  organization_id: string
  hotel_id: string
  hotel_name?: string | null
  hotel_city?: string | null
  room_number: string
  room_type: string
  capacity: number
  price_per_night: string | number
  currency: string
  availability_status: RoomAvailabilityStatus
  is_active: boolean
  description: string
  amenities: string[]
  created_at: string
  updated_at: string
}

export interface Booking {
  _id: string
  booking_ref: string
  organization_id: string
  hotel_id: string
  room_id: string
  customer_id: string
  check_in_date: string
  check_out_date: string
  guest_count: number
  booking_date: string
  nightly_rate_snapshot: string | number
  currency: string
  total_amount: string | number
  status: BookingStatus
  cancellation_deadline_at: string
  created_at: string
  updated_at: string
}

export interface CancellationRequest {
  _id: string
  booking_id: string
  organization_id: string
  hotel_id: string
  requested_by: string
  reason: string
  status: CancellationRequestStatus
  reviewed_by: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface UserRead {
  _id: string
  name: string
  email: string
  role: Role
  created_at: string
  updated_at: string
}

export interface RagHotelOption {
  organization_id: string
  hotel_id: string
  hotel_name: string
  city: string
  source_file?: string | null
  chunk_count: number
}

export interface RagCitation {
  section: string
  page_start: number
  page_end: number
  score: number
  excerpt: string
}

export interface RagAskResponse {
  answer: string
  grounded: boolean
  hotel_id: string
  organization_id: string
  citations: RagCitation[]
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

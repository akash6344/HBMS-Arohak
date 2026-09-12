import { tokenStorage } from './storage'
import {
  ApiError,
  type AuthenticatedPrincipal,
  type Booking,
  type BookingStatus,
  type CancellationRequest,
  type CancellationRequestStatus,
  type Hotel,
  type Organization,
  type RagAskResponse,
  type RagHotelOption,
  type Room,
  type TokenResponse,
  type UserRead,
} from './types'

const API_BASE = '/api/v1'

async function parseError(response: Response): Promise<ApiError> {
  try {
    const data = (await response.json()) as { detail?: string | Array<{ msg?: string }> }
    if (typeof data.detail === 'string') {
      return new ApiError(response.status, data.detail)
    }
    if (Array.isArray(data.detail) && data.detail[0]?.msg) {
      return new ApiError(response.status, data.detail[0].msg)
    }
  } catch {
    // fall through
  }
  return new ApiError(response.status, `Request failed (${response.status})`)
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  const accessToken = tokenStorage.getAccess()
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (response.status === 401 && retry && tokenStorage.getRefresh()) {
    const refreshed = await refreshTokens()
    if (refreshed) {
      return request<T>(path, options, false)
    }
  }

  if (!response.ok) {
    throw await parseError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

async function refreshTokens(): Promise<boolean> {
  const refreshToken = tokenStorage.getRefresh()
  if (!refreshToken) {
    return false
  }

  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) {
      tokenStorage.clear()
      return false
    }
    const data = (await response.json()) as TokenResponse
    tokenStorage.setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    tokenStorage.clear()
    return false
  }
}

export const api = {
  register(payload: { name: string; email: string; password: string }) {
    return request<UserRead>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  login(payload: { email: string; password: string }) {
    return request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  logout(refreshToken: string) {
    return request<{ status: string }>('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  },
  me() {
    return request<AuthenticatedPrincipal>('/auth/me')
  },
  listOrganizations() {
    return request<Organization[]>('/organizations')
  },
  createOrganization(payload: { name: string }) {
    return request<Organization>('/organizations', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  listHotels(organizationId: string) {
    return request<Hotel[]>(`/organizations/${organizationId}/hotels`)
  },
  createHotel(
    organizationId: string,
    payload: {
      name: string
      address: string
      city: string
      description: string
      contact_number: string
      email: string
      timezone: string
    },
  ) {
    return request<Hotel>(`/organizations/${organizationId}/hotels`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  listRooms(hotelId: string) {
    return request<Room[]>(`/hotels/${hotelId}/rooms`)
  },
  createRoom(
    hotelId: string,
    payload: {
      room_number: string
      room_type: string
      capacity: number
      price_per_night: number
      currency: string
      description: string
      amenities: string[]
    },
  ) {
    return request<Room>(`/hotels/${hotelId}/rooms`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  deactivateRoom(hotelId: string, roomId: string) {
    return request<Room>(`/hotels/${hotelId}/rooms/${roomId}/deactivate`, {
      method: 'POST',
    })
  },
  searchRooms(params: {
    check_in: string
    check_out: string
    guests: number
    city?: string
    organization_id?: string
    hotel_id?: string
  }) {
    const query = new URLSearchParams({
      check_in: params.check_in,
      check_out: params.check_out,
      guests: String(params.guests),
    })
    if (params.city) query.set('city', params.city)
    if (params.organization_id) query.set('organization_id', params.organization_id)
    if (params.hotel_id) query.set('hotel_id', params.hotel_id)
    return request<Room[]>(`/search/rooms?${query.toString()}`)
  },
  createBooking(
    payload: {
      room_id: string
      check_in_date: string
      check_out_date: string
      guest_count: number
    },
    idempotencyKey?: string,
  ) {
    return request<Booking>('/bookings', {
      method: 'POST',
      body: JSON.stringify(payload),
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
    })
  },
  listMyBookings() {
    return request<Booking[]>('/bookings')
  },
  listMyCancellationRequests() {
    return request<CancellationRequest[]>('/bookings/cancellation-requests')
  },
  cancelBooking(bookingId: string) {
    return request<Booking>(`/bookings/${bookingId}/cancel`, { method: 'POST' })
  },
  createCancellationRequest(bookingId: string, reason: string) {
    return request<CancellationRequest>(`/bookings/${bookingId}/cancellation-requests`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    })
  },
  listStaffBookings(params: {
    status?: BookingStatus
    from?: string
    to?: string
    hotel_id?: string
    customer?: string
    booking_ref?: string
  } = {}) {
    const query = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value) query.set(key, value)
    })
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request<Booking[]>(`/staff/bookings${suffix}`)
  },
  listCancellationRequests(status?: CancellationRequestStatus) {
    const suffix = status ? `?status=${status}` : ''
    return request<CancellationRequest[]>(`/staff/cancellation-requests${suffix}`)
  },
  approveCancellationRequest(requestId: string) {
    return request<CancellationRequest>(`/staff/cancellation-requests/${requestId}/approve`, {
      method: 'POST',
    })
  },
  rejectCancellationRequest(requestId: string) {
    return request<CancellationRequest>(`/staff/cancellation-requests/${requestId}/reject`, {
      method: 'POST',
    })
  },
  createOrgAdmin(payload: {
    organization_id: string
    name: string
    email: string
    password: string
  }) {
    return request<UserRead>('/staff/org-admins', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  createReceptionist(payload: {
    name: string
    email: string
    password: string
    hotel_ids: string[]
  }) {
    return request<UserRead>('/staff/receptionists', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  listRagHotels() {
    return request<RagHotelOption[]>('/ai/rag/hotels')
  },
  askRag(payload: { hotel_id: string; question: string }) {
    return request<RagAskResponse>('/ai/rag/ask', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}

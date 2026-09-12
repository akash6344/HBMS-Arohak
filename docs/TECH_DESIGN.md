# Hotel Booking Management System — Technical Design

**Status:** Design approved target, implementation pending  
**Scope in build now:** Mandatory MVP + Core Extensions through multi-tenant architecture  
**AI scope in this document:** Architecture-ready only; do not implement AI features yet

---

## 1) Confirmed technology choices

Based on your decisions:

- **Backend:** Python + FastAPI
- **Frontend:** React + Vite + TypeScript + CSS/SCSS
- **Database:** MongoDB (Atlas) with Atlas Vector Search
- **Auth:** Self-managed JWT (access + refresh)
- **LLM direction (future):** Mistral
- **Cancellation policy (confirmed):** End-of-day before check-in, hotel-local timezone
- **Deployment decision:** Deferred until MVP/Core is stable

---

## 2) Architecture goals

1. **Tenant-safe from day one**  
   Schema and API paths are tenant-scoped from the first commit. A one-hotel demo dataset is only a test-data size choice and does not change capabilities.

2. **Booking correctness under race conditions**  
   Prevent overlapping bookings at the database level so concurrent requests cannot double-book.

3. **AI-ready service boundary**  
   The future chatbot calls existing application services through controlled tools. No direct DB access for models.

4. **Low rework migration path**  
   Mandatory MVP artifacts (auth, rooms, bookings) remain unchanged when enabling multiple organizations.

---

## 3) High-level system design

### 3.1 Logical components

- **Web App (React + Vite)**  
  Role-based UI for customer and staff flows: auth, room browsing, booking, cancellation, dashboards.

- **API Service (FastAPI)**  
  REST endpoints + service layer + authorization policy layer + idempotency middleware.

- **MongoDB Atlas**  
  Primary transactional and document store for tenant-scoped booking data and vectorized RAG chunks.

- **Background Jobs (FastAPI worker / scheduler)**  
  Marks completed bookings after check-out date, optional cleanup tasks.

- **Future AI Gateway (not built now)**  
  Tool executor process exposing controlled functions such as `search_rooms`, `create_booking`, etc.

### 3.2 Layered backend structure

- `api/` — route handlers, request/response schemas
- `auth/` — token issue/refresh/revoke, password hashing, session checks
- `policy/` — role and scope authorization rules
- `services/` — booking logic, availability calculations, cancellation logic
- `repositories/` — tenant-scoped query objects
- `db/` — Mongo models/schemas + migration scripts
- `jobs/` — scheduled status transitions
- `audit/` — immutable event logging
- `ai_tools/` — future controlled tool contracts (interfaces only in this phase)

---

## 4) Multi-tenant domain model

### 4.1 Hierarchy

`Platform -> Organization -> Hotel -> Room -> Booking`

### 4.2 Core entities

- **Organization**
  - `id`, `name`, `status`, `created_at`
- **Hotel**
  - `id`, `organization_id`, `name`, `address`, `city`, `description`, `contact_number`, `email`, `status`, `timezone`
- **Room**
  - `id`, `organization_id`, `hotel_id`, `room_number`, `room_type`, `capacity`, `price_per_night`, `currency`, `availability_status`, `is_active`, `description`
- **RoomAmenity**
  - `room_id`, `amenity` (normalized list)
- **User**
  - `id`, `name`, `email`, `password_hash`, `role`, `status`, `created_at`
- **UserOrganizationMembership**
  - `user_id`, `organization_id`, `role_in_org` (for Org Admin / staff)
- **ReceptionistHotelAssignment**
  - `user_id`, `hotel_id`
- **Booking**
  - `id`, `booking_ref`, `organization_id`, `hotel_id`, `room_id`, `customer_id`, `check_in_date`, `check_out_date`, `guest_count`, `booking_date`, `nightly_rate_snapshot`, `currency`, `total_amount`, `status`, `cancellation_deadline_at`
- **CancellationRequest**
  - `id`, `booking_id`, `requested_by`, `reason`, `status`, `reviewed_by`, `reviewed_at`
- **AuthSession / RefreshToken**
  - `id`, `user_id`, `token_hash`, `expires_at`, `revoked_at`
- **AuditEvent**
  - `id`, `actor_user_id`, `entity_type`, `entity_id`, `action`, `before_json`, `after_json`, `created_at`

### 4.3 Tenant key strategy

- `organization_id` is present on all tenant-owned documents (`hotels`, `rooms`, `bookings`, future `hotel_documents` and `document_chunks`).
- Use compound indexes beginning with `organization_id` for all frequent tenant-scoped reads.
- All repository methods require a `TenantContext`.

---

## 5) Authorization and access control model

### 5.1 Roles

- `PRODUCT_ADMIN`
- `ORG_ADMIN`
- `RECEPTIONIST`
- `CUSTOMER`

### 5.2 Access policy

- **Product Admin**
  - Full platform scope: organizations + platform analytics
- **Organization Admin**
  - Full scope within one organization
- **Receptionist**
  - Limited to explicitly assigned hotels
- **Customer**
  - Can browse active organizations/hotels/rooms and manage only own bookings

### 5.3 Enforcement rules

1. **Endpoint guard** checks role category.
2. **Service guard** checks ownership/scope.
3. **Repository filter** always applies tenant and assignment predicates.

Even if UI or API params are manipulated, data outside scope is not returned.

---

## 6) Booking and availability design

### 6.1 Availability logic

A room is bookable only when:

- room `is_active = true`
- room `availability_status = AVAILABLE`
- hotel `status = ACTIVE`
- room `capacity >= requested_guests`
- no blocking booking overlaps requested stay

Date interval semantics: **half-open** range `[check_in, check_out)`.

### 6.2 Overlap prevention (critical)

MongoDB has no native exclusion constraint for date-range overlap, so we enforce correctness with a transactional locking pattern:

- Create a `room_inventory_days` collection keyed by `(organization_id, hotel_id, room_id, date)`.
- During booking, expand `[check_in, check_out)` into per-night dates.
- In one transaction:
  - insert lock documents for each date using unique key `(room_id, date)` (tenant fields included)
  - if any insert conflicts, abort and return `409 Conflict`
  - only then insert booking as `CONFIRMED`
- On cancellation of a confirmed booking, release corresponding day-lock documents.

This gives a database-backed guarantee of no overlap under concurrent writes.

### 6.3 Simultaneous booking attempts

Booking create flow:

1. Validate payload and scope.
2. Start transaction.
3. Recheck room state and capacity.
4. Insert booking (`CONFIRMED` attempt).
5. On day-lock conflict:
   - rollback cleanly
   - return `409 Conflict` with structured reason.

Result: exactly one success among concurrent conflicting requests.

### 6.4 Idempotency

Support `Idempotency-Key` header on booking creation:

- unique by `(customer_id, endpoint, idempotency_key)`
- first successful response cached
- retries return original response without second insert

Useful for both UI retries and future AI tool retries.

---

## 7) Cancellation policy and state machine

### 7.1 Booking status enum (fixed by requirement)

- `CONFIRMED`
- `CANCELLED`
- `COMPLETED`

### 7.2 Deadline rule (confirmed)

`cancellation_deadline_at = end_of_day(check_in_date - 1 day, hotel_timezone)`

Persist this at booking creation time.

### 7.3 Cancellation flow

- If now <= deadline: direct cancellation, booking becomes `CANCELLED`.
- If now > deadline: create `CancellationRequest` with `PENDING`.
- Staff can `APPROVE` or `REJECT` request.
- Approval transitions booking to `CANCELLED`.

---

## 8) API surface (Phase 1+2)

### 8.1 Auth

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

### 8.2 Platform / organization management

- `POST /organizations` (Product Admin)
- `GET /organizations`
- `PATCH /organizations/{id}`
- `POST /organizations/{id}/hotels`
- `GET /organizations/{id}/hotels`

### 8.3 Room management

- `POST /hotels/{hotelId}/rooms`
- `GET /hotels/{hotelId}/rooms`
- `PATCH /hotels/{hotelId}/rooms/{roomId}`
- `POST /hotels/{hotelId}/rooms/{roomId}/deactivate`

### 8.4 Search and booking

- `GET /search/rooms?city=&organizationId=&hotelId=&checkIn=&checkOut=&guests=`
- `POST /bookings` (with idempotency key)
- `GET /bookings/{bookingId}`
- `GET /bookings?mine=true` (customer)
- `POST /bookings/{bookingId}/cancel`
- `POST /bookings/{bookingId}/cancellation-requests`

### 8.5 Staff dashboards

- `GET /staff/bookings?status=&from=&to=&hotelId=&customer=`
- `GET /staff/bookings/{bookingId}`
- `POST /staff/cancellation-requests/{requestId}/approve`
- `POST /staff/cancellation-requests/{requestId}/reject`

---

## 9) Database design and indexing

### 9.1 Important indexes

- `hotels`: `{ organization_id: 1, city: 1, status: 1 }`
- `rooms`: `{ organization_id: 1, hotel_id: 1, is_active: 1, availability_status: 1, capacity: 1 }`
- `bookings`: `{ organization_id: 1, hotel_id: 1, customer_id: 1, status: 1, check_in_date: 1 }`
- `bookings`: `{ room_id: 1, check_in_date: 1, check_out_date: 1 }`
- `receptionist_hotel_assignments`: unique `{ user_id: 1, hotel_id: 1 }`
- `idempotency_records`: unique `{ customer_id: 1, endpoint: 1, idempotency_key: 1 }`
- `room_inventory_days`: unique `{ organization_id: 1, hotel_id: 1, room_id: 1, date: 1 }`

### 9.2 Data isolation patterns

- Never query tenant records by bare `id`.
- Always include organization predicate.
- For receptionist routes, include assignment join predicate.

---

## 10) Frontend technical design

### 10.1 App structure

- React + Vite + TypeScript
- Route groups:
  - `/auth/*`
  - `/customer/*`
  - `/staff/*`
  - `/platform/*`
- Role-aware navigation from `/me` claims

### 10.2 State and networking

- Query caching for lists/search (TanStack Query recommended)
- Form validation on client + server
- Token refresh interceptor with silent retry

### 10.3 UI requirements mapping

- Customer:
  - room search form (dates + guests + optional city/hotel)
  - room list cards with all required fields
  - booking confirmation screen with required attributes
  - booking dashboard (upcoming/history/cancelled)
- Staff:
  - room management tables/forms
  - booking dashboard with search/filter
  - cancellation request review

---

## 11) AI extension readiness (architecture only)

No AI implementation now. But the following contracts are defined early so Phase 3 can plug in quickly.

### 11.1 Tool interface contract

Future tool names (aligned with assignment):

- `search_rooms`
- `check_availability`
- `get_booking`
- `create_booking`
- `cancel_booking`

Each tool:

- accepts a `PrincipalContext` (caller identity, role, tenant scope)
- calls existing service methods
- returns typed JSON responses
- never executes direct database commands from model output

### 11.2 Why this works for Mistral

Mistral supports structured function/tool calling. We can enforce:

- schema-validated arguments
- deterministic tool routing
- explicit refusal when tool data is missing

### 11.3 RAG readiness for hotel PDFs

Collections:

- `hotel_documents (id, organization_id, hotel_id, source_file, version, uploaded_by, uploaded_at)`
- `hotel_document_chunks (id, organization_id, hotel_id, document_id, chunk_text, embedding_text, embedding[1024], section, page_start, page_end, chunk_index, metadata_json)`

#### Chosen ingest strategy (research-backed)

For the AROHAK hotel policy PDF (short, heading-structured, FAQ + tables), use **heading/section-aware chunking with recursive size fallback** — not naive fixed windows and not embedding-based semantic chunking.

Evidence used:

- Heading/structure-aware chunking beats fixed-size by ~12–18% recall on structured PDFs; pure semantic boundaries add ~2% at much higher preprocess cost ([pdfmux comparison](https://pdfmux.com/blog/pdf-chunking-strategies-rag/)).
- Large-scale eval favors content-aware / paragraph-group strategies over naive character splits ([arXiv:2603.06976](https://arxiv.org/html/2603.06976v1)).
- Policy/reference corpora work best with section-aware splits + section titles carried into each child chunk ([Edtek legal/reference guidance](https://edtek.ai/kb/chunking-strategies-legal-reference-documents/)).
- MongoDB Atlas RAG tutorials recommend recursive splitting plus **tenant metadata filters** on the vector query.

Pipeline steps:

1. Extract page-aware text (`pypdf`), strip page boilerplate headers/footers.
2. Split on numbered sections (`1. …`, `2. …`) and named subsections (e.g. Check-in Policy).
3. Keep FAQ as **one Q+A per chunk**; keep the room-category table intact as one chunk.
4. If a section exceeds ~1200 characters, recursively split on `\n\n` → `\n` → spaces with ~15% overlap (~180 chars).
5. Build `embedding_text = "[Section Title]\n{chunk}"` so the vector carries section context.
6. Embed with `mistral-embed` (1024-d), store in Mongo, filter retrieval by `(organization_id, hotel_id)`.
7. Answer only from retrieved chunks; refuse when evidence is missing.

Notes:

- `mistral-embed` dimensions: **1024**.
- Retrieval query always includes `(organization_id, hotel_id)` from selected hotel context, and the Atlas vector index search is post-filtered by these fields in the same query pipeline.
- If no relevant chunk exists, assistant returns “information unavailable in provided PDF”.

This directly satisfies “selected hotel PDF only” and prevents cross-hotel leakage.

---

## 12) Observability, testing, and quality gates

### 12.1 Logging and audit

- Structured JSON logs with request ID and user ID.
- Audit every booking create/update/cancel transition.
- Audit every future AI tool invocation.

### 12.2 Test strategy

- **Unit tests**
  - date overlap logic
  - cancellation deadline computation across timezones
  - total amount computation
- **Integration tests**
  - auth and role guards
  - tenant isolation (org-admin and receptionist boundaries)
  - search filtering correctness
- **Concurrency tests**
  - N parallel booking requests for same room+interval -> 1 success, N-1 conflicts
- **E2E tests**
  - customer booking journey
  - staff manage bookings flow

### 12.3 Exit gates for current scope

1. All PRD acceptance criteria through ORG section pass.
2. Zero cross-tenant leak in automated tests.
3. Double-booking impossible under stress test.
4. Seed data allows reviewer to test all roles quickly.

---

## 13) Key implementation sequence (recommended)

1. Create schema with full tenant keys from day one.
2. Implement auth and role-aware principal extraction.
3. Implement hotel and room CRUD with policy guards.
4. Implement search + booking with transactional day-locking and idempotency.
5. Implement cancellation and request flow.
6. Implement dashboards and filter endpoints.
7. Enable multi-organization management and assignments.
8. Add AI tool interface stubs (no model calls yet).

---

## 14) Risks and mitigations

1. **Risk:** Hidden tenant leaks via helper queries  
   **Mitigation:** repository APIs require `TenantContext`; no global unscoped helpers.

2. **Risk:** Ambiguous date/time handling causes wrong cancellation behavior  
   **Mitigation:** store hotel timezone; compute and persist deadline at create time; timezone tests.

3. **Risk:** Race conditions in booking logic  
   **Mitigation:** transactional day-lock collection with unique keys + conflict handling.

4. **Risk:** AI phase accidentally bypasses auth  
   **Mitigation:** tool executor can call only app services requiring principal context.

---

## 15) Open decisions intentionally deferred

- Cloud deployment target/provider
- Queue technology (if future async jobs become heavy)
- AI model variant selection for chat (Mistral family chosen; exact model can be tuned by cost/performance later)

These do not block Phase 1+2 delivery.


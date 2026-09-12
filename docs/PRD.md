# Hotel Booking Management System — Product Requirements Document

**Project:** AROHAK Hackathon Hiring — Hotel Booking Management System
**Source:** `AROHAK Hackathon Hiring — Problem Statement` (4 pages, transcribed in [Appendix A](#appendix-a--verbatim-requirement-transcription))
**Status:** Draft for approval — no implementation started
**Build scope of this document:** Everything through the Multi-Organization model (63 of 100 marks). The AI extensions (37 marks) are specified here only to the depth needed to prove the architecture accommodates them without rework.

---

## 1. Objective

Build a hotel booking management system that lets users register and log in, manages hotel rooms, exposes searchable availability, takes bookings, and handles cancellations across isolated organizations, and finally exposes the same capabilities through an AI chat interface.

## 2. How the challenge is scored

| # | Requirement block | Marks | Phase | In build scope now |
|---|---|---|---|---|
| 1 | User Authentication & Roles | 15 | 1 (Mandatory MVP) | Yes |
| 2 | Single Hotel & Room Management | 15 | 1 (Mandatory MVP) | Yes |
| 3 | Customer Hotel Booking | 20 | 1 (Mandatory MVP) | Yes |
| 4 | Booking Management Dashboards | 3 | 2 (Core Extension) | Yes |
| 5 | Multi-Organization Architecture | 10 | 2 (Core Extension) | Yes |
| 6 | AI Chatbot — Booking Management | 20 | 3 (AI Extension) | Design only |
| 7 | AI Chatbot — RAG over PDF | 17 | 3 (AI Extension) | Design only |
| | **Total** | **100** | | **63 marks buildable now** |

All three Mandatory MVP blocks must be complete before extensions are attempted. Both extension tracks may be attempted; the maximum score is 100.

## 3. Product principles

These are the judgement calls that resolve ambiguity everywhere else in the document.

1. **Multi-tenancy is structural from commit one.** The problem statement already lists `Organization ID` as a booking field in the *MVP* section. The system ships with tenant scope in every table, query, and permission check. A minimal demo dataset may contain one organization and one hotel, but this is a data quantity choice, not a capability boundary.
2. **Availability is derived, never asserted.** A room's bookability is computed from its active flag, its operational status, and the set of overlapping bookings. No cached "is booked" boolean is a source of truth.
3. **Correctness under concurrency beats feature count.** "Handle simultaneous booking attempts safely" is an explicit requirement; a double-booking is a hard failure regardless of how much else works.
4. **The AI layer is a client, not a second implementation.** Every AI tool call routes through the same application service and the same authorization check as the equivalent REST call. There is no privileged path to the database for the model.
5. **Grounded or silent.** Both chatbots must decline rather than guess — no invented availability, no invented policy.

## 4. Personas and roles

| Role | Scope | Created by | Primary jobs |
|---|---|---|---|
| **Customer** | Platform-wide (not owned by an organization) | Public self-registration | Browse organizations and hotels, search rooms by date and guest count, book, view own bookings, cancel within policy or request cancellation |
| **Receptionist** | Assigned hotel(s) within one organization | Organization Admin | View and manage rooms, availability, bookings and cancellations for assigned hotels only |
| **Organization Admin** | One organization, all of its hotels | Product Admin | Manage the organization, create and manage hotels and rooms, assign receptionists, view all bookings in the organization |
| **Product Admin** | Entire platform | Seeded | Create, manage and view organizations; platform-level reporting |

**Deliberate design decisions on roles:**

- A **Customer is intentionally not scoped to an organization.** They shop across the whole platform (`browse organization → hotel → rooms → availability → book`), so organization scope attaches to the *booking*, not to the customer account.
- **Receptionists do not get Admin-level functionality**, as stated. Concretely: no hotel create/delete, no room create/delete, no staff management, no organization settings. They operate rooms and bookings for hotels they are assigned to.
- **Customers cannot modify room information** — the room write API is closed to the Customer role at the authorization layer, not merely hidden in the UI.
- The registration form exposes a Role field as specified, **but self-registration can only mint a Customer.** Allowing an anonymous visitor to self-assign Admin would be a privilege-escalation hole. Staff accounts are created by the tier above them (or via a signed invite token). Seeded demo accounts for every role will be documented in the README so a reviewer can exercise each role immediately.

## 5. Phase 1 — Mandatory MVP (50 marks)

### 5.1 User Authentication & Roles — 15 marks

**Registration fields:** Name, Email, Password, Role.
**Login fields:** Email Address, Password.

**User stories**

- As a visitor, I can register with name, email, password and receive a Customer account.
- As a registered user, I can log in with email and password and receive a session bound to my role and scope.
- As any user, I am refused access to any capability outside my role, whether I reach for it through the UI or directly through the API.

**Acceptance criteria**

| ID | Criterion |
|---|---|
| AUTH-1 | Email is unique, case-insensitively normalized, and format-validated. |
| AUTH-2 | Passwords are stored only as a salted Argon2id (or bcrypt) hash. A minimum-strength policy is enforced. |
| AUTH-3 | Login returns a short-lived access token plus a refresh token. Failed login returns an identical generic error for unknown-email and wrong-password cases. |
| AUTH-4 | The session carries the user's role and, for staff, their organization and assigned hotel IDs. |
| AUTH-5 | Every protected endpoint declares its required role. A Customer calling a staff endpoint receives `403`, not `404` or a partial result. |
| AUTH-6 | Direct-object access is scoped: requesting another user's booking by ID returns `404`, and it does so for exactly the same reason a nonexistent booking does. |
| AUTH-7 | Repeated failed logins from one source are rate-limited. |

### 5.2 Single Hotel & Room Management — 15 marks

The MVP acceptance run can use a minimal dataset with one organization and one hotel.

**Hotel fields:** Hotel ID, Hotel Name, Address, City, Description, Contact Number, Email Address, Status (Active / Inactive).
**Room fields:** Room ID, Room Number, Room Type, Number of Guests / Capacity, Price Per Night, Availability Status, Description, Amenities.

Authorized staff can add, view, update, manage availability, and deactivate rooms.

**Acceptance criteria**

| ID | Criterion |
|---|---|
| HOTEL-1 | Staff can create and update a hotel with all eight listed fields. |
| HOTEL-2 | An Inactive hotel is excluded from all customer-facing search and browse results. |
| ROOM-1 | Staff can create, read, update and deactivate rooms with all eight listed fields. Amenities are a multi-valued attribute, not free text, so they can be filtered and rendered as chips. |
| ROOM-2 | Room Number is unique within its hotel. |
| ROOM-3 | **Two separate concepts are modeled, not conflated.** `is_active` is the deactivate/lifecycle flag; `availability_status` is the operational flag (`AVAILABLE` / `UNAVAILABLE` / `MAINTENANCE`). Date-based availability is a third, purely derived thing computed from bookings. |
| ROOM-4 | **Inactive rooms cannot be booked** — enforced server-side at booking time, not only by filtering the list. |
| ROOM-5 | Deactivating a room does not cancel or corrupt its existing bookings; it only prevents new ones. |
| ROOM-6 | Price Per Night is a non-negative decimal with an explicit currency. Capacity is a positive integer. |

### 5.3 Customer Hotel Booking — 20 marks

**Search fields:** Check-in Date, Check-out Date, Number of Guests.
**Listings must show:** room number, room type, price, capacity, description, amenities, availability.
**Booking fields:** Booking ID, Customer ID, Organization ID, Hotel ID, Room ID, Check-in Date, Check-out Date, Number of Guests, Booking Date, Total Amount, Booking Status.

**Acceptance criteria — search**

| ID | Criterion |
|---|---|
| SEARCH-1 | Given a check-in date, check-out date and guest count, results contain only rooms that are active, operationally available, in an active hotel, with `capacity >= guests`, and with no overlapping blocking booking. |
| SEARCH-2 | Dates are validated: check-out is strictly after check-in, check-in is not in the past, and stay length is within a configured maximum. |
| SEARCH-3 | Date ranges are treated as half-open `[check-in, check-out)`. A stay ending on the 20th and a stay starting on the 20th **do not** conflict — same-day turnover is legal. |
| SEARCH-4 | Every listing renders all seven required attributes. |
| SEARCH-5 | The search API accepts optional city / organization / hotel filters from day one. The same endpoint supports both minimal demo data and full multi-organization usage, including the AI chatbot query pattern "a room in Mumbai", without redesign. |

**Acceptance criteria — booking**

| ID | Criterion |
|---|---|
| BOOK-1 | A booking persists all eleven required fields. |
| BOOK-2 | `Total Amount` = nights × nightly rate, where the rate is **snapshotted onto the booking**. A later price change must not retroactively alter a historical booking's total. |
| BOOK-3 | Guest count is re-validated against room capacity at write time. |
| BOOK-4 | **Overlapping bookings for the same room are impossible.** This is guaranteed by a database-level constraint, not only by an application pre-check. |
| BOOK-5 | **Simultaneous attempts are safe.** Two concurrent requests for the last available room produce exactly one `CONFIRMED` booking and one clean, actionable `409 Conflict` — never two bookings, never a `500`, never a partial write. |
| BOOK-6 | Booking creation is idempotent under a client-supplied idempotency key, so a double-clicked button or a retried AI tool call cannot create two bookings. |
| BOOK-7 | The confirmation shows booking ID, hotel, room, customer, dates, guest count, total amount and status. |
| BOOK-8 | A human-readable booking reference (e.g. `BK-2026-000123`) is issued alongside the internal ID, since the reference is quoted to customers and, later, to the chatbot. |

**Acceptance criteria — cancellation**

The rule as stated: *a customer can cancel up to 24 hours / one day before check-in. For a Sept 20 check-in, direct cancellation is allowed until Sept 19. After the deadline, the customer must submit a cancellation request.*

| ID | Criterion |
|---|---|
| CANCEL-1 | The deadline is computed and **stored on the booking at creation time** as `cancellation_deadline_at`, so a later policy change cannot silently alter the terms a customer already agreed to. |
| CANCEL-2 | **Confirmed rule:** `deadline = end of the day before the check-in date, in the hotel's local timezone`. This makes the worked example exact — a Sept 20 check-in is directly cancellable through all of Sept 19 (23:59:59 hotel-local). The stricter reading (`check-in datetime − 24h`) is left as a config toggle but is not the shipped default. |
| CANCEL-3 | Before the deadline, the customer cancels directly and the booking becomes `CANCELLED` immediately. |
| CANCEL-4 | After the deadline, direct cancellation is refused and the customer may instead submit a **cancellation request**, which staff approve or reject. |
| CANCEL-5 | A cancellation request is a **separate entity with its own `PENDING` / `APPROVED` / `REJECTED` status.** It is not a fourth booking status, because the required booking status enum has exactly three values. Approval is what transitions the booking to `CANCELLED`. |
| CANCEL-6 | Cancelling frees the dates immediately — a `CANCELLED` booking no longer blocks availability. |
| CANCEL-7 | Cancellation is only permitted on a `CONFIRMED` booking, and only by its owner or authorized staff. Cancelling twice is a no-op, not an error state. |

## 6. Phase 2 — Core Extensions (13 marks)

### 6.1 Booking Management Dashboards — 3 marks

**Booking status values:** `CONFIRMED`, `CANCELLED`, `COMPLETED`.

**Customer dashboard:** upcoming bookings, historical / completed bookings, cancelled bookings, and a detail view showing status.

**Staff dashboard:** authorized Admins and Receptionists see the customer bookings relevant to their scope, can search and filter them, and can view details and manage bookings where permitted.

| ID | Criterion |
|---|---|
| DASH-1 | Upcoming / historical / cancelled are derived from status plus dates, not from a manually maintained field. |
| DASH-2 | A booking becomes `COMPLETED` once its check-out date has passed, applied by a scheduled job so the state is consistent for every reader rather than computed differently in each view. |
| DASH-3 | The staff dashboard supports filtering by date range, status, hotel, room and customer, and searching by booking reference, customer name or email. |
| DASH-4 | Staff results are hard-scoped: an Organization Admin sees only their organization; a Receptionist sees only assigned hotels. The scope filter is applied in the data layer, so it cannot be bypassed by a crafted query parameter. |
| DASH-5 | Lists are paginated and sorted deterministically. |

### 6.2 Multi-Organization Architecture — 10 marks

**Hierarchy:** `Platform → Organization → Hotel → Room → Booking`

- **Product Admin:** create, manage and view organizations and appropriate platform-level information.
- **Organization Admin:** manage their organization, multiple hotels, rooms, and assign receptionists.
- **Data isolation:** users can access only authorized organizations and hotels. An Organization Admin cannot access another organization. A Receptionist can access only assigned hotel(s).
- Each hotel has its own rooms, availability, bookings and hotel information.
- **Customer flow:** browse organization → hotel → rooms → availability → book.

| ID | Criterion |
|---|---|
| ORG-1 | Product Admin can create an organization and provision its first Organization Admin. |
| ORG-2 | Organization Admin can manage multiple hotels within their organization and assign receptionists to specific hotels. |
| ORG-3 | **Cross-organization access is impossible.** Requesting another organization's hotel, room, booking or customer by ID returns `404` — indistinguishable from a nonexistent record, so IDs cannot be enumerated to probe for existence. |
| ORG-4 | A Receptionist assigned to Hotel A cannot read or write Hotel B's rooms or bookings even within the same organization. |
| ORG-5 | Customers browse and book across organizations; each booking records the organization that owns the hotel. |
| ORG-6 | Room numbers, availability, pricing and bookings are per-hotel; two hotels may both have a "Room 101" without collision. |
| ORG-7 | The same schema supports both a minimal demo dataset and larger real datasets, with no schema change or nullable-column backfill. |
| ORG-8 | An automated test suite asserts isolation for every tenant-scoped endpoint. This is the highest-risk requirement in the challenge and is verified exhaustively rather than spot-checked. |

## 7. Phase 3 — AI Extensions (37 marks) — specified, not built

Recorded now so the Phase 1–2 architecture provably supports them. Implementation is explicitly deferred.

### 7.1 AI Chatbot — Booking Management — 20 marks

An AI-powered booking assistant connected to actual booking data.

- Understand natural-language booking intent.
- Extract location, number of guests, check-in date and check-out date. Worked example: *"I need a room in Mumbai for 2 people from Sept 20 to Sept 23."*
- Check **actual** room availability and never invent availability.
- Assist with booking and management through chat, including upcoming bookings, booking details, and cancellation assistance.
- Use a **controlled tool/API layer** between the AI and the backend rather than unrestricted database access.
- Example backend tools: `search_rooms()`, `check_availability()`, `get_booking()`, `create_booking()`, `cancel_booking()`.

**Requirements this places on Phase 1–2 (all satisfied by the current design):**

| Need | Where it is already handled |
|---|---|
| Search by city, guests and date range in one call | SEARCH-5 |
| An availability answer that is authoritative | Derived availability + DB-level constraint (BOOK-4) |
| Safe retries when the model re-issues a call | Idempotency key (BOOK-6) |
| Booking lookup by a reference a human would say out loud | Booking reference (BOOK-8) |
| Cancellation that respects the deadline and falls back to a request | CANCEL-3 to CANCEL-5 |
| No privileged data path for the model | Tools call the same application services under the same `Principal` (Principle 4) |

### 7.2 AI Chatbot — RAG over PDF — 17 marks

A RAG chatbot answering customer questions strictly from an uploaded PDF.

- The PDF may contain hotel policies, cancellation policy, check-in/check-out rules, amenities, room information, FAQs, facilities and guidelines.
- Answer questions such as check-in time, Wi-Fi availability, cancellation policy, and parking.
- Retrieve relevant PDF context and ground answers in that context.
- If the requested information is not present in the PDF, **say it is unavailable rather than inventing an answer.**
- If multiple hotels are supported, use the **selected hotel's PDF only.**
- Any suitable RAG technology or approach is acceptable.

**The load-bearing constraint:** "use the selected hotel's PDF only" makes retrieval a **tenant-isolated** operation. Documents and their chunks are owned by a hotel inside an organization, and the hotel filter is applied in the retrieval query itself — never delegated to the model's judgement. This is the same isolation rule as ORG-3, extended to vector search.

## 8. Non-functional requirements

| Area | Requirement |
|---|---|
| Correctness | Zero double-bookings under concurrent load. Verified by a test that fires N simultaneous requests at one room and asserts exactly one success. |
| Isolation | Zero cross-tenant reads or writes. Verified per-endpoint by automated tests. |
| Performance | Room search p95 under 300 ms for a realistic seed (tens of hotels, hundreds of rooms, thousands of bookings). |
| Time correctness | All instants stored in UTC. Each hotel carries a timezone; stay dates are calendar dates in hotel-local time, and the cancellation deadline is computed in that timezone. |
| Money correctness | Decimal arithmetic only, never floating point. Explicit currency. Rate snapshotted per booking. |
| Auditability | Every state change on a booking, and every AI tool invocation, is recorded with actor, timestamp and before/after state. |
| Security | Hashed passwords, scoped tokens, server-side authorization on every route, parameterized queries only, no secrets in the repository. |
| Reviewability | One-command startup, seeded demo data, documented credentials for all four roles, and a written record of technical decisions — the problem statement warns that candidates may be asked to explain and defend their implementation. |

## 9. Out of scope

Payments and refunds (`Total Amount` is recorded, not charged), real check-in/check-out desk operations, housekeeping, pricing engines and seasonal rates, reviews, email/SMS delivery (confirmations are rendered in-app and logged), i18n, and native mobile apps.

## 10. Delivery plan

| Milestone | Contents | Marks | Exit criterion |
|---|---|---|---|
| M0 | Repo scaffold, schema with organization scope, migrations, seed, CI | 0 | One documented command brings up API, UI and database |
| M1 | Auth, roles, permission layer | 15 | All AUTH criteria pass |
| M2 | Hotel and room management | 30 | All HOTEL / ROOM criteria pass |
| M3 | Search, booking, cancellation, concurrency guarantees | 50 | All SEARCH / BOOK / CANCEL criteria pass, including the concurrency test |
| M4 | Customer and staff dashboards | 53 | All DASH criteria pass |
| M5 | Multi-organization architecture and isolation test suite | 63 | All ORG criteria pass |
| M6 | *(deferred)* AI booking agent | 83 | — |
| M7 | *(deferred)* RAG over per-hotel PDF | 100 | — |

M0–M5 is the scope authorized by this document. M6–M7 are pre-designed in the technical design so that starting them requires no change to M0–M5 code.

---

## Appendix A — Verbatim requirement transcription

Transcribed from the four source photographs so the requirement text is greppable and no detail is lost to paraphrase.

### Page 1

> **AROHAK Hackathon Hiring** — Problem Statement
> **Hotel Booking Management System**
> **Objective:** Build a hotel booking management system that lets users register and log in, manage hotel rooms, search available rooms, make bookings, and manage cancellations.
>
> **Challenge Structure**
> 1. Mandatory MVP — 50 Marks
> 2. Core Extensions — 13 Marks
> 3. High-Value AI Extensions — 37 Marks
>
> **Important:** Candidates must complete all three Mandatory MVP features first. After that, they can choose Core Extensions, High-Value AI Extensions, or both. Maximum score: 100.
>
> **I. Mandatory MVP — 50 Marks**
>
> **1. User Authentication & Roles — 15 Marks**
> Implement registration, login, and role-based access.
> *User Registration Fields:* Name, Email, Password, Role
> *Login Fields:* Email Address, Password
> *Roles and permissions:*
> - **Admin:** Manage hotel and rooms, availability, and relevant bookings.
> - **Receptionist:** View and manage rooms, availability, bookings, and cancellations.
> - **Customer:** Browse rooms, view room details, select dates, book rooms, view bookings, and cancel according to the cancellation rules.
>
> Customers cannot modify room information. Receptionists do not have Admin-level functionality.
>
> **2. Single Hotel & Room Management — 15 Marks**
> The MVP initially supports **one standalone hotel**.
> *Hotel Fields:* Hotel ID, Hotel Name, Address, City

### Page 2

> *(Hotel Fields continued:)* Description, Contact Number, Email Address, Status (Active / Inactive)
> Authorized staff can add, view, update, manage availability, and deactivate rooms.
> *Room Fields:* Room ID, Room Number, Room Type, Number of Guests / Capacity, Price Per Night, Availability Status, Description, Amenities
> Inactive rooms cannot be booked. Availability must consider existing bookings.
>
> **3. Customer Hotel Booking — 20 Marks**
> Customers can browse available rooms in the single hotel.
> *Search Fields:* Check-in Date, Check-out Date, Number of Guests
> Room listings must show room number, room type, price, capacity, description, amenities, and availability.
> *Booking Fields:* Booking ID, Customer ID, Organization ID, Hotel ID, Room ID, Check-in Date, Check-out Date, Number of Guests, Booking Date, Total Amount, Booking Status
> Prevent conflicting or overlapping bookings and handle simultaneous booking attempts safely.
> **Booking confirmation:** Include booking ID, hotel, room, customer, dates, guests, total amount, and booking status.
> **Cancellation:** A customer can cancel up to 24 hours / one day before check-in. Example: for a Sept 20 check-in, direct cancellation is allowed until Sept 19. After the deadline, the customer must submit a cancellation request.

### Page 3

> **II. Core Extensions — 13 Marks**
>
> **4. Booking Management Dashboards — 3 Marks**
> *Customer Dashboard:* Upcoming bookings; Historical / completed bookings; Cancelled bookings; View booking details and status
> *Staff Dashboard:* Authorized Admins and Receptionists can view relevant customer bookings; Search and filter bookings; View booking details and manage bookings where permitted
> *Booking Status Values:* CONFIRMED, CANCELLED, COMPLETED
>
> **5. Multi-Organization Architecture — 10 Marks**
> Upgrade the standalone system to support multiple isolated organizations.
> **Hierarchy:** Platform → Organization → Hotel → Room → Booking
> - **Product Admin:** Create, manage, and view organizations and appropriate platform-level information.
> - **Organization Admin:** Manage their organization, multiple hotels, rooms, and assign receptionists.
> - **Data isolation:** Users can access only authorized organizations and hotels. An Organization Admin cannot access another organization. A Receptionist can access only assigned hotel(s).
> - Each hotel has its own rooms, availability, bookings, and hotel information.
> - Customer flow can browse organization → hotel → rooms → availability → book.
>
> **III. High-Value AI Extensions — 37 Marks**
>
> **6. AI Chatbot — Booking Management — 20 Marks**
> Build an AI-powered booking assistant connected to actual booking data.
> - Understand natural-language booking intent.
> - Extract location, number of guests, check-in date, and check-out date.
> - Example: "I need a room in Mumbai for 2 people from Sept 20 to Sept 23."
> - Check actual room availability and never invent availability.
> - Assist with booking and management through chat, including upcoming bookings, booking details, and cancellation assistance.
> - Use a controlled tool/API layer between the AI and backend rather than unrestricted database access.
>
> **Example backend tools:** `search_rooms()`, `check_availability()`, `get_booking()`, `create_booking()`, `cancel_booking()`
>
> **7. AI Chatbot — RAG Based on PDF — 17 Marks**
> Build a RAG chatbot that answers customer questions strictly using information from an uploaded PDF.

### Page 4

> The PDF can contain hotel policies, cancellation policy, check-in/check-out rules, amenities, room information, FAQs, facilities, and guidelines.
> - Answer questions such as check-in time, Wi-Fi availability, cancellation policy, and parking.
> - Retrieve relevant PDF context and ground answers in that context.
> - If the requested information is not present in the PDF, say that it is unavailable rather than inventing an answer.
> - If multiple hotels are supported, use the selected hotel's PDF only.
> - Candidates may use suitable RAG technologies and approaches.
>
> **Technology**
> - Candidates are free to choose the frontend, backend, programming language, database, authentication approach, and deployment method.
>
> **AI-Assisted Development**
> - AI-assisted development is allowed and encouraged during the hackathon.
> - Candidates are responsible for understanding, testing, and validating the code they submit and may be asked to explain their implementation and technical decisions.

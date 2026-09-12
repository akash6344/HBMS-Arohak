import { NavLink, Outlet } from 'react-router-dom'
import { Button } from '../../ui'
import { useAuth } from '../../../auth/AuthContext'
import type { Role } from '../../../lib/types'
import styles from './AppShell.module.scss'

interface NavItem {
  to: string
  label: string
  roles: Role[]
}

interface NavSection {
  label: string
  items: NavItem[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    label: '',
    items: [
      { to: '/search', label: 'Search rooms', roles: ['CUSTOMER'] },
      { to: '/my-bookings', label: 'My bookings', roles: ['CUSTOMER'] },
      {
        to: '/hotel-info',
        label: 'Assistant',
        roles: ['CUSTOMER', 'PRODUCT_ADMIN', 'ORG_ADMIN', 'RECEPTIONIST'],
      },
    ],
  },
  {
    label: 'Operations',
    items: [
      {
        to: '/staff/bookings',
        label: 'Bookings',
        roles: ['PRODUCT_ADMIN', 'ORG_ADMIN', 'RECEPTIONIST'],
      },
      {
        to: '/staff/rooms',
        label: 'Rooms',
        roles: ['PRODUCT_ADMIN', 'ORG_ADMIN', 'RECEPTIONIST'],
      },
      {
        to: '/staff/cancellations',
        label: 'Cancellations',
        roles: ['PRODUCT_ADMIN', 'ORG_ADMIN', 'RECEPTIONIST'],
      },
    ],
  },
  {
    label: 'Workspace',
    items: [
      { to: '/platform/organizations', label: 'Organizations', roles: ['PRODUCT_ADMIN'] },
      { to: '/staff/team', label: 'Team', roles: ['PRODUCT_ADMIN', 'ORG_ADMIN'] },
    ],
  },
]

function roleLabel(role: string): string {
  return role
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function AppShell() {
  const { principal, logout, hasRole } = useAuth()
  const sections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => hasRole(...item.roles)),
  })).filter((section) => section.items.length > 0)

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brandBlock}>
          <div className={styles.brandMark}>H</div>
          <div>
            <p className={styles.brand}>HBMS</p>
            <p className={styles.brandMeta}>Hotel Booking</p>
          </div>
        </div>

        <nav className={styles.nav}>
          {sections.map((section) => (
            <div key={section.label || 'customer'} className={styles.section}>
              {section.label ? <p className={styles.sectionLabel}>{section.label}</p> : null}
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    [styles.navLink, isActive ? styles.active : ''].filter(Boolean).join(' ')
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userCard}>
            <div className={styles.avatar}>
              {(principal?.role?.[0] ?? 'U').toUpperCase()}
            </div>
            <div className={styles.userMeta}>
              <p className={styles.userRole}>{principal ? roleLabel(principal.role) : 'User'}</p>
              <p className={styles.userHint}>Signed in</p>
            </div>
          </div>
          <Button variant="secondary" size="sm" onClick={() => void logout()}>
            Log out
          </Button>
        </div>
      </aside>

      <div className={styles.content}>
        <header className={styles.topbar}>
          <p className={styles.topbarTitle}>Workspace</p>
        </header>
        <main className={styles.main}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

import { NavLink, Outlet, useLocation } from "react-router-dom";
import CandleIcon from "./CandleIcon.jsx";
import styles from "./Layout.module.css";

const desktopNavLinks = [
  { to: "/graph", label: "Графік" },
  { to: "/", label: "Головна", end: true },
  { to: "/info", label: "Про сервіс" },
  { to: "/faq", label: "FAQ" },
];

const mobileTabs = [
  {
    to: "/graph",
    label: "Графік",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
  },
  {
    to: "/",
    label: "Головна",
    end: true,
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
  },
  {
    to: "/info",
    label: "Інфо",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    ),
  },
  {
    to: "/faq",
    label: "FAQ",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
  },
  {
    to: "/donate",
    label: "Донат",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
      </svg>
    ),
  },
];

export default function Layout() {
  const { pathname } = useLocation();

  return (
    <div className={styles.shell}>
      <div className={styles.ambient} aria-hidden />

      {/* Sticky Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <NavLink to="/" className={styles.brand}>
            <div className={styles.logoMark}>
              <CandleIcon size={24} />
            </div>
            <div className={styles.brandText}>
              <span className={styles.logoTitle}>Likhtarychok</span>
              <span className={styles.logoSubtitle}>Графік відключень у Житомирі</span>
            </div>
          </NavLink>

          {/* Desktop Nav */}
          <nav className={styles.desktopNav}>
            {desktopNavLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          {/* Header Actions */}
          <div className={styles.actions}>
            {/* Telegram news channel */}
            <a
              href="https://t.me/likhtarychok_org"
              target="_blank"
              rel="noreferrer"
              className={styles.channelBtn}
              title="Новинний Telegram-канал @likhtarychok_org"
            >
              <svg
                className={styles.tgIcon}
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M21.5 2L2 9.5l7 3 2 6.5 3.5-3.5 5 3.5 2-17z" />
              </svg>
              <span className={styles.channelBtnText}>@likhtarychok_org</span>
              <span className={styles.channelBtnTextMobile}>Канал</span>
            </a>

            <NavLink
              to="/donate"
              title="Підтримати проєкт"
              aria-label="Підтримати проєкт"
              className={({ isActive }) =>
                `${styles.donateBtn} ${isActive ? styles.donateBtnActive : ""}`
              }
            >
              <span className={styles.heartIcon} aria-hidden>💛</span>
              <span className={styles.donateBtnText}>Підтримати</span>
            </NavLink>

            <NavLink
              to="/graph"
              className={`${styles.ctaBtn} ${pathname === "/graph" ? styles.ctaBtnActive : ""}`}
            >
              Графік
            </NavLink>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className={styles.main}>
        <Outlet />
      </main>

      {/* Mobile Bottom Navigation Bar */}
      <nav className={styles.mobileBottomNav} aria-label="Мобільна навігація">
        {mobileTabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `${styles.tabItem} ${isActive ? styles.tabItemActive : ""}`
            }
          >
            <div className={styles.tabIcon}>{tab.icon}</div>
            <span className={styles.tabLabel}>{tab.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <div className={styles.footerLogo}>
              <CandleIcon size={22} />
              <span className={styles.footerTitle}>Likhtarychok</span>
            </div>
            <p className={styles.footerCopy}>
              Онлайн-сервіс графіків погодинних відключень електроенергії у Житомирі та області.
              Швидка перевірка черги, зручний циферблат та завчасні сповіщення.
            </p>
          </div>

          <div className={styles.footerNav}>
            <div className={styles.footerCol}>
              <span className={styles.footerColTitle}>Розділи</span>
              <NavLink to="/graph" className={styles.footerLink}>Графік</NavLink>
              <NavLink to="/" className={styles.footerLink}>Головна</NavLink>
              <NavLink to="/info" className={styles.footerLink}>Про сервіс</NavLink>
              <NavLink to="/faq" className={styles.footerLink}>FAQ</NavLink>
              <NavLink to="/donate" className={styles.footerLink}>Підтримати проєкт</NavLink>
            </div>

            <div className={styles.footerCol}>
              <span className={styles.footerColTitle}>Контакти & Допомога</span>
              <a
                href="https://t.me/likhtarychok_org"
                target="_blank"
                rel="noreferrer"
                className={styles.footerLink}
              >
                Новинний канал (@likhtarychok_org)
              </a>
              <a
                href="https://t.me/likhtarychok_help_bot"
                target="_blank"
                rel="noreferrer"
                className={styles.footerLink}
              >
                Telegram-бот підтримки
              </a>
              <a
                href="https://t.me/younici"
                target="_blank"
                rel="noreferrer"
                className={styles.footerLink}
              >
                Зворотний зв&apos;язок (@younici)
              </a>
              <a
                href="mailto:kostantinreksha@gmail.com"
                className={styles.footerLink}
              >
                kostantinreksha@gmail.com
              </a>
              <NavLink to="/privacy" className={styles.footerLink}>
                Політика приватності
              </NavLink>
            </div>
          </div>

          <div className={styles.footerBottom}>
            <span>© 2025–2026 Likhtarychok. Дані: АТ «Житомиробленерго».</span>
            <span>Графік синхронізується кожні 5 хвилин</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

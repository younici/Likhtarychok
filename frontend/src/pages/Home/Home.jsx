import { Link } from "react-router-dom";
import styles from "./Home.module.css";

const highlights = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
    title: "Офіційні дані Житомиробленерго",
    body: "Пряма синхронізація розкладу кожні 5 хвилин. Ми конвертуємо складні списки у зрозумілий графік.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
    title: "Інтерактивний циферблат",
    body: "Наочний 24-годинний годинник показує поточну фазу, скільки годин лишилося до включення та розклад на день.",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
    title: "Пошук за адресою",
    body: "Введіть назву вулиці та номер будинку — сервіс миттєво підкаже вашу чергу (1.1 – 6.2).",
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    ),
    title: "Сповіщення за 1 годину",
    body: "Отримуйте нагадування про планові відключення у браузері або через Telegram-бота — без зайвого спаму.",
  },
];

const steps = [
  {
    step: "01",
    title: "Знайдіть свою чергу",
    body: "Скористайтеся пошуком за адресою або виберіть чергу вручну зі списку. Ми збережемо її у вашому браузері.",
  },
  {
    step: "02",
    title: "Слідкуйте за графіком",
    body: "Переглядайте графік у зручному форматі: інтерактивний циферблат, повна таблиця годин або слоти без світла.",
  },
  {
    step: "03",
    title: "Отримуйте сповіщення",
    body: "Дозвольте web push у браузері або підключіть Telegram-бота, щоб завжди бути напоготові.",
  },
];

export default function Home() {
  return (
    <div className={styles.page}>
      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.heroText}>
          <div className={styles.badge}>
            <span className={styles.pulseDot} />
            Онлайн-гід по відключеннях у Житомирі
          </div>
          <h1 className={styles.title}>
            Likhtarychok допомагає підготуватися до відключень світла
          </h1>
          <p className={styles.lead}>
            Швидкий пошук за адресою, наочний 24-годинний циферблат, оновлення кожні 5 хвилин
            та завчасні сповіщення. Усе, щоб ви завжди знали свій статус енергопостачання.
          </p>
          <div className={styles.actions}>
            <Link className={styles.primaryBtn} to="/graph">
              <span>Відкрити графік</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </Link>
            <Link className={styles.secondaryBtn} to="/info">
              Як працює сервіс
            </Link>
          </div>

          {/* Telegram News Channel Banner */}
          <a
            href="https://t.me/likhtarychok_org"
            target="_blank"
            rel="noreferrer"
            className={styles.channelBanner}
          >
            <div className={styles.channelBannerIcon}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.5 2L2 9.5l7 3 2 6.5 3.5-3.5 5 3.5 2-17z" />
              </svg>
            </div>
            <div className={styles.channelBannerText}>
              <div className={styles.channelBannerHeader}>
                <span className={styles.channelBannerTitle}>Новинний канал @likhtarychok_org</span>
                <span className={styles.channelBannerBadge}>Telegram</span>
              </div>
              <span className={styles.channelBannerSub}>
                Оперативні новини про відключення та оновлення графіків Житомиробленерго
              </span>
            </div>
            <svg className={styles.channelBannerArrow} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </a>

          <div className={styles.tags}>
            <span>Пошук за адресою</span>
            <span>24-год циферблат</span>
            <span>Web Push + Telegram</span>
            <span>Оновлення кожні 5 хв</span>
          </div>
        </div>

        {/* Hero Features Panel */}
        <div className={styles.heroPanel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>Можливості сервісу</span>
          </div>

          <div className={styles.panelGrid}>
            <div className={styles.panelCard}>
              <div className={styles.panelIcon} style={{ color: "var(--accent)" }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>
              <h3 className={styles.panelCardTitle}>Пошук черги за адресою</h3>
              <p className={styles.panelCardText}>
                Вкажіть вулицю і будинок у Житомирі — сервіс миттєво визначить номер вашої черги.
              </p>
            </div>

            <div className={styles.panelCard}>
              <div className={styles.panelIcon} style={{ color: "var(--cyan)" }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              </div>
              <h3 className={styles.panelCardTitle}>Циферблат на 24 години</h3>
              <p className={styles.panelCardText}>
                Кругова діаграма показує години зі світлом та відключеннями з одного погляду на екран.
              </p>
            </div>

            <div className={styles.panelCardWide}>
              <div className={styles.panelWideHeader}>
                <span className={styles.panelIcon} style={{ color: "var(--success)" }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                </span>
                <span className={styles.panelCardTitle}>Безпека та приватність</span>
              </div>
              <p className={styles.panelCardText}>
                Жодних персональних даних. Обрана черга чи адреса зберігаються виключно у пам&apos;яті вашого браузера.
                Без реклами та зайвих трекерів.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Highlights Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeading}>
          <span className={styles.sectionEyebrow}>Переваги</span>
          <h2 className={styles.sectionTitle}>Чому житомиряни обирають Likhtarychok</h2>
          <p className={styles.sectionSubtitle}>
            Створено з турботою про містян для швидкого доступу до графіків без перевантажених сайтів
          </p>
        </div>

        <div className={styles.highlightsGrid}>
          {highlights.map((item) => (
            <div key={item.title} className={styles.card}>
              <div className={styles.cardIcon}>{item.icon}</div>
              <h3 className={styles.cardTitle}>{item.title}</h3>
              <p className={styles.cardText}>{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 3 Steps Section */}
      <section className={styles.stepsSection}>
        <div className={styles.sectionHeading}>
          <span className={styles.sectionEyebrow}>Як користуватися</span>
          <h2 className={styles.sectionTitle}>Три прості кроки до спокою</h2>
          <p className={styles.sectionSubtitle}>
            Усе налаштовується менше ніж за хвилину
          </p>
        </div>

        <div className={styles.stepsGrid}>
          {steps.map((step) => (
            <div key={step.step} className={styles.stepCard}>
              <div className={styles.stepNum}>{step.step}</div>
              <h3 className={styles.stepTitle}>{step.title}</h3>
              <p className={styles.stepText}>{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Quick CTA Banner */}
      <section className={styles.ctaBanner}>
        <div className={styles.ctaBannerContent}>
          <h2 className={styles.ctaBannerTitle}>Перевірте стан світла прямо зараз</h2>
          <p className={styles.ctaBannerSubtitle}>
            Відкрийте графік для вашої черги та дізнайтеся, коли наступне включення чи відключення.
          </p>
        </div>
        <Link className={styles.ctaBannerBtn} to="/graph">
          Відкрити графік
        </Link>
      </section>
    </div>
  );
}

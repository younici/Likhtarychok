import styles from "./Donate.module.css";

const MONOBANK_JAR_URL = "https://send.monobank.ua/jar/URkkezeB6";

const reasons = [
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
        <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
        <line x1="6" y1="6" x2="6.01" y2="6" />
        <line x1="6" y1="18" x2="6.01" y2="18" />
      </svg>
    ),
    title: "Серверна інфраструктура",
    body: "Оплата виділених VDS серверів, швидкої бази даних PostgreSQL та Redis для миттєвого кешування графіків кожні 5 хвилин.",
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    ),
    title: "Стабільні сповіщення",
    body: "Підтримка фонових демонів розсилки Web Push та Telegram-бота, які попереджають тисячі житомирян за годину до зміни графіку.",
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
    title: "Жодної реклами",
    body: "Сервіс не має набридливих банерів, трекерів чи комерційних інтеграцій — інтерфейс залишається чистим і швидким.",
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    ),
    title: "Постійний розвиток",
    body: "Ми постійно вдосконалюємо алгоритми: додали точний пошук адрес, інтерактивний циферблат та оптимізуємо мобільну версію.",
  },
];

export default function Donate() {
  return (
    <div className={styles.page}>
      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.glow} aria-hidden />

        <div className={styles.heroBadge}>
          <span>💛</span>
          Підтримка проєкту
        </div>

        <h1 className={styles.title}>Допоможіть Likhtarychok світити далі</h1>

        <p className={styles.lead}>
          Likhtarychok — некомерційний волонтерський проєкт для мешканців Житомира.
          Усі кошти спрямовуються виключно на оплату хостингу, серверів та стабільну роботу розсилки сповіщень.
        </p>

        {/* Monobank button */}
        <a
          className={styles.monoButton}
          href={MONOBANK_JAR_URL}
          target="_blank"
          rel="noreferrer"
        >
          <span className={styles.monoLogo} aria-hidden>
            m
          </span>
          <span>Підтримати через Monobank</span>
        </a>

        <p className={styles.hint}>
          Будь-який внесок — 20, 50 чи 100 грн — допомагає оплачувати сервери. Дякуємо! 💛
        </p>
      </section>

      {/* Grid of reasons */}
      <section className={styles.section}>
        <div className={styles.sectionHeading}>
          <span className={styles.eyebrow}>Куди йдуть кошти</span>
          <h2 className={styles.sectionTitle}>На що витрачаються донати</h2>
        </div>

        <div className={styles.grid}>
          {reasons.map((item) => (
            <div key={item.title} className={styles.card}>
              <span className={styles.cardIcon} aria-hidden="true">
                {item.icon}
              </span>
              <h3 className={styles.cardTitle}>{item.title}</h3>
              <p className={styles.cardBody}>{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Bottom Thanks */}
      <section className={styles.thanksCard}>
        <div className={styles.thanksContent}>
          <h3 className={styles.thanksTitle}>Дякуємо кожному, хто підтримує!</h3>
          <p className={styles.thanksText}>
            Завдяки вашій підтримці сервіс залишається повністю безкоштовним і відкритим для всіх містян.
            Якщо ви маєте ідеї чи пропозиції — напишіть нам у{" "}
            <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">
              Telegram-бот підтримки
            </a>
            .
          </p>
        </div>
      </section>
    </div>
  );
}

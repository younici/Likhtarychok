import styles from "./Privacy.module.css";

export default function Privacy() {
  return (
    <div className={styles.page}>
      {/* Header */}
      <section className={styles.header}>
        <div className={styles.headerBadge}>Конфіденційність</div>
        <h1 className={styles.title}>Політика приватності</h1>
        <p className={styles.lead}>
          Likhtarychok створено як некомерційний відкритий сервіс для допомоги мешканцям Житомира.
          Ми дотримуємося принципу мінімізації даних: сайт не вимагає реєстрації, не показує рекламу
          та не продає ваші дані третім особам.
        </p>
      </section>

      {/* Grid of details */}
      <section className={styles.grid}>
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ color: "var(--accent)" }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
            </span>
            <h2 className={styles.cardTitle}>Дані у пам&apos;яті вашого браузера</h2>
          </div>
          <p className={styles.cardDesc}>
            У локальному сховищі браузера (<code>localStorage</code>) зберігається мінімум інформації,
            необхідний для зручного користування сайтом:
          </p>
          <ul className={styles.list}>
            <li>Номер обраної вами черги (наприклад, <code>1.2</code>) для автоматичного відкриття;</li>
            <li>Остання обрана назва вулиці та номер будинку (якщо ви користувалися пошуком за адресою);</li>
            <li>Відмітка про закриття інформаційного банера підтримки;</li>
            <li>Обраний режим відображення графіка.</li>
          </ul>
        </div>

        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ color: "var(--cyan)" }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
            </span>
            <h2 className={styles.cardTitle}>Web Push та сповіщення</h2>
          </div>
          <p className={styles.cardDesc}>
            Якщо ви добровільно підписуєтеся на отримання сповіщень:
          </p>
          <ul className={styles.list}>
            <li>Браузер генерує анонімний криптографічний токен пристрою (Endpoint та публічний ключ шифрування);</li>
            <li>Цей токен прив&apos;язується до обраної черги виключно для доставки планових сповіщень;</li>
            <li>Ми не маємо доступу до вашої особи, IP-адреси чи номера телефону через Web Push;</li>
            <li>Ви можете будь-якої миті відкликати дозвіл у налаштуваннях браузера.</li>
          </ul>
        </div>

        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ color: "var(--danger)" }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
              </svg>
            </span>
            <h2 className={styles.cardTitle}>Чого ми НІКОЛИ не збираємо</h2>
          </div>
          <ul className={styles.list}>
            <li>Жодних персональних даних: ім&apos;я, email, телефон, паролі;</li>
            <li>Жодних даних про ваше точне GPS-місцезнаходження;</li>
            <li>Жодних рекламних пікселів або передачі поведінкових профілів комерційним компаніям;</li>
            <li>Ми не монетизуємо дані наших відвідувачів.</li>
          </ul>
        </div>

        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ color: "var(--success)" }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </span>
            <h2 className={styles.cardTitle}>Керування та видалення даних</h2>
          </div>
          <p className={styles.cardDesc}>
            Ви маєте повний контроль над збереженими налаштуваннями:
          </p>
          <ul className={styles.list}>
            <li>Очищення кешу або локального сховища вашого браузера миттєво видаляє всі налаштування;</li>
            <li>Щоб припинити push-сповіщення, просто вимкніть дозвіл на сповіщення для сайту у налаштуваннях браузера або відпишіться у Telegram-боті командою <code>/stop</code>.</li>
          </ul>
        </div>
      </section>

      {/* Contact box */}
      <section className={styles.contactBox}>
        <div className={styles.contactContent}>
          <span className={styles.contactEyebrow}>Запитання та звернення</span>
          <h3 className={styles.contactTitle}>Потрібна допомога чи консультація?</h3>
          <p className={styles.contactDesc}>
            З будь-яких питань щодо роботи сервісу, безпеки або обробки даних напишіть нам:
          </p>
          <div className={styles.contactLinks}>
            <a href="mailto:kostantinreksha@gmail.com" className={styles.contactLink}>
              kostantinreksha@gmail.com
            </a>
            <span className={styles.sep}>•</span>
            <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer" className={styles.contactLink}>
              Telegram-бот підтримки
            </a>
            <span className={styles.sep}>•</span>
            <a href="https://t.me/younici" target="_blank" rel="noreferrer" className={styles.contactLink}>
              Зворотний зв&apos;язок (@younici)
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}

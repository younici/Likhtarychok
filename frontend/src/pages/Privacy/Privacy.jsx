import styles from "./Privacy.module.css";

function Privacy() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <p className={styles.eyebrow}>Політика приватності</p>
        <h1>Як ми працюємо з даними</h1>
        <p className={styles.lead}>
          Ми не збираємо персональні дані користувачів і не показуємо рекламу. Сайт працює завдяки добровільним пожертвам.
        </p>
      </section>

      <section className={styles.grid}>
        <div className={styles.card}>
          <h3>Дані, які ми зберігаємо</h3>
          <ul>
            <li>Номер обраної черги та налаштування вигляду графіка — у локальному сховищі браузера.</li>
            <li>Підписка на сповіщення (якщо ви її підтвердили) — для надсилання web-push.</li>
          </ul>
        </div>
        <div className={styles.card}>
          <h3>Що не збираємо</h3>
          <ul>
            <li>Не просимо ім’я, email чи інші персональні дані для користування сайтом.</li>
            <li>Не продаємо та не передаємо інформацію третім сторонам.</li>
          </ul>
        </div>
      </section>

      <section className={styles.note}>
        <div>
          <p className={styles.eyebrow}>Запитання</p>
          <h3>Потрібна допомога або видалення даних?</h3>
          <p>
            Напишіть нам на{" "}
            <a href="mailto:kostantinreksha@gmail.com" rel="noreferrer">
              kostantinreksha@gmail.com
            </a>{" "}
            або у <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">Telegram-бот підтримки</a>.
          </p>
        </div>
      </section>
    </div>
  );
}

export default Privacy;

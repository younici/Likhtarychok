import styles from "./Donate.module.css";

const MONOBANK_JAR_URL = "https://send.monobank.ua/jar/URkkezeB6";

const reasons = [
  {
    icon: "🖥️",
    title: "Сервери",
    body: "Оплата хостингу, бази даних та Redis, щоб графік оновлювався кожні 5 хвилин без збоїв.",
  },
  {
    icon: "🔔",
    title: "Сповіщення",
    body: "Стабільна робота web-push та Telegram-бота, які нагадують про відключення за годину.",
  },
  {
    icon: "🚫",
    title: "Без реклами",
    body: "Сайт не показує рекламу — він чистий і швидкий саме завдяки вашим пожертвам.",
  },
];

function Donate() {
  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.glow} aria-hidden />
        <p className={styles.eyebrow}>Підтримати проєкт</p>
        <h1>Допоможіть Likhtarychok світити далі</h1>
        <p className={styles.lead}>
          Likhtarychok — безкоштовний некомерційний сервіс. Усі пожертви йдуть на підтримку роботи серверів, а завдяки
          вашій допомозі на сайті немає реклами.
        </p>

        <a className={styles.monoButton} href={MONOBANK_JAR_URL} target="_blank" rel="noreferrer">
          <span className={styles.monoLogo} aria-hidden>
            m
          </span>
          Задонатити через Monobank
        </a>
        <small className={styles.hint}>Будь-яка сума має значення. Дякуємо! 💛</small>
      </section>

      <section className={styles.grid}>
        {reasons.map((item) => (
          <div key={item.title} className={styles.card}>
            <span className={styles.icon} aria-hidden>
              {item.icon}
            </span>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

export default Donate;

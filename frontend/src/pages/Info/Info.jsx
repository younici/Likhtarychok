import { Link } from "react-router-dom";
import styles from "./Info.module.css";

const pillars = [
  {
    title: "Офіційні джерела",
    body: (
      <>
        Забираємо графік з{" "}
        <a href="https://www.ztoe.com.ua/unhooking-search.php" target="_blank" rel="noreferrer">
          сайту Житомиробленерго
        </a>
        , приводимо до півгодинних слотів і показуємо у двох режимах.
      </>
    ),
  },
  {
    title: "Приватність",
    body: "Не збираємо персональних даних. Зберігаємо лише обрану вами чергу та налаштування вигляду у браузері.",
  },
  {
    title: "Надійність",
    body: "Резервний канал сповіщень через Telegram-бот, якщо web-push у браузері обмежений або працює нестабільно.",
  },
  {
    title: "Відкритість",
    body: "Попереджаємо про можливі відхилення й не приховуємо, що графік може змінюватися без попередження.",
  },
];

const timeline = [
  {
    label: "Отримуємо дані",
    desc: "Запитуємо офіційний розклад та конвертуємо його у рівні півгодинні інтервали.",
  },
  {
    label: "Нормалізуємо черги",
    desc: "Зберігаємо вибрану чергу у браузері та автоматично оновлюємо графік кожні 5 хвилин.",
  },
  {
    label: "Показуємо зрозуміло",
    desc: "Два режими — повний графік або лише відрізки без світла. Є перемикач у будь-який момент.",
  },
  {
    label: "Нагадуємо завчасно",
    desc: "Сповіщаємо за годину до планового відключення через web-push або Telegram-бот.",
  },
];

function Info() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <p className={styles.eyebrow}>Про сервіс</p>
        <h1>Likhtarychok створили для швидкої підготовки до стабілізаційних відключень</h1>
        <p className={styles.lead}>
          Ми не навантажуємо вас деталями, а показуємо актуальний графік для вашої черги, два варіанти відображення та
          сповіщення за годину до планового відключення.
        </p>
        <div className={styles.badges}>
          <span>Web push + Telegram</span>
          <span>Оновлення кожні 5 хв</span>
          <span>Житомирська область</span>
        </div>
      </section>

      <section className={styles.grid}>
        {pillars.map((item) => (
          <div key={item.title} className={styles.card}>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </div>
        ))}
      </section>

      <section className={styles.timeline}>
        <div className={styles.timelineIntro}>
          <p className={styles.eyebrow}>Як усе побудовано</p>
          <h2>Шлях даних від джерела до сповіщення</h2>
          <p>
            Графік може змінюватися, але ми пояснюємо кожен крок: де беремо дані, як їх обробляємо та як надсилаємо
            сповіщення.
          </p>
        </div>
        <div className={styles.timelineList}>
          {timeline.map((step) => (
            <div key={step.label} className={styles.timelineItem}>
              <div className={styles.dot} />
              <div>
                <h3>{step.label}</h3>
                <p>{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.notice}>
        <div>
          <p className={styles.eyebrow}>Важливо</p>
          <h3>Графік може змінюватися без попередження</h3>
          <p>
            Навіть офіційний розклад іноді оновлюється із запізненням. Якщо бачите розбіжності або маєте питання,
            переходьте у <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">Telegram-бот підтримки</a> або
            напишіть нам напряму.
          </p>
        </div>
        <Link className={styles.linkButton} to="/faq">
          Перейти до FAQ
        </Link>
      </section>
    </div>
  );
}

export default Info;

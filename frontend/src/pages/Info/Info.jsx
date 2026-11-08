import { Link } from "react-router-dom";
import styles from "./Info.module.css";

const pillars = [
  {
    title: "Офіційні джерела",
    body: (
      <>
        Дані автоматично зчитуються з офіційного розкладу{" "}
        <a href="https://www.ztoe.com.ua/unhooking-search.php" target="_blank" rel="noreferrer">
          АТ «Житомиробленерго»
        </a>
        . Ми трансформуємо складні таблиці у зручні інтервали та інтерактивний циферблат.
      </>
    ),
  },
  {
    title: "Повна приватність",
    body: "Сервіс не вимагає реєстрації та не запитує персональних даних. Номер вашої черги або збережена адреса зберігаються лише у локальній пам'яті браузера.",
  },
  {
    title: "Подвійний канал сповіщень",
    body: (
      <>
        Отримуйте сповіщення прямо у браузері (Web Push) або підключіть наш{" "}
        <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">
          Telegram-бот
        </a>
        , якщо браузер пристрою обмежує фонові повідомлення.
      </>
    ),
  },
  {
    title: "Чесність та прозорість",
    body: "Ми завжди показуємо точний час останньої синхронізації та попереджаємо про можливі аварійні відхилення, які вводить Укренерго.",
  },
];

const timeline = [
  {
    step: "1",
    label: "Отримання даних",
    desc: "Серверний демон опитує сайт Житомиробленерго щоп'ять хвилин, перевіряючи зміни у графіках для всіх черг 1.1–6.2.",
  },
  {
    step: "2",
    label: "Нормалізація інтервалів",
    desc: "Розклад розбивається на чіткі 30-хвилинні слоти: світло є (гарантовано), можливе відключення (жовта зона) або відключено (сіра зона).",
  },
  {
    step: "3",
    label: "Миттєве відображення",
    desc: "Користувач бачить поточний статус енергопостачання, таймер зворотного відліку та зручний 24-годинний годинник.",
  },
  {
    step: "4",
    label: "Завчасне сповіщення",
    desc: "За 60 хвилин до планового відключення або включення система надсилає пуш-повідомлення підписникам черги.",
  },
];

const tips = [
  {
    title: "Як дізнатися номер своєї черги?",
    desc: "Скористайтеся вбудованим пошуком за адресою на сторінці «Графік» або звіртеся на сайті Житомиробленерго за назвою вулиці та номером будинку.",
  },
  {
    title: "Чому світло вимкнули не за графіком?",
    desc: "У разі перевантаження енергосистеми НЕК «Укренерго» застосовує аварійні відключення (САВ), які не відображаються у планових графіках.",
  },
  {
    title: "Сповіщення не приходять на iOS / Android?",
    desc: "Перевірте дозволи у налаштуваннях браузера. На iOS додайте сайт на головний екран («Поділитися» -> «На початковий екран»), або скористайтеся Telegram-ботом.",
  },
];

export default function Info() {
  return (
    <div className={styles.page}>
      {/* Header section */}
      <section className={styles.header}>
        <div className={styles.headerBadge}>Про проєкт Likhtarychok</div>
        <h1 className={styles.title}>
          Прозорий гід по графіках погодинних відключень у Житомирі
        </h1>
        <p className={styles.lead}>
          Likhtarychok створений для того, щоб ви не витрачали час на пошук своєї черги у незручних таблицях.
          Ми перетворюємо офіційні дані у наочний інтерфейс із таймерами, циферблатом та сповіщеннями.
        </p>
        <div className={styles.badges}>
          <span>Web Push + Telegram</span>
          <span>Синхронізація що 5 хв</span>
          <span>Житомир та область</span>
          <span>Без збору даних</span>
        </div>
      </section>

      {/* Pillars */}
      <section className={styles.section}>
        <div className={styles.sectionHeading}>
          <span className={styles.eyebrow}>Принципи</span>
          <h2 className={styles.sectionTitle}>На чому базується робота сервісу</h2>
        </div>
        <div className={styles.grid}>
          {pillars.map((item) => (
            <div key={item.title} className={styles.card}>
              <h3 className={styles.cardTitle}>{item.title}</h3>
              <p className={styles.cardBody}>{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Timeline */}
      <section className={styles.timelineSection}>
        <div className={styles.timelineIntro}>
          <span className={styles.eyebrow}>Архітектура даних</span>
          <h2 className={styles.sectionTitle}>Шлях інформації від обленерго до вашого екрана</h2>
          <p className={styles.timelineIntroText}>
            Ми налагодили надійний конвеєр обробки даних, щоб розбіжність із першоджерелом була мінімальною.
          </p>
        </div>

        <div className={styles.timelineList}>
          {timeline.map((item) => (
            <div key={item.step} className={styles.timelineItem}>
              <div className={styles.stepCircle}>{item.step}</div>
              <div className={styles.timelineContent}>
                <h3 className={styles.timelineItemTitle}>{item.label}</h3>
                <p className={styles.timelineItemText}>{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Tips */}
      <section className={styles.section}>
        <div className={styles.sectionHeading}>
          <span className={styles.eyebrow}>Корисні поради</span>
          <h2 className={styles.sectionTitle}>Як отримати максимум від Likhtarychok</h2>
        </div>
        <div className={styles.grid}>
          {tips.map((item) => (
            <div key={item.title} className={styles.tipCard}>
              <h3 className={styles.tipTitle}>{item.title}</h3>
              <p className={styles.tipDesc}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Important Notice */}
      <section className={styles.noticeBanner}>
        <div className={styles.noticeText}>
          <span className={styles.eyebrow}>Зверніть увагу</span>
          <h3 className={styles.noticeHeading}>Графік може оперативно коригуватися</h3>
          <p className={styles.noticeDesc}>
            Усі розпорядження про зміну черг віддає черговий диспетчер НЕК «Укренерго». Ми оновлюємо дані одразу,
            як тільки вони з&apos;являються на офіційних серверах. Залишилися питання? Завітайте у FAQ або зверніться до бота підтримки.
          </p>
        </div>
        <div className={styles.noticeActions}>
          <Link className={styles.faqBtn} to="/faq">
            Перейти до FAQ
          </Link>
          <a
            className={styles.botBtn}
            href="https://t.me/likhtarychok_help_bot"
            target="_blank"
            rel="noreferrer"
          >
            Бот підтримки
          </a>
        </div>
      </section>
    </div>
  );
}

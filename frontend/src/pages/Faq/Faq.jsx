import { useState } from "react";
import styles from "./Faq.module.css";

const questions = [
  {
    id: "q1",
    q: "Як дізнатися свою чергу?",
    a: (
      <>
        На сторінці «Графік» скористайтеся вбудованим пошуком за адресою — введіть вулицю та номер будинку у Житомирі.
        Також ви можете перевірити номер черги безпосередньо на{" "}
        <a href="https://www.ztoe.com.ua/unhooking-search.php" target="_blank" rel="noreferrer">
          офіційному сайті Житомиробленерго
        </a>
        . Обрана черга (наприклад, 2.1) збережеться у вашому браузері і буде відкриватися за замовчуванням.
      </>
    ),
  },
  {
    id: "q2",
    q: "Чому графік на сайті може відрізнятися від реального відключення?",
    a: "Графік, який ми транслюємо, є офіційним плановим погодинним розкладом (ГПВ). Проте за командою НЕК «Укренерго» диспетчери можуть екстрено застосовувати спеціальні або аварійні графіки (САВ / ГАВ), які вводяться без завчасного попередження через дефіцит потужності в енергосистемі.",
  },
  {
    id: "q3",
    q: "Як підключити сповіщення через Telegram-бот?",
    a: (
      <>
        Перейдіть у наш{" "}
        <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">
          Telegram-бот підтримки
        </a>
        , натисніть <code>/start</code> та оберіть вашу чергу. Бот надішле повідомлення за 1 годину до планового відключення або включення світла.
      </>
    ),
  },
  {
    id: "q4",
    q: "Як часто оновлюються дані на сайті?",
    a: "Наш бекенд опитує офіційні сервери Житомиробленерго кожні 5 хвилин. На сторінці «Графік» ви завжди бачите точний час останнього успішного оновлення. Також можна натиснути кнопку «Оновити» вручну.",
  },
  {
    id: "q5",
    q: "Які персональні дані збирає сайт?",
    a: "Жодних персональних даних ми не збираємо і не зберігаємо на серверах. Номер обраної вами черги чи адреса зберігаються виключно в пам'яті вашого власного браузера (localStorage). Якщо ви вмикаєте Web Push, генерується анонімний криптографічний токен пристрою виключно для доставки push-повідомлень.",
  },
  {
    id: "q6",
    q: "Що робити, якщо Web Push сповіщення не приходять?",
    a: "Переконайтеся, що у налаштуваннях вашого браузера надано дозвіл на сповіщення для сайту Likhtarychok. На смартфонах перевірте, чи не ввімкнено суворий режим енергозбереження, який блокує фонову передачу даних браузера. Як надійну альтернативу рекомендуємо Telegram-бота.",
  },
  {
    id: "q7",
    q: "Як додати Likhtarychok як додаток на екран телефона?",
    a: "На iPhone у Safari натисніть кнопку «Поділитися» (квадрат зі стрілкою) і виберіть «На початковий екран». На Android у Chrome натисніть меню (три крапки) і виберіть «Встановити додаток» або «Додати на головний екран». Сервіс працюватиме як швидкий мобільний застосунок.",
  },
];

export default function Faq() {
  const [openItems, setOpenItems] = useState({ q1: true, q2: true });

  const toggleItem = (id) => {
    setOpenItems((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <section className={styles.header}>
        <div className={styles.headerBadge}>База знань</div>
        <h1 className={styles.title}>Відповіді на поширені питання</h1>
        <p className={styles.lead}>
          Корисна інформація про черги, джерела даних, сповіщення та стабільність розкладу.
          Якщо вашого питання немає у списку — зв&apos;яжіться з нами напряму.
        </p>
      </section>

      {/* Accordion / Cards List */}
      <section className={styles.faqList}>
        {questions.map((item) => {
          const isOpen = !!openItems[item.id];
          return (
            <div
              key={item.id}
              className={`${styles.itemCard} ${isOpen ? styles.itemCardOpen : ""}`}
            >
              <button
                type="button"
                className={styles.questionBtn}
                onClick={() => toggleItem(item.id)}
                aria-expanded={isOpen}
              >
                <span className={styles.questionText}>{item.q}</span>
                <span className={styles.iconWrapper}>
                  <svg
                    className={`${styles.chevron} ${isOpen ? styles.chevronOpen : ""}`}
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </span>
              </button>
              {isOpen && (
                <div className={styles.answerWrapper}>
                  <div className={styles.answerText}>{item.a}</div>
                </div>
              )}
            </div>
          );
        })}
      </section>

      {/* Contact Section */}
      <section className={styles.contact}>
        <div className={styles.contactText}>
          <span className={styles.contactEyebrow}>Не знайшли відповіді?</span>
          <h3 className={styles.contactTitle}>Запитайте нас особисто або через бота</h3>
          <p className={styles.contactSubtitle}>
            Помітили неточність, маєте пропозицію або потрібна допомога з чергою? Ми відкриті до зв&apos;язку та відповідаємо оперативно.
          </p>
        </div>

        <div className={styles.contactActions}>
          <a
            className={styles.primaryAction}
            href="https://t.me/likhtarychok_help_bot"
            target="_blank"
            rel="noreferrer"
          >
            <span>Telegram-бот підтримки</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2L2 9.5l7 3 2 6.5 3.5-3.5 5 3.5 2-17z" />
            </svg>
          </a>
          <a
            className={styles.secondaryAction}
            href="https://t.me/younici"
            target="_blank"
            rel="noreferrer"
          >
            <span>Написати автору (@younici)</span>
          </a>
        </div>
      </section>
    </div>
  );
}

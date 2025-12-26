import styles from "./Faq.module.css";

const questions = [
  {
    q: "Як дізнатися свою чергу?",
    a: (
      <>
        Зайдіть на{" "}
        <a href="https://www.ztoe.com.ua/unhooking-search.php" target="_blank" rel="noreferrer">
          сайт Житомиробленерго
        </a>{" "}
        і знайдіть будинок за адресою. Номер черги збережеться у браузері, щоб не вводити його щоразу.
      </>
    ),
  },
  {
    q: "Чому графік може не співпадати з реальністю?",
    a: "Офіційний розклад може змінюватися впродовж дня. Ми оновлюємо дані кожні 5 хвилин і показуємо їх у зручному вигляді, але інколи можливі відхилення.",
  },
  {
    q: "Що робити, якщо браузер не підтримує push-сповіщення?",
    a: (
      <>
        Скористайтесь нашим{" "}
        <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">
          Telegram-ботом підтримки
        </a>
        . Він дублює сповіщення, якщо web-push недоступний або працює нестабільно.
      </>
    ),
  },
  {
    q: "Як часто оновлюються дані?",
    a: "Кожні 5 хвилин. Якщо потрібно, можна вручну натиснути «Оновити інформацію» на сторінці графіка.",
  },
  {
    q: "Які налаштування ви зберігаєте?",
    a: "Лише номер обраної черги та режим перегляду графіка. Інші персональні дані не збираємо.",
  },
  {
    q: "Що робити, якщо сповіщення не приходять?",
    a: "Перевірте, чи дозволені сповіщення для сайту у браузері, чи не відписались від них випадково, та чи працює підключення до інтернету на пристрої.",
  },
];

function Faq() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <p className={styles.eyebrow}>FAQ</p>
        <h1>Відповіді на поширені питання</h1>
        <p className={styles.lead}>
          Зібрали короткі інструкції щодо черг, точності графіка та сповіщень. Якщо не знайшли своє питання — напишіть нам.
        </p>
      </section>

      <section className={styles.grid}>
        {questions.map((item) => (
          <div key={item.q} className={styles.card}>
            <h3>{item.q}</h3>
            <p>{item.a}</p>
          </div>
        ))}
      </section>

      <section className={styles.contact}>
        <div>
          <p className={styles.eyebrow}>Потрібна допомога?</p>
          <h3>Напишіть нам у Telegram — реагуємо швидко</h3>
          <p>
            Якщо бачите помилку у графіку або хочете запропонувати покращення, дайте знати. Ми читаємо всі повідомлення та
            підказки.
          </p>
        </div>
        <div className={styles.actions}>
          <a className={styles.supportPrimary} href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">
            Відкрити бот підтримки
          </a>
          <a className={styles.secondary} href="https://t.me/younici" target="_blank" rel="noreferrer">
            Написати напряму
          </a>
        </div>
      </section>
    </div>
  );
}

export default Faq;

import styles from "./Stats.module.css";

const highlights = [
  { label: "Оновлення графіка", value: "кожні 5 хвилин", desc: "Синхронізація з офіційним сайтом протягом дня." },
  { label: "Черги в одному місці", value: "12 черг", desc: "Показуємо всі комбінації (1.1–6.2) зберігаючи вашу в браузері." },
  { label: "Канали сповіщень", value: "Push + Telegram", desc: "Резервний варіант, якщо браузер не підтримує web-push." },
];

const roadmap = [
  { title: "Живі лічильники підписок", desc: "Показати динаміку за тиждень та пікові години відправки сповіщень." },
  { title: "Відсоток точності графіка", desc: "Візуалізувати, як часто офіційні дані оновлюються протягом дня." },
  { title: "Історія відключень по чергах", desc: "Додати архівні дні, щоб бачити типові проміжки без світла." },
];

const mockLoad = [
  { label: "Push-сповіщення", value: "чернетка", tone: "warm" },
  { label: "Запити до API", value: "під наглядом", tone: "calm" },
  { label: "Помилки доставки", value: "мінімальні", tone: "ok" },
];

function Stats() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <p className={styles.eyebrow}>Чернетка аналітики</p>
        <h1>Статистика Likhtarychok готується до релізу</h1>
        <p className={styles.lead}>
          Зараз фокусуємося на стабільності графіка та сповіщень. Тут зʼявляться живі лічильники та історичні зрізи, щойно
          достатньо даних накопичиться для публічної аналітики.
        </p>
      </section>

      <section className={styles.highlights}>
        {highlights.map((item) => (
          <div key={item.label} className={styles.card}>
            <p className={styles.label}>{item.label}</p>
            <p className={styles.value}>{item.value}</p>
            <p className={styles.copy}>{item.desc}</p>
          </div>
        ))}
      </section>

      <section className={styles.load}>
        <div className={styles.loadIntro}>
          <p className={styles.eyebrow}>Що відбувається зараз</p>
          <h2>Моніторимо стабільність сервісу</h2>
          <p>Ці стани описують, над чим працює система щодня, поки готуємо публічні графіки.</p>
        </div>
        <div className={styles.loadGrid}>
          {mockLoad.map((item) => (
            <div key={item.label} className={`${styles.loadCard} ${styles[item.tone]}`}>
              <p className={styles.label}>{item.label}</p>
              <p className={styles.value}>{item.value}</p>
              <p className={styles.copy}>Підтримуємо стабільність і логіку повторних спроб доставки.</p>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.roadmap}>
        <div>
          <p className={styles.eyebrow}>Найближчі додавання</p>
          <h2>Що зʼявиться у статистиці</h2>
          <p>Публікуватимемо тільки ті метрики, які можна збирати стабільно та без ризику для приватності користувачів.</p>
        </div>
        <div className={styles.roadmapList}>
          {roadmap.map((item) => (
            <div key={item.title} className={styles.roadmapItem}>
              <div className={styles.dot} />
              <div>
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default Stats;

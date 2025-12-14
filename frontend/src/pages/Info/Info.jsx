import styles from "./Info.module.css";

function Info() {
  return (
    <main className={styles.page}>
      <div className={styles.infoContainer}>
        <div className={styles.infoHead}>
          <h2 className={`${styles.infoTitle} ${styles.card}`}>Про сайт</h2>
        </div>
        <div className={styles.infoBody}>
          <div className={styles.card}>
            <h1>
              <a href="/">Likhtarychok</a> (Ліхтаричок) сайт створений для зручного показу
              графіку відключень світла по Житомирьскій області 
            </h1>
          </div>
          <div className={styles.card}>
            Як дізнатися свою чергу? зайдіть на сайт{" "}
            <a href="https://www.ztoe.com.ua/unhooking-search.php" target="_blank" rel="noreferrer">
              Житомир обл. Енерго
            </a>{" "}
            та знайдіть свою чергу
          </div>
          <div className={styles.card}>
            <p>
              Графік береться з{" "}
              <a href="https://www.ztoe.com.ua/unhooking-search.php" target="_blank" rel="noreferrer">
                офіційного сайту Житомир обл. Енерго
              </a>
            </p>
          </div>
          <div className={styles.card}>
            Графік може бути не точним, так як самі працівникі Житомир обл. Енерго
            не завджи знають коли потрібно відключити світло а коли ні
          </div>
        </div>
        <div className={styles.infoFooter}>
          <div className={styles.card}>
            <p>
              Created by <a href="https://t.me/younici">younici</a>
              <br />
              kostantinreksa@gmail.com
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}

export default Info;

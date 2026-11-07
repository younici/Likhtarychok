import { useState, useEffect, useCallback } from "react";
import styles from "./AdmStats.module.css";

const apiBase =
  import.meta.env.API_BASE_PATH ||
  import.meta.env.VITE_API_BASE ||
  import.meta.env.VITE_API_BASE_PATH ||
  "";

const STORAGE_KEY = "admstats_token";

export default function AdmStats() {
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastUpdated, setLastUpdated] = useState("");

  const fetchStats = useCallback(async (authPass) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/admin/stats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: authPass }),
      });

      if (res.status === 401) {
        setIsAuthenticated(false);
        sessionStorage.removeItem(STORAGE_KEY);
        setError("Невірний пароль доступу. Спробуйте ще раз.");
        return;
      }

      if (!res.ok) {
        throw new Error(`Помилка сервера (HTTP ${res.status})`);
      }

      const data = await res.json();
      if (data && data.ok) {
        setStats(data.stats);
        setIsAuthenticated(true);
        sessionStorage.setItem(STORAGE_KEY, authPass);
        setLastUpdated(new Date().toLocaleTimeString());
      } else {
        setError(data.error || "Не вдалося отримати статистику");
      }
    } catch (err) {
      setError(err.message || "Помилка зв'язку з сервером");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Try auto-login on mount if session token exists
  useEffect(() => {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      setPassword(saved);
      fetchStats(saved);
    }
  }, [fetchStats]);

  // Handle auto-refresh interval
  useEffect(() => {
    if (!isAuthenticated || !autoRefresh) return;
    const interval = setInterval(() => {
      const currentPass = sessionStorage.getItem(STORAGE_KEY) || password;
      if (currentPass) {
        fetchStats(currentPass);
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated, autoRefresh, password, fetchStats]);

  const handleLogin = (e) => {
    e.preventDefault();
    if (!password.trim()) {
      setError("Введіть пароль");
      return;
    }
    fetchStats(password);
  };

  const handleLogout = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    setIsAuthenticated(false);
    setPassword("");
    setStats(null);
    setError(null);
  };

  // If NOT authenticated, show password prompt
  if (!isAuthenticated) {
    return (
      <div className={styles.container}>
        <div className={styles.loginWrapper}>
          <div className={styles.loginCard}>
            <div className={styles.lockIconWrap}>
              <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
            </div>
            <h1 className={styles.loginTitle}>Панель адміністратора</h1>
            <p className={styles.loginSubtitle}>
              Доступ до статистики бази даних та розсилок захищено паролем
            </p>

            <form onSubmit={handleLogin} className={styles.form}>
              <div className={styles.inputGroup}>
                <label htmlFor="adm-pass">Пароль адміністратора</label>
                <div className={styles.inputWrapper}>
                  <input
                    id="adm-pass"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Введіть пароль..."
                    className={styles.passwordInput}
                    autoComplete="current-password"
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className={styles.togglePassBtn}
                    aria-label="Показати пароль"
                  >
                    {showPassword ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                      </svg>
                    ) : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {error && (
                <div className={styles.errorBanner} role="alert">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                  <span>{error}</span>
                </div>
              )}

              <button type="submit" disabled={isLoading} className={styles.submitBtn}>
                {isLoading ? <span className={styles.spinner} /> : "Увійти"}
              </button>
            </form>

            <div className={styles.securityNote}>
              🔒 Безпека: перевірка пароля здійснюється виключно на бекенді. Переглянути пароль у клієнтському коді неможливо.
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Dashboard Data destructured
  const users = stats?.users || {};
  const pushes = stats?.pushes_24h || {};
  const dbData = stats?.database || {};
  const redis = stats?.redis || {};
  const queueDist = users.by_queue || {};
  const pushHistory = pushes.history || [];

  return (
    <div className={styles.container}>
      {/* Header bar */}
      <div className={styles.dashHeader}>
        <div className={styles.dashTitleBlock}>
          <h1>Статистика системи (/admstats)</h1>
          <div className={styles.metaText}>
            <span>Сервер: {stats?.server_time || "N/A"}</span>
            {lastUpdated && <span>• Оновлено в клієнті: {lastUpdated}</span>}
          </div>
        </div>

        <div className={styles.headerActions}>
          <label className={styles.autoRefreshToggle}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Авто 30с
          </label>

          <button
            onClick={() => fetchStats(sessionStorage.getItem(STORAGE_KEY) || password)}
            disabled={isLoading}
            className={styles.refreshBtn}
            title="Оновити статистику"
          >
            {isLoading ? <span className={styles.spinner} /> : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M23 4v6h-6"></path>
                <path d="M1 20v-6h6"></path>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
            )}
            Оновити
          </button>

          <button onClick={handleLogout} className={styles.logoutBtn} title="Вийти з панелі">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
            Вийти
          </button>
        </div>
      </div>

      {/* Top 4 KPI Metrics Cards */}
      <div className={styles.metricsGrid}>
        {/* Metric 1: Pushes 24h */}
        <div className={styles.metricCard}>
          <div className={styles.metricCardHeader}>
            <span className={styles.metricLabel}>Пуші за 24 години</span>
            <div className={styles.metricIcon} style={{ color: "var(--accent)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
              </svg>
            </div>
          </div>
          <div className={styles.bigValue}>{pushes.total_24h ?? 0}</div>
          <div className={styles.badgeRow}>
            <span className={`${styles.badge} ${styles.badgeWarning}`}>Web: {pushes.web_24h ?? 0}</span>
            <span className={`${styles.badge} ${styles.badgeSuccess}`}>Telegram: {pushes.tg_24h ?? 0}</span>
          </div>
          <div className={styles.subText}>Всього відправок (пакетів): {pushes.events_count_24h ?? 0}</div>
        </div>

        {/* Metric 2: Registered Users */}
        <div className={styles.metricCard}>
          <div className={styles.metricCardHeader}>
            <span className={styles.metricLabel}>Користувачів у системі</span>
            <div className={styles.metricIcon} style={{ color: "var(--accent-secondary)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
            </div>
          </div>
          <div className={styles.bigValue}>{users.total_registered ?? 0}</div>
          <div className={styles.badgeRow}>
            <span className={styles.badge}>Web: {users.web_subscribers ?? 0}</span>
            <span className={styles.badge}>Telegram: {users.telegram_subscribers ?? 0}</span>
          </div>
          <div className={styles.subText}>
            У пам&apos;яті: Web {users.in_memory_active_web ?? 0} • TG {users.in_memory_active_tg ?? 0}
          </div>
        </div>

        {/* Metric 3: Database */}
        <div className={styles.metricCard}>
          <div className={styles.metricCardHeader}>
            <span className={styles.metricLabel}>База даних</span>
            <div className={styles.metricIcon} style={{ color: dbData.status === "online" ? "var(--success)" : "var(--danger)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
              </svg>
            </div>
          </div>
          <div className={styles.bigValue} style={{ fontSize: "1.75rem" }}>
            <span className={dbData.status === "online" ? styles.badgeSuccess : styles.badgeDanger} style={{ padding: "0.2rem 0.7rem", borderRadius: "8px" }}>
              {dbData.status === "online" ? "Online" : "Offline"}
            </span>
          </div>
          <div className={styles.badgeRow}>
            <span className={styles.badge}>Таблиць: {Object.keys(dbData.tables || {}).length}</span>
            {dbData.support_tickets_open !== undefined && (
              <span className={`${styles.badge} ${styles.badgeWarning}`}>
                Тікети: {dbData.support_tickets_open} відкр.
              </span>
            )}
          </div>
          <div className={styles.subText}>PostgreSQL + SQLAlchemy asyncpg</div>
        </div>

        {/* Metric 4: Redis & Runtime */}
        <div className={styles.metricCard}>
          <div className={styles.metricCardHeader}>
            <span className={styles.metricLabel}>Кеш &amp; Сервіси</span>
            <div className={styles.metricIcon} style={{ color: redis.status === "online" ? "var(--success)" : "var(--warning)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
                <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
                <line x1="6" y1="6" x2="6.01" y2="6"></line>
                <line x1="6" y1="18" x2="6.01" y2="18"></line>
              </svg>
            </div>
          </div>
          <div className={styles.bigValue} style={{ fontSize: "1.75rem" }}>
            <span className={redis.status === "online" ? styles.badgeSuccess : styles.badgeWarning} style={{ padding: "0.2rem 0.7rem", borderRadius: "8px" }}>
              Redis: {redis.status === "online" ? "Online" : "Offline"}
            </span>
          </div>
          <div className={styles.badgeRow}>
            <span className={styles.badge}>Ключів у Redis: {redis.keys_count ?? 0}</span>
            <span className={styles.badge}>Кешування: {stats?.system?.can_cache ? "Увімкн" : "Вимкн"}</span>
          </div>
          <div className={styles.subText}>
            TG Бот: {stats?.system?.notify_bot_online ? "Онлайн" : "Офлайн"}
          </div>
        </div>
      </div>

      {/* Section: Queue Distribution */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <polyline points="16 11 18 13 22 9"></polyline>
            </svg>
            Розподіл користувачів за чергами
          </div>
          <span className={styles.metaText}>Всього підписників: {users.total_registered ?? 0}</span>
        </div>

        <div className={styles.tableResponsive}>
          <table className={styles.customTable}>
            <thead>
              <tr>
                <th>Черга</th>
                <th>Web Push</th>
                <th>Telegram</th>
                <th>Всього</th>
                <th>Частка</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(queueDist).length === 0 ? (
                <tr>
                  <td colSpan="5" className={styles.emptyState}>Немає зареєстрованих підписників</td>
                </tr>
              ) : (
                Object.entries(queueDist).map(([lbl, qData]) => {
                  const maxTotal = Math.max(1, users.total_registered || 1);
                  const pct = Math.round(((qData.total || 0) / maxTotal) * 100);
                  return (
                    <tr key={lbl}>
                      <td>
                        <span className={styles.queueBadge}>Черга {lbl}</span>
                      </td>
                      <td>{qData.web ?? 0}</td>
                      <td>{qData.tg ?? 0}</td>
                      <td>
                        <strong>{qData.total ?? 0}</strong>
                      </td>
                      <td>
                        <div className={styles.progressBarWrap}>
                          <div className={styles.progressBar} style={{ width: `${pct}%` }} />
                        </div>
                        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{pct}%</span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section: Database Tables Stats */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
            Статистика таблиць бази даних
          </div>
          <span className={styles.metaText}>
            Статус: {dbData.status === "online" ? "✅ Підключено" : "⚠️ Офлайн / вимкнено"}
          </span>
        </div>

        {dbData.status === "online" ? (
          <div className={styles.tableResponsive}>
            <table className={styles.customTable}>
              <thead>
                <tr>
                  <th>Таблиця</th>
                  <th>Опис</th>
                  <th>Кількість рядків</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(dbData.tables || {}).map(([tableName, count]) => (
                  <tr key={tableName}>
                    <td><code>{tableName}</code></td>
                    <td>
                      {tableName.includes("subscription") && "Web-push підписки користувачів"}
                      {tableName.includes("tg_sub") && "Підписки Telegram-користувачів на черги"}
                      {tableName === "users" && "Основні записи користувачів"}
                      {tableName === "support_tickets" && "Тікети підтримки (звернення)"}
                      {tableName === "support_admins" && "Адміністратори бота підтримки"}
                      {tableName === "support_bans" && "Заблоковані користувачі"}
                    </td>
                    <td>
                      <strong>{count}</strong>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className={styles.emptyState}>
            База даних наразі не підключена або відключена в конфігурації (<code>DB_ONLINE=false</code>).
            Усі підписки зберігаються в оперативній пам&apos;яті та Redis.
          </div>
        )}
      </div>

      {/* Section: Push History 24h */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            Історія відправки сповіщень (за останні 24 години)
          </div>
          <span className={styles.metaText}>
            Всього доставлено за добу: <strong>{pushes.total_24h ?? 0}</strong>
          </span>
        </div>

        <div className={styles.tableResponsive}>
          <table className={styles.customTable}>
            <thead>
              <tr>
                <th>Час</th>
                <th>Заголовок</th>
                <th>Черга</th>
                <th>Web Push</th>
                <th>Telegram</th>
                <th>Всього відправлено</th>
              </tr>
            </thead>
            <tbody>
              {pushHistory.length === 0 ? (
                <tr>
                  <td colSpan="6" className={styles.emptyState}>
                    За останні 24 години відправок сповіщень не зафіксовано.
                  </td>
                </tr>
              ) : (
                pushHistory.map((item, idx) => (
                  <tr key={idx}>
                    <td>
                      <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                        {item.datetime}
                      </span>
                    </td>
                    <td>
                      <strong>{item.title}</strong>
                    </td>
                    <td>
                      <span className={styles.queueBadge}>{item.queue_label || "Всі"}</span>
                    </td>
                    <td>{item.web_sent}</td>
                    <td>{item.tg_sent}</td>
                    <td>
                      <span className={`${styles.badge} ${styles.badgeSuccess}`}>
                        +{item.total_sent}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

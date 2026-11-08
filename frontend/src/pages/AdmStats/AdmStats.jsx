import { useState, useEffect, useCallback, useMemo } from "react";
import styles from "./AdmStats.module.css";

const apiBase =
  import.meta.env.API_BASE_PATH ||
  import.meta.env.VITE_API_BASE ||
  import.meta.env.VITE_API_BASE_PATH ||
  "/api";

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
      const res = await fetch(`${apiBase}/admin/stats`, {
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

  // Extract structured dashboard data
  const users = stats?.users || {};
  const pushes = stats?.pushes_24h || {};
  const dbData = stats?.database || {};
  const redis = stats?.redis || {};
  const queueDist = users.by_queue || {};
  const subscribersRanking = users.subscribers_ranking || [];
  const pushesRanking = stats?.pushes_ranking || [];
  const graphRequests = stats?.graph_requests || {};
  const graphRanking = graphRequests.ranking || [];
  const pushHistory = pushes.history || [];

  // Calculate highest queue subscribers for chart scale
  const maxQueueSubscribers = useMemo(() => {
    const counts = Object.values(queueDist).map((q) => q.total || 0);
    return Math.max(...counts, 1);
  }, [queueDist]);

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
            <h1 className={styles.loginTitle}>Панель статистики</h1>
            <p className={styles.loginSubtitle}>
              Доступ до статистики бази даних, розсилок та черг захищено паролем
            </p>

            <form onSubmit={handleLogin} className={styles.form}>
              <div className={styles.inputGroup}>
                <label htmlFor="adm-pass">Пароль доступу</label>
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
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Top Header */}
      <div className={styles.dashHeader}>
        <div className={styles.dashTitleBlock}>
          <h1>Статистика сервісу (/stats)</h1>
          <div className={styles.metaText}>
            <span>Сервер: {stats?.server_time || "N/A"}</span>
            {lastUpdated && <span>• Оновлено: {lastUpdated}</span>}
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

      {/* KPI Metric Cards */}
      <div className={styles.metricsGrid}>
        {/* Metric 1: Recipients of pushes */}
        <div className={styles.metricCard}>
          <div className={styles.metricCardHeader}>
            <span className={styles.metricLabel}>Отримувачі сповіщень</span>
            <div className={styles.metricIcon} style={{ color: "var(--accent)" }}>
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
            <span className={`${styles.badge} ${styles.badgeWarning}`}>Web: {users.web_subscribers ?? 0}</span>
            <span className={`${styles.badge} ${styles.badgeSuccess}`}>Telegram: {users.telegram_subscribers ?? 0}</span>
          </div>
          <div className={styles.subText}>
            Активні в пам&apos;яті: Web {users.in_memory_active_web ?? 0} • TG {users.in_memory_active_tg ?? 0}
          </div>
        </div>

        {/* Metric 2: Pushes 24h */}
        <div className={styles.metricCard}>
          <div className={styles.metricCardHeader}>
            <span className={styles.metricLabel}>Пушів за 24 години</span>
            <div className={styles.metricIcon} style={{ color: "var(--accent-strong)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
              </svg>
            </div>
          </div>
          <div className={styles.bigValue}>{pushes.total_24h ?? 0}</div>
          <div className={styles.badgeRow}>
            <span className={styles.badge}>Web: {pushes.web_24h ?? 0}</span>
            <span className={styles.badge}>Telegram: {pushes.tg_24h ?? 0}</span>
          </div>
          <div className={styles.subText}>
            Розсилок (пакетів): {pushes.events_count_24h ?? 0} за добу
          </div>
        </div>

        {/* Metric 3: Graph views / requests */}
        <div className={styles.metricCard}>
          <div className={styles.metricCardHeader}>
            <span className={styles.metricLabel}>Запити графіків</span>
            <div className={styles.metricIcon} style={{ color: "var(--accent-secondary)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
            </div>
          </div>
          <div className={styles.bigValue}>{graphRequests.total_requests ?? 0}</div>
          <div className={styles.badgeRow}>
            <span className={`${styles.badge} ${styles.badgeSuccess}`}>24г: {graphRequests.requests_24h ?? 0}</span>
            {graphRanking[0] && (
              <span className={styles.badge}>Топ: Черга {graphRanking[0].label}</span>
            )}
          </div>
          <div className={styles.subText}>
            Переглядів через сайт та API
          </div>
        </div>

        {/* Metric 4: Database & Redis */}
        <div className={styles.metricCard}>
          <div className={styles.metricCardHeader}>
            <span className={styles.metricLabel}>База даних &amp; Кеш</span>
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
              {dbData.status === "online" ? "DB Online" : "DB Offline"}
            </span>
          </div>
          <div className={styles.badgeRow}>
            <span className={styles.badge}>PostgreSQL: {Object.keys(dbData.tables || {}).length} табл.</span>
            <span className={redis.status === "online" ? styles.badgeSuccess : styles.badge}>
              Redis: {redis.status === "online" ? "Online" : "Offline"}
            </span>
          </div>
          <div className={styles.subText}>
            Ключів у Redis: {redis.keys_count ?? 0}
          </div>
        </div>
      </div>

      {/* SECTION 1: QUEUE VISUAL CHART */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            Діаграма підписників за чергами (12 очередей)
          </div>
          <span className={styles.metaText}>
            Всього підписників на пуші: <strong>{users.total_registered ?? 0}</strong>
          </span>
        </div>

        <div className={styles.chartWrapper}>
          <div className={styles.chartBarsContainer}>
            {Object.entries(queueDist).map(([lbl, qData]) => {
              const total = qData.total || 0;
              const web = qData.web || 0;
              const tg = qData.tg || 0;
              const heightPct = Math.max(6, Math.round((total / maxQueueSubscribers) * 100));
              const webPct = total > 0 ? (web / total) * 100 : 50;

              return (
                <div key={lbl} className={styles.chartBarCol}>
                  <div className={styles.chartBarValue}>{total}</div>
                  <div className={styles.chartBarTrack}>
                    <div
                      className={styles.chartBarFill}
                      style={{ height: `${heightPct}%` }}
                      title={`Черга ${lbl}: ${total} підписників (Web: ${web}, TG: ${tg})`}
                    >
                      {total > 0 && (
                        <>
                          <div className={styles.chartSegmentWeb} style={{ height: `${webPct}%` }} />
                          <div className={styles.chartSegmentTg} style={{ height: `${100 - webPct}%` }} />
                        </>
                      )}
                    </div>
                  </div>
                  <div className={styles.chartBarLabel}>
                    <span className={styles.queueBadgeSmall}>{lbl}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className={styles.chartLegend}>
            <div className={styles.legendItem}>
              <span className={styles.legendDotWeb} />
              <span>Web Push</span>
            </div>
            <div className={styles.legendItem}>
              <span className={styles.legendDotTg} />
              <span>Telegram</span>
            </div>
            <div className={styles.legendItem} style={{ marginLeft: "auto", fontSize: "0.8rem", color: "var(--text-muted)" }}>
              * Висота стовпчика пропорційна кількості підписників
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 2: SUBSCRIBERS RANKING */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="8" r="7"></circle>
              <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline>
            </svg>
            Рейтинг черг за кількістю підписок
          </div>
          <span className={styles.metaText}>Сортування за спаданням аудиторії</span>
        </div>

        <div className={styles.tableResponsive}>
          <table className={styles.customTable}>
            <thead>
              <tr>
                <th style={{ width: "60px" }}>Місце</th>
                <th>Черга</th>
                <th>Web Push</th>
                <th>Telegram</th>
                <th>Всього</th>
                <th>Частка від усіх</th>
              </tr>
            </thead>
            <tbody>
              {subscribersRanking.length === 0 ? (
                <tr>
                  <td colSpan="6" className={styles.emptyState}>Немає даних про підписників</td>
                </tr>
              ) : (
                subscribersRanking.map((item, idx) => {
                  const medal = idx === 0 ? "#1" : idx === 1 ? "#2" : idx === 2 ? "#3" : `#${idx + 1}`;
                  return (
                    <tr key={item.label}>
                      <td>
                        <span className={styles.rankBadge}>{medal}</span>
                      </td>
                      <td>
                        <span className={styles.queueBadge}>Черга {item.label}</span>
                      </td>
                      <td>{item.web}</td>
                      <td>{item.tg}</td>
                      <td>
                        <strong>{item.total}</strong>
                      </td>
                      <td>
                        <div className={styles.progressBarWrap}>
                          <div className={styles.progressBar} style={{ width: `${item.percent}%` }} />
                        </div>
                        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{item.percent}%</span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 3: PUSHES RANKING */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
            </svg>
            Рейтинг черг за надісланими пушами
          </div>
          <span className={styles.metaText}>
            Скільки сповіщень доставлено по кожній черзі
          </span>
        </div>

        <div className={styles.tableResponsive}>
          <table className={styles.customTable}>
            <thead>
              <tr>
                <th style={{ width: "60px" }}>Місце</th>
                <th>Черга</th>
                <th>Доставлено за 24г</th>
                <th>Всього доставлено</th>
                <th>Розсилок (подій)</th>
                <th>Останній пуш</th>
              </tr>
            </thead>
            <tbody>
              {pushesRanking.length === 0 ? (
                <tr>
                  <td colSpan="6" className={styles.emptyState}>Немає зафіксованих пушів</td>
                </tr>
              ) : (
                pushesRanking.map((item, idx) => {
                  const medal = idx === 0 ? "#1" : idx === 1 ? "#2" : idx === 2 ? "#3" : `#${idx + 1}`;
                  return (
                    <tr key={item.label}>
                      <td>
                        <span className={styles.rankBadge}>{medal}</span>
                      </td>
                      <td>
                        <span className={styles.queueBadge}>{item.label.startsWith("Всі") ? item.label : `Черга ${item.label}`}</span>
                      </td>
                      <td>
                        {item.total_24h > 0 ? (
                          <span className={`${styles.badge} ${styles.badgeSuccess}`}>+{item.total_24h}</span>
                        ) : (
                          <span style={{ color: "var(--text-muted)" }}>0</span>
                        )}
                      </td>
                      <td>
                        <strong>{item.total_sent}</strong>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          Web: {item.web_sent} • TG: {item.tg_sent}
                        </div>
                      </td>
                      <td>{item.events_count}</td>
                      <td>
                        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                          {item.last_sent || "—"}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 4: GRAPH REQUESTS & POPULARITY */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            Запити графіків &amp; Топ переглядів
          </div>
          <span className={styles.metaText}>
            Всього переглядів: <strong>{graphRequests.total_requests ?? 0}</strong> • За добу: <strong>{graphRequests.requests_24h ?? 0}</strong>
          </span>
        </div>

        <div className={styles.tableResponsive}>
          <table className={styles.customTable}>
            <thead>
              <tr>
                <th style={{ width: "60px" }}>Місце</th>
                <th>Черга графіка</th>
                <th>Запитів сьогодні/24г</th>
                <th>Всього запитів</th>
                <th>Частка запитів</th>
              </tr>
            </thead>
            <tbody>
              {graphRanking.length === 0 ? (
                <tr>
                  <td colSpan="5" className={styles.emptyState}>Запитів графіків поки не зафіксовано</td>
                </tr>
              ) : (
                graphRanking.map((item, idx) => {
                  const medal = idx === 0 ? "#1" : idx === 1 ? "#2" : idx === 2 ? "#3" : `#${idx + 1}`;
                  return (
                    <tr key={item.label}>
                      <td>
                        <span className={styles.rankBadge}>{medal}</span>
                      </td>
                      <td>
                        <span className={styles.queueBadge}>Черга {item.label}</span>
                      </td>
                      <td>
                        {item.today_requests > 0 ? (
                          <span className={`${styles.badge} ${styles.badgeSuccess}`}>+{item.today_requests}</span>
                        ) : (
                          <span style={{ color: "var(--text-muted)" }}>0</span>
                        )}
                      </td>
                      <td>
                        <strong>{item.total_requests}</strong>
                      </td>
                      <td>
                        <div className={styles.progressBarWrap}>
                          <div className={styles.progressBar} style={{ width: `${item.percent}%` }} />
                        </div>
                        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{item.percent}%</span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 5: DATABASE TABLES STATS */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
            Статистика бази даних (PostgreSQL)
          </div>
          <span className={styles.metaText}>
            Статус: {dbData.status === "online" ? "Підключено" : "Офлайн / вимкнено"}
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

      {/* SECTION 6: PUSH HISTORY 24H */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
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
                <th>Всього надіслано</th>
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

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { queueOptions } from '../../lib/ztoe.js';
import {
  fetchVapidPublicKey,
  loadQueueStatus,
  subscribeWebPush,
  unsubscribeWebPush,
} from '../../lib/api.js';
import ClockDial from './ClockDial.jsx';
import AddressSearch from './AddressSearch.jsx';
import styles from './Graph.module.css';

// ── helpers ──────────────────────────────────────────────────────────────────

const defaultStatuses = Array(48).fill(false);

function hasSavedQueueInStorage() {
  if (typeof window === 'undefined') return false;
  try {
    const savedQ = localStorage.getItem('queueSelector');
    if (savedQ && queueOptions.includes(savedQ)) return true;
    const savedAddr = localStorage.getItem('savedUserAddress');
    if (savedAddr) return true;
  } catch (_) {
    /* ignore */
  }
  return false;
}

function loadQueueFromStorage() {
  if (typeof window === 'undefined') return '31';
  try {
    const saved = localStorage.getItem('queueSelector');
    if (saved && queueOptions.includes(saved)) return saved;
  } catch (_) {
    /* ignore */
  }
  return '31';
}

function loadViewModeFromStorage() {
  if (typeof window === 'undefined') return 'dial';
  try {
    const saved = localStorage.getItem('graphViewMode');
    if (saved && ['dial', 'timeline', 'intervals'].includes(saved)) return saved;
  } catch (_) {
    /* ignore */
  }
  return 'dial';
}

function normalizeStatuses(data = []) {
  const normalized = [];
  const len = data.length;

  for (let h = 0; h < 24; h += 1) {
    let left = false;
    let right = false;

    if (len >= 48) {
      left = Boolean(data[h * 2] ?? 0);
      right = Boolean(data[h * 2 + 1] ?? 0);
    } else if (len === 24) {
      const v = Boolean(data[h] ?? 0);
      left = v;
      right = v;
    } else if (len > 0) {
      left = Boolean(data[Math.min(h * 2, len - 1)] ?? 0);
      right = Boolean(data[Math.min(h * 2 + 1, len - 1)] ?? 0);
    }

    normalized.push(left);
    normalized.push(right);
  }

  return normalized;
}

function formatHalfHour(index) {
  if (index >= 48) return '24:00';
  const hours = Math.floor(index / 2);
  const minutes = index % 2 === 0 ? '00' : '30';
  return `${String(hours).padStart(2, '0')}:${minutes}`;
}

function collectOutageRanges(statuses) {
  const ranges = [];
  let start = null;

  for (let i = 0; i <= statuses.length; i += 1) {
    const off = statuses[i] ?? false;

    if (off && start === null) start = i;

    const isBoundary = !off || i === statuses.length;
    if (isBoundary && start !== null) {
      ranges.push({ start, end: i });
      start = null;
    }
  }

  return ranges.map(({ start, end }) => ({
    start: formatHalfHour(start),
    end: formatHalfHour(end),
    startIdx: start,
    endIdx: end,
  }));
}

function getCurrentSlotIndex() {
  const now = new Date();
  return now.getHours() * 2 + (now.getMinutes() >= 30 ? 1 : 0);
}

function getCurrentMinutes() {
  const now = new Date();
  return now.getHours() * 60 + now.getMinutes();
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i += 1) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

const SOURCE_LABELS = {
  api: { text: 'Сервер ✓', cls: 'api' },
  ztoe: { text: 'ЖОЕ (резерв)', cls: 'ztoe' },
  cache: { text: 'Кеш', cls: 'cache' },
  none: { text: 'Нема даних', cls: 'none' },
};

const QUEUE_GROUPS = ['1', '2', '3', '4', '5', '6'];

// ── SVG Timeline (Linear Scale) ──────────────────────────────────────────────

function Timeline({ statuses, currentMinutes }) {
  const svgRef = useRef(null);
  const [svgWidth, setSvgWidth] = useState(840);
  const [tooltip, setTooltip] = useState(null);
  const HEIGHT = 60;

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      setSvgWidth(entries[0].contentRect.width || 840);
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const segmentWidth = svgWidth / 48;
  const needleX = (currentMinutes / 1440) * svgWidth;

  const hourLabels = [];
  for (let h = 0; h <= 24; h += 3) {
    const x = (h / 24) * svgWidth;
    hourLabels.push({ h, x });
  }

  function handleMouseMove(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = e.clientX - rect.left;
    const idx = Math.floor((relX / svgWidth) * 48);
    if (idx < 0 || idx > 47) {
      setTooltip(null);
      return;
    }
    const isOff = statuses[idx] ?? false;
    const time = `${formatHalfHour(idx)}–${formatHalfHour(idx + 1)}`;
    setTooltip({ x: relX, text: `${time}  ${isOff ? 'Відключення' : 'Є світло'}` });
  }

  return (
    <div className={styles.timelineWrap}>
      <svg
        ref={svgRef}
        className={styles.timelineSvg}
        viewBox={`0 0 ${svgWidth} ${HEIGHT}`}
        preserveAspectRatio="none"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
        aria-label="Лінійний графік відключень на сьогодні"
      >
        <defs>
          <linearGradient id="timeline-outage-grad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#ffc94a" />
            <stop offset="100%" stopColor="#ff7a5a" />
          </linearGradient>
        </defs>

        {/* 48 Segments */}
        {statuses.map((isOff, idx) => {
          const x = idx * segmentWidth;
          if (isOff) {
            return (
              <rect
                key={idx}
                x={x}
                y={0}
                width={Math.max(1, segmentWidth - 0.5)}
                height={HEIGHT}
                fill="url(#timeline-outage-grad)"
                opacity={0.92}
                rx={1}
              />
            );
          }
          return (
            <rect
              key={idx}
              x={x}
              y={0}
              width={Math.max(1, segmentWidth - 0.5)}
              height={HEIGHT}
              fill="rgba(95, 245, 203, 0.12)"
              stroke="rgba(95, 245, 203, 0.22)"
              strokeWidth={0.5}
              rx={1}
            />
          );
        })}

        {/* Hour vertical ticks */}
        {hourLabels.map(({ h, x }) => (
          <line
            key={h}
            x1={x}
            y1={0}
            x2={x}
            y2={HEIGHT}
            stroke="rgba(255, 255, 255, 0.12)"
            strokeWidth={1}
          />
        ))}

        {/* Real-time needle */}
        <line
          x1={needleX}
          y1={0}
          x2={needleX}
          y2={HEIGHT}
          stroke="var(--cyan)"
          strokeWidth={2.2}
          strokeDasharray="4 2"
        />

        {/* Needle badge */}
        <rect
          x={Math.max(2, Math.min(needleX - 22, svgWidth - 46))}
          y={2}
          width={44}
          height={16}
          rx={4}
          fill="#07090f"
          stroke="var(--cyan)"
          strokeWidth={1}
        />
        <text
          x={Math.max(24, Math.min(needleX, svgWidth - 24))}
          y={13}
          textAnchor="middle"
          fontSize={10}
          fontFamily="var(--font)"
          fontWeight={700}
          fill="var(--cyan)"
        >
          {`${String(Math.floor(currentMinutes / 60)).padStart(2, '0')}:${String(currentMinutes % 60).padStart(2, '0')}`}
        </text>
      </svg>

      {/* Hour labels row */}
      <div className={styles.timelineLabels}>
        {hourLabels.map(({ h, x }) => (
          <span
            key={h}
            className={styles.timelineLabel}
            style={{ left: `${(x / svgWidth) * 100}%` }}
          >
            {String(h).padStart(2, '0')}:00
          </span>
        ))}
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className={styles.tooltip}
          style={{ left: Math.min(Math.max(10, tooltip.x), svgWidth - 190) }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}

// ── Queue selector ────────────────────────────────────────────────────────────

function QueueSelector({ queue, onChange }) {
  const selectedGroup = queue[0];
  const selectedSub = queue[1];

  return (
    <div className={styles.queueSelector}>
      <div className={styles.queueSelectorHeader}>
        <span className={styles.queueSelectorHint}>1. Оберіть номер групи:</span>
      </div>
      <div className={styles.queueGroups}>
        {QUEUE_GROUPS.map((g) => (
          <button
            key={g}
            type="button"
            className={`${styles.groupBtn} ${selectedGroup === g ? styles.groupBtnActive : ''}`}
            onClick={() => onChange(`${g}${selectedSub}`)}
            aria-label={`Черга ${g}`}
          >
            Черга {g}
          </button>
        ))}
      </div>

      <div className={styles.queueSelectorHeader}>
        <span className={styles.queueSelectorHint}>2. Оберіть підчергу:</span>
      </div>
      <div className={styles.subQueues}>
        {['1', '2'].map((s) => (
          <button
            key={s}
            type="button"
            className={`${styles.subBtn} ${selectedSub === s ? styles.subBtnActive : ''}`}
            onClick={() => onChange(`${selectedGroup}${s}`)}
            aria-label={`Підчерга .${s}`}
          >
            Підчерга .{s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Notifications Card (Web Push + Telegram Bot + News Channel) ───────────────

function NotificationsCard({ queueLabel, queue }) {
  const [isSupported, setIsSupported] = useState(true);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isPushLoading, setIsPushLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  // Check Web Push support and current subscription state on mount
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const supported =
      'Notification' in window &&
      'serviceWorker' in navigator &&
      'PushManager' in window;

    setIsSupported(supported);

    if (supported) {
      navigator.serviceWorker.ready
        .then((reg) => reg.pushManager.getSubscription())
        .then((sub) => {
          setIsSubscribed(Boolean(sub));
        })
        .catch(() => {
          setIsSubscribed(false);
        });
    }
  }, []);

  const handleSubscribe = async () => {
    if (!isSupported) {
      alert('Ваш браузер не підтримує Web Push. Скористайтеся нашим Telegram-ботом!');
      return;
    }

    setIsPushLoading(true);
    setStatusMsg(null);

    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        setStatusMsg({ type: 'error', text: 'Дозвіл на сповіщення не надано у браузері.' });
        setIsPushLoading(false);
        return;
      }

      const vapidKey = await fetchVapidPublicKey();
      if (!vapidKey) {
        setStatusMsg({ type: 'error', text: 'Не вдалося отримати VAPID ключ сервера.' });
        setIsPushLoading(false);
        return;
      }

      let reg = await navigator.serviceWorker.getRegistration();
      if (!reg) {
        reg = await navigator.serviceWorker.register('/sw.js');
      }
      await navigator.serviceWorker.ready;

      let sub = await reg.pushManager.getSubscription();
      if (!sub) {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidKey),
        });
      }

      const res = await subscribeWebPush(queue, sub);
      setIsSubscribed(true);
      setStatusMsg({
        type: 'success',
        text: res?.msg || `Ви успішно підписалися на сповіщення для черги ${queueLabel}!`,
      });
    } catch (err) {
      setStatusMsg({
        type: 'error',
        text: 'Помилка підписки. Спробуйте пізніше або використовуйте Telegram-бота.',
      });
    } finally {
      setIsPushLoading(false);
    }
  };

  const handleUnsubscribe = async () => {
    setIsPushLoading(true);
    setStatusMsg(null);

    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();

      if (sub) {
        try {
          await unsubscribeWebPush(sub);
        } catch (_) {
          /* ignore server error */
        }
        await sub.unsubscribe();
      }

      setIsSubscribed(false);
      setStatusMsg({ type: 'info', text: 'Підписку на Web Push сповіщення скасовано.' });
    } catch (_) {
      setStatusMsg({ type: 'error', text: 'Не вдалося скасувати підписку.' });
    } finally {
      setIsPushLoading(false);
    }
  };

  return (
    <section className={styles.card}>
      <div className={styles.cardTop}>
        <div>
          <div className={styles.notifyCardTitleRow}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className={styles.notifyTitleIcon}>
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <h2 className={styles.cardTitle}>Сповіщення та Telegram</h2>
          </div>
          <p className={styles.cardDesc}>
            Отримуйте попередження за 1 годину до відключення для черги {queueLabel} та оперативні новини
          </p>
        </div>
      </div>

      <div className={styles.notifyGrid}>
        {/* Web Push Card */}
        <div className={styles.notifyChannelCard}>
          <div className={styles.notifyChannelHeader}>
            <div className={styles.notifyChannelIconWrap}>
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
            </div>
            <div className={styles.notifyMeta}>
              <div className={styles.notifyChannelTitle}>Браузерні сповіщення (Web Push)</div>
              <div className={styles.notifyChannelSub}>
                Працюють на смартфонах Android, iPhone (PWA) та на комп&rsquo;ютері
              </div>
            </div>
          </div>

          <div className={styles.notifyChannelBody}>
            {isSubscribed ? (
              <div className={styles.subscribedStatusRow}>
                <span className={styles.subscribedBadge}>Активна підписка (Черга {queueLabel})</span>
                <button
                  type="button"
                  className={styles.unsubscribeBtn}
                  onClick={handleUnsubscribe}
                  disabled={isPushLoading}
                >
                  {isPushLoading ? 'Скасування…' : 'Скасувати підписку'}
                </button>
              </div>
            ) : (
              <button
                type="button"
                className={styles.subscribeBtn}
                onClick={handleSubscribe}
                disabled={isPushLoading}
              >
                {isPushLoading ? 'Підключення…' : `Увімкнути для черги ${queueLabel}`}
              </button>
            )}

            {statusMsg && (
              <div
                className={`${styles.notifyStatusAlert} ${
                  statusMsg.type === 'error'
                    ? styles.notifyStatusError
                    : styles.notifyStatusSuccess
                }`}
              >
                {statusMsg.text}
              </div>
            )}
          </div>
        </div>

        {/* Telegram Bot Card */}
        <div className={styles.notifyChannelCard}>
          <div className={styles.notifyChannelHeader}>
            <div className={styles.notifyChannelIconTelegram}>
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.52 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" />
              </svg>
            </div>
            <div className={styles.notifyMeta}>
              <div className={styles.notifyChannelTitle}>Telegram-бот сповіщень</div>
              <div className={styles.notifyChannelSub}>
                Персональний графік та надійні сповіщення без збоїв
              </div>
            </div>
          </div>

          <div className={styles.notifyChannelBody}>
            <a
              href="https://t.me/likhtarychok_bot"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.telegramBtn}
            >
              <span>Відкрити @likhtarychok_bot</span>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </a>
          </div>
        </div>

        {/* Telegram News Channel Card */}
        <div className={styles.notifyChannelCard}>
          <div className={styles.notifyChannelHeader}>
            <div className={styles.notifyChannelIconNews}>
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.52 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" />
              </svg>
            </div>
            <div className={styles.notifyMeta}>
              <div className={styles.notifyChannelTitle}>Новинний Telegram-канал</div>
              <div className={styles.notifyChannelSub}>
                Оперативні новини щодо відключень, аварій та оновлень графіків у Житомирі
              </div>
            </div>
          </div>

          <div className={styles.notifyChannelBody}>
            <a
              href="https://t.me/likhtarychok_org"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.telegramChannelBtn}
            >
              <span>Підписатися на @likhtarychok_org</span>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Main Page Component ───────────────────────────────────────────────────────

export default function Graph() {
  const [isQueuePreselected] = useState(() => hasSavedQueueInStorage());
  const [queue, setQueue] = useState(() => loadQueueFromStorage());
  const [viewMode, setViewMode] = useState(() => loadViewModeFromStorage());
  const [selectionTab, setSelectionTab] = useState('address'); // 'address' | 'queue'
  const [statuses, setStatuses] = useState(defaultStatuses);
  const [source, setSource] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentMinutes, setCurrentMinutes] = useState(() => getCurrentMinutes());

  // Update current time minutes every 20 seconds
  useEffect(() => {
    const id = setInterval(() => setCurrentMinutes(getCurrentMinutes()), 20_000);
    return () => clearInterval(id);
  }, []);

  const handleSelectQueue = useCallback((newQueue) => {
    setQueue(newQueue);
    try {
      localStorage.setItem('queueSelector', newQueue);
    } catch (_) {
      /* ignore */
    }
  }, []);

  const handleSelectViewMode = useCallback((mode) => {
    setViewMode(mode);
    try {
      localStorage.setItem('graphViewMode', mode);
    } catch (_) {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem('graphViewMode', viewMode);
    } catch (_) {
      /* ignore */
    }
  }, [viewMode]);

  const fetchStatuses = useCallback(async (q) => {
    setIsLoading(true);
    try {
      const { data, source: src } = await loadQueueStatus(q);
      setStatuses(data.length > 0 ? normalizeStatuses(data) : defaultStatuses);
      setSource(src);
    } catch (_) {
      setStatuses(defaultStatuses);
      setSource('none');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatuses(queue);
  }, [queue, fetchStatuses]);

  // Auto-refresh every 5 min
  useEffect(() => {
    const id = setInterval(() => fetchStatuses(queue), 5 * 60_000);
    return () => clearInterval(id);
  }, [queue, fetchStatuses]);

  const outageRanges = useMemo(() => collectOutageRanges(statuses), [statuses]);
  const currentSlot = getCurrentSlotIndex();
  const queueLabel = `${queue[0]}.${queue[1]}`;
  const srcInfo = source ? SOURCE_LABELS[source] : null;

  const hasData = statuses.some(Boolean);

  // Stats calculation
  const totalOffSlots = statuses.filter(Boolean).length;
  const totalOffHours = (totalOffSlots * 0.5).toFixed(totalOffSlots % 2 === 0 ? 0 : 1);
  const totalOnHours = (24 - Number(totalOffHours)).toFixed(totalOffSlots % 2 === 0 ? 0 : 1);
  const isCurrentOff = Boolean(statuses[currentSlot]);

  // ── Section: Queue selection ────────────────────────────────────────────────
  const queueSelectionSection = (
    <section className={styles.card}>
      <div className={styles.cardTop}>
        <div>
          <h2 className={styles.cardTitle}>Вибір черги</h2>
          <p className={styles.cardDesc}>
            Знайдіть свою чергу за адресою або оберіть номер вручну
          </p>
        </div>

        {/* Segmented Switcher */}
        <div className={styles.subTabSwitcher}>
          <button
            type="button"
            className={`${styles.subTabBtn} ${
              selectionTab === 'address' ? styles.subTabBtnActive : ''
            }`}
            onClick={() => setSelectionTab('address')}
          >
            Пошук за адресою
          </button>
          <button
            type="button"
            className={`${styles.subTabBtn} ${
              selectionTab === 'queue' ? styles.subTabBtnActive : ''
            }`}
            onClick={() => setSelectionTab('queue')}
          >
            Ручний вибір
          </button>
        </div>
      </div>

      {selectionTab === 'address' ? (
        <AddressSearch onSelectQueue={handleSelectQueue} currentQueue={queue} />
      ) : (
        <QueueSelector queue={queue} onChange={handleSelectQueue} />
      )}
    </section>
  );

  return (
    <div className={styles.page}>
      {/* ── Sub-header with region and current queue indicator ── */}
      <header className={styles.heroHeader}>
        <div className={styles.heroInner}>
          <div className={styles.brandRow}>
            <span className={styles.logoCity}>Житомирська область</span>
            <div className={styles.headerRightActions}>
              <div className={styles.activeQueuePill} title="Обрана черга">
                <span className={styles.activeQueueText}>Черга {queueLabel}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className={styles.main}>
        {/* If user hasn't selected a queue before, show selector first */}
        {!isQueuePreselected && queueSelectionSection}

        {/* ── BLOCK 1: Primary Visualization (Clock Dial / Timeline / Intervals) ── */}
        <section className={`${styles.card} ${styles.heroVisualCard} ${isLoading ? styles.cardFaded : ''}`}>
          <div className={styles.cardTop}>
            <div className={styles.heroCardHeader}>
              <h2 className={styles.cardTitle}>Графік відключень · Черга {queueLabel}</h2>
              <p className={styles.cardDesc}>
                {hasData
                  ? `Без світла: ${totalOffHours} год · Зі світлом: ${totalOnHours} год`
                  : 'Завантаження або відсутність графіка на добу'}
              </p>
            </div>

            <div className={styles.cardActions}>
              {/* View Switcher: Clock Dial / Timeline / Intervals */}
              <div className={styles.viewModeToggle} role="group" aria-label="Вид графіка">
                <button
                  type="button"
                  className={`${styles.viewToggleBtn} ${viewMode === 'dial' ? styles.viewToggleBtnActive : ''}`}
                  onClick={() => handleSelectViewMode('dial')}
                  title="Циферблат годинника"
                >
                  Циферблат
                </button>
                <button
                  type="button"
                  className={`${styles.viewToggleBtn} ${viewMode === 'timeline' ? styles.viewToggleBtnActive : ''}`}
                  onClick={() => handleSelectViewMode('timeline')}
                  title="Лінійна шкала"
                >
                  Шкала
                </button>
                <button
                  type="button"
                  className={`${styles.viewToggleBtn} ${viewMode === 'intervals' ? styles.viewToggleBtnActive : ''}`}
                  onClick={() => handleSelectViewMode('intervals')}
                  title="Список інтервалів відключень"
                >
                  Час без світла
                </button>
              </div>

              {srcInfo && (
                <span className={`${styles.sourceBadge} ${styles[`source_${srcInfo.cls}`]}`}>
                  {srcInfo.text}
                </span>
              )}

              <button
                type="button"
                className={`${styles.refreshBtn} ${isLoading ? styles.refreshBtnSpinning : ''}`}
                onClick={() => fetchStatuses(queue)}
                disabled={isLoading}
                aria-label="Оновити графік"
              >
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 2v6h-6" />
                  <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
                  <path d="M3 22v-6h6" />
                  <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
                </svg>
                <span className={styles.refreshBtnText}>{isLoading ? '…' : 'Оновити'}</span>
              </button>
            </div>
          </div>

          {/* Clock Dial View */}
          {viewMode === 'dial' && (
            <div className={styles.clockDialSection}>
              <ClockDial
                statuses={statuses}
                currentMinutes={currentMinutes}
                queueLabel={queueLabel}
              />
            </div>
          )}

          {/* Linear Timeline View */}
          {viewMode === 'timeline' && (
            <div className={styles.linearTimelineSection}>
              <Timeline statuses={statuses} currentMinutes={currentMinutes} />
            </div>
          )}

          {/* Intervals View ("Час без світла") */}
          {viewMode === 'intervals' && (
            <div className={styles.intervalsVisualSection}>
              {/* Status Header Strip */}
              <div className={styles.intervalsStatusStrip}>
                <div className={styles.intervalsStatusLeft}>
                  <span
                    className={`${styles.intervalsStatusDot} ${
                      isCurrentOff ? styles.intervalsStatusDotOff : styles.intervalsStatusDotOn
                    }`}
                  />
                  <span className={styles.intervalsStatusLabel}>
                    {isCurrentOff ? 'Зараз відключення' : 'Зараз світло є'}
                  </span>
                </div>
                <div className={styles.intervalsStatusRight}>
                  Всього без світла: <strong>{totalOffHours} год</strong>
                </div>
              </div>

              {/* Intervals List */}
              <div className={styles.intervalsCardList}>
                {!hasData && (
                  <p className={styles.emptyState}>Немає даних щодо графіка на сьогодні</p>
                )}

                {hasData && outageRanges.length === 0 && (
                  <div className={styles.emptyStateGood}>
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                    <p>Сьогодні відключень для черги {queueLabel} не заплановано</p>
                  </div>
                )}

                {hasData &&
                  outageRanges.map(({ start, end, startIdx, endIdx }) => {
                    const isActive = currentSlot >= startIdx && currentSlot < endIdx;
                    const isPast = currentSlot >= endIdx;
                    const durationHours = (endIdx - startIdx) * 0.5;
                    const durFormatted = `${durationHours % 1 === 0 ? durationHours : durationHours} год`;

                    return (
                      <div
                        key={`${start}-${end}`}
                        className={`${styles.intervalRowCard} ${
                          isActive
                            ? styles.intervalRowActive
                            : isPast
                            ? styles.intervalRowPast
                            : styles.intervalRowUpcoming
                        }`}
                      >
                        <div className={styles.intervalRowLeft}>
                          <span className={styles.intervalRowTime}>
                            {start} – {end}
                          </span>
                          <span className={styles.intervalRowDuration}>
                            {durFormatted}
                          </span>
                        </div>

                        <div className={styles.intervalRowRight}>
                          {isActive && (
                            <span className={styles.intervalBadgeActive}>
                              Зараз відключення
                            </span>
                          )}
                          {!isActive && !isPast && (
                            <span className={styles.intervalBadgeUpcoming}>
                              Заплановано
                            </span>
                          )}
                          {isPast && (
                            <span className={styles.intervalBadgePast}>
                              Минуло
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Chart Legend (only for dial & timeline views) */}
          {viewMode !== 'intervals' && (
            <div className={styles.legend}>
              <span className={styles.legendItem}>
                <span className={styles.legendDotOff} /> Відключення
              </span>
              <span className={styles.legendItem}>
                <span className={styles.legendDotOn} /> Є світло
              </span>
              <span className={styles.legendItem}>
                <span className={styles.legendNeedle} /> Зараз
              </span>
            </div>
          )}
        </section>

        {/* If user already had a saved queue, render selector here */}
        {isQueuePreselected && queueSelectionSection}

        {/* ── BLOCK 3: Push Notifications & Telegram Channels ── */}
        <NotificationsCard queueLabel={queueLabel} queue={queue} />

        {/* ── Footer Note ── */}
        <footer className={styles.footer}>
          <p>Дані оновлюються автоматично кожні 5 хвилин · Житомиробленерго (ЖОЕ)</p>
          <p>Офіційний графік може оперативно змінюватися за розпорядженням НЕК &laquo;Укренерго&raquo;</p>
        </footer>
      </main>
    </div>
  );
}

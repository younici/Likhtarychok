/*
 * Клієнтський резервний парсер графіка з сайту Житомиробленерго.
 * Використовується, коли API-сервер недоступний: тягнемо публічну сторінку
 * через CORS-проксі, розбираємо таблицю для ВСІХ черг одразу та запам'ятовуємо
 * результат у localStorage.
 */

export const queueOptions = ["11", "12", "21", "22", "31", "32", "41", "42", "51", "52", "61", "62"];

const ZTOE_URL = "https://www.ztoe.com.ua/unhooking-search.php";
const CACHE_KEY = "ztoeScheduleCache";
const SLOTS_PER_DAY = 48;

// Проксі пробуємо по черзі: сайт ЖОЕ не віддає CORS-заголовки.
// r.jina.ai з X-Return-Format віддає сирий HTML (зі стилями) вже в UTF-8,
// allorigins пропускає байти як є — тобто windows-1251.
const corsProxies = [
  {
    url: (target) => `https://r.jina.ai/${target}`,
    headers: { "X-Return-Format": "html" },
    encoding: "utf-8",
  },
  {
    url: (target) => `https://api.allorigins.win/raw?url=${encodeURIComponent(target)}`,
    headers: {},
    encoding: "windows-1251",
  },
  {
    url: (target) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(target)}`,
    headers: {},
    encoding: "windows-1251",
  },
];

function todayKey() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function decodeHtml(buffer, encoding) {
  try {
    return new TextDecoder(encoding).decode(buffer);
  } catch (_) {
    // Стилі та розмітка — чистий ASCII, тож для парсингу вистачить і utf-8.
    return new TextDecoder("utf-8", { fatal: false }).decode(buffer);
  }
}

async function fetchZtoeHtml() {
  let lastError = null;

  for (const proxy of corsProxies) {
    try {
      const response = await fetch(proxy.url(`${ZTOE_URL}?t=${Date.now()}`), {
        headers: { Accept: "text/html", ...proxy.headers },
      });
      if (!response.ok) throw new Error(`Проксі відповів ${response.status}`);

      const html = decodeHtml(await response.arrayBuffer(), proxy.encoding);
      if (html.includes("unhooking-search")) return html;
      throw new Error("Неочікуваний вміст сторінки");
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError ?? new Error("Не вдалося завантажити сторінку ЖОЕ");
}

function cellIsOff(cell) {
  const background = (cell.getAttribute("style") ?? "")
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("background"));

  if (!background) return false;

  const color = background.split(":", 2)[1]?.trim().toLowerCase() ?? "";
  return color !== "" && color !== "#ffffff" && color !== "white" && color !== "#fff";
}

/** Розбирає HTML сторінки ЖОЕ у мапу { "11": [48 boolean], ... }. */
export function parseAllQueues(html) {
  const doc = new DOMParser().parseFromString(html, "text/html");

  // Шукаємо таблицю за структурою, а не за індексом: розмітка ЖОЕ не валідна,
  // і браузерний парсер може переставити вкладені таблиці та форми.
  const hasScheduleRows = (candidate) =>
    Array.from(candidate.querySelectorAll("tr")).some(
      (row) => row.querySelectorAll("td").length >= SLOTS_PER_DAY
    );

  const candidates = Array.from(doc.querySelectorAll("table")).filter(hasScheduleRows);
  // Таблиця графіка вкладена у таблицю-обгортку, тож беремо найглибшого кандидата —
  // того, всередині якого немає іншої таблиці з такими ж рядками.
  const table = candidates.find(
    (candidate) => !Array.from(candidate.querySelectorAll("table")).some(hasScheduleRows)
  );
  if (!table) throw new Error("Таблицю графіка не знайдено");

  const rows = Array.from(table.querySelectorAll("tr")).filter(
    (row) => row.querySelectorAll("td").length >= SLOTS_PER_DAY
  );
  if (rows.length < queueOptions.length) throw new Error("Неповна таблиця графіка");

  // Рядок з годинами теж має 48+ комірок, тож беремо останні 12 — це черги 1.1…6.2.
  const queueRows = rows.slice(-queueOptions.length);
  const result = {};

  queueOptions.forEach((queue, idx) => {
    const row = queueRows[idx];
    if (!row) return;

    // У рядках черг x.1 три службові комірки, у x.2 — дві, тож беремо останні 48.
    const cells = Array.from(row.querySelectorAll("td")).slice(-SLOTS_PER_DAY);
    if (cells.length !== SLOTS_PER_DAY) return;

    result[queue] = cells.map(cellIsOff);
  });

  if (Object.keys(result).length === 0) throw new Error("Жодної черги не розібрано");
  return result;
}

export function readCache() {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.queues ? parsed : null;
  } catch (_) {
    return null;
  }
}

function writeCache(queues) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ date: todayKey(), fetchedAt: Date.now(), queues }));
  } catch (_) {
    /* сховище може бути переповнене або вимкнене */
  }
}

/** Тягне сторінку ЖОЕ, парсить усі черги, зберігає та повертає статуси однієї. */
export async function fetchStatusFromZtoe(queue) {
  const queues = parseAllQueues(await fetchZtoeHtml());
  writeCache(queues);
  return queues[queue] ?? null;
}

/** Останній збережений графік для черги, якщо він ще за сьогодні. */
export function readCachedStatus(queue) {
  const cache = readCache();
  if (!cache || cache.date !== todayKey()) return null;
  return cache.queues?.[queue] ?? null;
}

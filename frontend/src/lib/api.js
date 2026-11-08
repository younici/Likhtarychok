import { fetchStatusFromZtoe, readCachedStatus } from './ztoe.js';

const apiBase =
  import.meta.env.API_BASE_PATH ||
  import.meta.env.VITE_API_BASE ||
  import.meta.env.VITE_API_BASE_PATH ||
  '/api';

const grpcStatusEndpoint = `${apiBase}/grpc/StatusService/GetStatus`;
const textEncoder = new TextEncoder();

// ── Protobuf / gRPC-Web helpers ──────────────────────────────────────────────

function encodeVarint(value) {
  const bytes = [];
  let v = value >>> 0;
  while (v >= 0x80) {
    bytes.push((v & 0x7f) | 0x80);
    v >>>= 7;
  }
  bytes.push(v);
  return Uint8Array.from(bytes);
}

function decodeVarint(bytes, start = 0) {
  let result = 0;
  let shift = 0;
  let pos = start;

  while (pos < bytes.length) {
    const byte = bytes[pos];
    result |= (byte & 0x7f) << shift;
    pos += 1;
    if ((byte & 0x80) === 0) break;
    shift += 7;
  }

  return [result, pos - start];
}

export function encodeStatusRequest(queue = '') {
  const queueBytes = textEncoder.encode(queue);
  const lenBytes = encodeVarint(queueBytes.length);
  const message = new Uint8Array(1 + lenBytes.length + queueBytes.length);
  message[0] = 0x0a; // field 1, wire type 2
  message.set(lenBytes, 1);
  message.set(queueBytes, 1 + lenBytes.length);
  return message;
}

export function wrapGrpcWebMessage(messageBytes) {
  const buffer = new Uint8Array(5 + messageBytes.length);
  const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  buffer[0] = 0x00; // data frame
  view.setUint32(1, messageBytes.length, false);
  buffer.set(messageBytes, 5);
  return buffer;
}

export function unwrapGrpcWebMessage(buffer) {
  const bytes = new Uint8Array(buffer);
  if (bytes.length < 5) throw new Error('Invalid gRPC-web response');

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const isDataFrame = bytes[0] === 0x00 || bytes[0] === 0x01;
  if (!isDataFrame) throw new Error('Unexpected gRPC-web frame');

  const msgLength = view.getUint32(1, false);
  const end = 5 + msgLength;
  if (end > bytes.length) throw new Error('Truncated gRPC-web payload');

  return bytes.slice(5, end);
}

export function decodeStatusResponse(messageBytes) {
  const result = [];
  let pos = 0;

  while (pos < messageBytes.length) {
    const tag = messageBytes[pos];
    pos += 1;
    const field = tag >> 3;
    const wireType = tag & 0x07;

    if (field === 1 && wireType === 2) {
      const [length, lenBytes] = decodeVarint(messageBytes, pos);
      pos += lenBytes;
      const end = pos + length;
      while (pos < end) {
        const [val, read] = decodeVarint(messageBytes, pos);
        result.push(Boolean(val));
        pos += read;
      }
    } else if (wireType === 0) {
      const [, read] = decodeVarint(messageBytes, pos);
      pos += read;
    } else if (wireType === 2) {
      const [length, lenBytes] = decodeVarint(messageBytes, pos);
      pos += lenBytes + length;
    } else {
      break;
    }
  }

  return result;
}

export async function fetchStatusGrpc(queue) {
  const message = encodeStatusRequest(queue ?? '');
  const payload = wrapGrpcWebMessage(message);

  const response = await fetch(grpcStatusEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/grpc-web+proto',
      'X-Grpc-Web': '1',
    },
    body: payload,
  });

  if (!response.ok) throw new Error(`gRPC request failed (${response.status})`);

  const buffer = await response.arrayBuffer();
  const messageBytes = unwrapGrpcWebMessage(buffer);
  return decodeStatusResponse(messageBytes);
}

/*
 * Роутер джерел даних: спершу API-сервер, далі — клієнтський парсинг сайту ЖОЕ,
 * і як остання лінія — збережений сьогоднішній графік з localStorage.
 */
export async function loadQueueStatus(queue) {
  try {
    const data = await fetchStatusGrpc(queue);
    if (data.length > 0) return { data, source: 'api' };
  } catch (_) {
    /* падаємо на наступне джерело */
  }

  try {
    const data = await fetchStatusFromZtoe(queue);
    if (data?.length) return { data, source: 'ztoe' };
  } catch (_) {
    /* падаємо на наступне джерело */
  }

  const cached = readCachedStatus(queue);
  if (cached?.length) return { data: cached, source: 'cache' };

  return { data: [], source: 'none' };
}

// ── Address Search API ───────────────────────────────────────────────────────

/**
 * Пошук черги за адресою (вулиця, будинок).
 * GET /api/addresses/search?q={query}&limit={limit}
 */
export async function searchAddresses(query, limit = 12, signal) {
  if (!query || !query.trim()) {
    return { results: [], total_indexed: 0, updated_at: null };
  }

  try {
    const url = `${apiBase}/addresses/search?q=${encodeURIComponent(query.trim())}&limit=${limit}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    });

    if (!response.ok) {
      return { results: [], total_indexed: 0, updated_at: null };
    }

    const data = await response.json();
    return {
      results: Array.isArray(data?.results) ? data.results : [],
      total_indexed: Number(data?.total_indexed) || 0,
      updated_at: data?.updated_at || null,
    };
  } catch (error) {
    if (error?.name === 'AbortError') {
      return { results: [], total_indexed: 0, updated_at: null, aborted: true };
    }
    return { results: [], total_indexed: 0, updated_at: null };
  }
}

// ── Web Push Notifications API ──────────────────────────────────────────────

/**
 * Отримати публічний VAPID-ключ сервера для браузерних Web Push підписок.
 * GET /api/vapid_public_key
 */
export async function fetchVapidPublicKey() {
  try {
    const response = await fetch(`${apiBase}/vapid_public_key`, {
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) return null;
    const data = await response.json();
    return data?.key ?? null;
  } catch (_) {
    return null;
  }
}

/**
 * Зберегти Web Push підписку для вказаної черги.
 * POST /api/subscribe
 */
export async function subscribeWebPush(queue, subscription) {
  const payload = {
    queue,
    subscription: subscription?.toJSON ? subscription.toJSON() : subscription,
  };

  const response = await fetch(`${apiBase}/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Subscribe failed (${response.status})`);
  }

  return response.json();
}

/**
 * Скасувати Web Push підписку.
 * POST /api/unsubscribe
 */
export async function unsubscribeWebPush(subscription) {
  const payload = {
    subscription: subscription?.toJSON ? subscription.toJSON() : subscription,
  };

  const response = await fetch(`${apiBase}/unsubscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Unsubscribe failed (${response.status})`);
  }

  return response.json();
}

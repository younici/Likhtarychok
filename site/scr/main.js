/**
 * @typedef {Object} StatusResponse
 * @property {number[]} Status
 * @property {number} [Count]
 */

/** @type {HTMLElement} */
const container = document.getElementsByClassName("status-conainer")[0];
const timeContainer = document.getElementsByClassName("time-container")[0];

(async () => {
  const publicKey = (await (await fetch(`/vapid_public_key`)).json()).key;

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
    return outputArray;
  }

  const button = document.getElementById("subscribe");
  if (button) {
    button.onclick = async () => {
      const reg = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;

      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });

      const answer = await fetch(`/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(subscription),
      });

      const result = await answer.json();
      alert(result?.msg || (result?.ok ? "ok" : "err"));
    };
  }

  const result = await fetch(`/status`);
  /** @type {StatusResponse} */
  const json = await result.json();

  const data = Array.isArray(json.Status) ? json.Status : [];
  const len = data.length;

  const perHourPairs = 24;
  let html = ``;
  let labels = ``;

  for (let h = 0; h < 24; h++) {
    let left = 0, right = 0;

    if (len >= 48) {
      left = Number(Boolean(data[h * 2] ?? 0));
      right = Number(Boolean(data[h * 2 + 1] ?? 0));
    } else if (len === 24) {
      const v = Number(Boolean(data[h] ?? 0));
      left = v; right = v;
    } else if (len > 0) {
      left = Number(Boolean(data[Math.min(h * 2, len - 1)] ?? 0));
      right = Number(Boolean(data[Math.min(h * 2 + 1, len - 1)] ?? 0));
    }

    const cellL = `<div class="status ${left === 1 ? "red" : ""}"></div>`;
    const cellR = `<div class="status ${right === 1 ? "red" : ""}"></div>`;
    html += `<div class="status-element">${cellL}${cellR}</div>`;

    const hh = h.toString().padStart(2, "0");
    const next = (h + 1).toString().padStart(2, "0");
    const endHour = h === 23 ? "24" : next;
    labels += `<p class="row-element">${hh}:00–${endHour}:00</p>`;
  }

  timeContainer.innerHTML = labels;
  container.innerHTML = html;
})();

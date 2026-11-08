import { useCallback, useEffect, useRef, useState } from 'react';
import { searchAddresses } from '../../lib/api.js';
import styles from './Graph.module.css';

// Fallback directory of Zhytomyr streets for offline/dev resilience
const ZHYTOMYR_STREETS_CATALOG = [
  { street: 'вул. Київська', city: 'м. Житомир', rem: 'Житомирський', queue: '31', queue_label: '3.1', houses_preview: '1-45, 2-56' },
  { street: 'вул. Велика Бердичівська', city: 'м. Житомир', rem: 'Житомирський', queue: '12', queue_label: '1.2', houses_preview: '2-112, 1-89' },
  { street: 'вул. Перемоги', city: 'м. Житомир', rem: 'Житомирський', queue: '21', queue_label: '2.1', houses_preview: '1-99, 2-104' },
  { street: 'вул. Михайлівська', city: 'м. Житомир', rem: 'Житомирський', queue: '32', queue_label: '3.2', houses_preview: '1-25, 2-24' },
  { street: 'вул. Покровська', city: 'м. Житомир', rem: 'Житомирський', queue: '41', queue_label: '4.1', houses_preview: '1-135, 2-160' },
  { street: 'вул. Чуднівська', city: 'м. Житомир', rem: 'Житомирський', queue: '51', queue_label: '5.1', houses_preview: '1-115, 2-120' },
  { street: 'вул. Домбровського', city: 'м. Житомир', rem: 'Житомирський', queue: '22', queue_label: '2.2', houses_preview: '1-67, 2-84' },
  { street: 'вул. Вітрука', city: 'м. Житомир', rem: 'Житомирський', queue: '61', queue_label: '6.1', houses_preview: '1-55, 2-60' },
  { street: 'вул. Івана Мазепи', city: 'м. Житомир', rem: 'Житомирський', queue: '31', queue_label: '3.1', houses_preview: '1-103, 2-110' },
  { street: 'вул. Шевченка', city: 'м. Житомир', rem: 'Житомирський', queue: '11', queue_label: '1.1', houses_preview: '1-85, 2-90' },
  { street: 'вул. Корольова', city: 'м. Житомир', rem: 'Житомирський', queue: '42', queue_label: '4.2', houses_preview: '1-168, 2-174' },
  { street: 'просп. Миру', city: 'м. Житомир', rem: 'Житомирський', queue: '52', queue_label: '5.2', houses_preview: '1-45, 2-62' },
  { street: 'вул. Лесі Українки', city: 'м. Житомир', rem: 'Житомирський', queue: '62', queue_label: '6.2', houses_preview: '1-79, 2-86' },
  { street: 'вул. Михайла Грушевського', city: 'м. Житомир', rem: 'Житомирський', queue: '21', queue_label: '2.1', houses_preview: '1-105, 2-112' },
  { street: 'вул. Небесної Сотні', city: 'м. Житомир', rem: 'Житомирський', queue: '31', queue_label: '3.1', houses_preview: '1-88, 2-94' },
  { street: 'вул. Селецька', city: 'м. Житомир', rem: 'Житомирський', queue: '12', queue_label: '1.2', houses_preview: '1-50, 2-48' },
  { street: 'вул. Бориса Тена', city: 'м. Житомир', rem: 'Житомирський', queue: '22', queue_label: '2.2', houses_preview: '1-102, 2-98' },
  { street: 'вул. Святослава Ріхтера', city: 'м. Житомир', rem: 'Житомирський', queue: '32', queue_label: '3.2', houses_preview: '1-75, 2-80' },
  { street: 'вул. Театральна', city: 'м. Житомир', rem: 'Житомирський', queue: '11', queue_label: '1.1', houses_preview: '1-30, 2-28' },
  { street: 'вул. Космонавтів', city: 'м. Житомир', rem: 'Житомирський', queue: '61', queue_label: '6.1', houses_preview: '1-64, 2-70' },
  { street: 'вул. Героїв Десантників', city: 'м. Житомир', rem: 'Житомирський', queue: '51', queue_label: '5.1', houses_preview: '1-35, 2-40' },
  { street: 'вул. Вокзальна', city: 'м. Житомир', rem: 'Житомирський', queue: '41', queue_label: '4.1', houses_preview: '1-28, 2-32' },
];

function normalizeQuery(str = '') {
  return str.toLowerCase().replace(/^(вул\.|вулиця|просп\.|проспект|пров\.|провулок)\s*/i, '').trim();
}

function parseQueryParts(query = '') {
  const trimmed = query.trim();
  // Match trailing house number (e.g. "Київська 21", "Миру 14-а", "Перемоги, 5")
  const match = trimmed.match(/^(.*?)[,\s]+(\d+[\wа-яіїєґА-ЯІЇЄҐ/-]*)$/i);
  if (match) {
    return {
      streetQuery: match[1].trim(),
      houseQuery: match[2].trim(),
    };
  }
  return { streetQuery: trimmed, houseQuery: '' };
}

function highlightMatch(text, query) {
  if (!query || !text) return text;
  const cleanQ = query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  if (!cleanQ) return text;

  const parts = text.split(new RegExp(`(${cleanQ})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <strong key={i} className={styles.highlightText}>
        {part}
      </strong>
    ) : (
      part
    )
  );
}

export default function AddressSearch({ onSelectQueue, currentQueue }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [savedAddress, setSavedAddress] = useState(null);
  const [isEditing, setIsEditing] = useState(false);

  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Load saved address from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('savedUserAddress');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && (parsed.street || parsed.queue)) {
          setSavedAddress(parsed);
        }
      }
    } catch (_) {
      /* ignore storage errors */
    }
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Search logic with debounce and API / Fallback
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);

    const timerId = setTimeout(async () => {
      const { streetQuery, houseQuery } = parseQueryParts(trimmed);
      let apiItems = [];

      try {
        const data = await searchAddresses(trimmed, 12, controller.signal);
        if (Array.isArray(data?.results) && data.results.length > 0) {
          apiItems = data.results;
        }
      } catch (_) {
        /* fallback to local directory */
      }

      // If backend returned nothing or empty, search local catalog
      if (apiItems.length === 0) {
        const normStreetQ = normalizeQuery(streetQuery);
        const filtered = ZHYTOMYR_STREETS_CATALOG.filter((item) => {
          const normStreet = normalizeQuery(item.street);
          return normStreet.includes(normStreetQ);
        });

        apiItems = filtered.map((item) => ({
          ...item,
          matched_house: houseQuery || null,
        }));
      } else if (houseQuery) {
        apiItems = apiItems.map((item) => ({
          ...item,
          matched_house: item.matched_house || houseQuery,
        }));
      }

      setResults(apiItems);
      setIsLoading(false);
      setIsOpen(apiItems.length > 0);
      setSelectedIndex(-1);
    }, 220);

    return () => {
      clearTimeout(timerId);
      controller.abort();
    };
  }, [query]);

  const handleSelect = useCallback(
    (item) => {
      if (!item) return;
      const { houseQuery } = parseQueryParts(query);
      const chosen = {
        ...item,
        matched_house: item.matched_house || houseQuery || null,
      };

      try {
        localStorage.setItem('savedUserAddress', JSON.stringify(chosen));
      } catch (_) {
        /* ignore */
      }

      setSavedAddress(chosen);
      setIsEditing(false);
      setIsOpen(false);
      setQuery('');

      if (chosen.queue) {
        onSelectQueue(chosen.queue);
      }
    },
    [query, onSelectQueue]
  );

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const handleResetSavedAddress = () => {
    try {
      localStorage.removeItem('savedUserAddress');
    } catch (_) {
      /* ignore */
    }
    setSavedAddress(null);
    setIsEditing(true);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleKeyDown = (e) => {
    if (!isOpen || results.length === 0) {
      if (e.key === 'ArrowDown' && results.length > 0) {
        setIsOpen(true);
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedIndex >= 0 && selectedIndex < results.length) {
        handleSelect(results[selectedIndex]);
      } else if (results.length > 0) {
        handleSelect(results[0]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div className={styles.addressSearchBox} ref={containerRef}>
      {/* ── Saved Address Card (if configured and not editing) ── */}
      {savedAddress && !isEditing ? (
        <div className={styles.savedAddressCard}>
          <div className={styles.savedAddressMain}>
            <div className={styles.savedAddressIcon}>
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
              </svg>
            </div>
            <div className={styles.savedAddressText}>
              <div className={styles.savedAddressTitle}>
                {savedAddress.street}
                {savedAddress.matched_house && (
                  <span className={styles.savedHouseBadge}>
                    буд. {savedAddress.matched_house}
                  </span>
                )}
              </div>
              <div className={styles.savedAddressMeta}>
                {savedAddress.city || 'м. Житомир'} · {savedAddress.rem || 'Житомирський'} РЕМ
                {savedAddress.houses_preview && ` · ${savedAddress.houses_preview}`}
              </div>
            </div>
            <div className={styles.savedQueueBadge}>
              Черга {savedAddress.queue_label || `${savedAddress.queue?.[0]}.${savedAddress.queue?.[1]}`}
            </div>
          </div>

          <div className={styles.savedAddressActions}>
            <button
              type="button"
              className={styles.savedActionEdit}
              onClick={() => {
                setIsEditing(true);
                setTimeout(() => inputRef.current?.focus(), 50);
              }}
            >
              Змінити адресу
            </button>
            <button
              type="button"
              className={styles.savedActionReset}
              onClick={handleResetSavedAddress}
            >
              Скинути
            </button>
          </div>
        </div>
      ) : null}

      {/* ── Google Maps style input field ── */}
      {(!savedAddress || isEditing) && (
        <div className={styles.searchInputWrapper}>
          <div className={styles.searchBar}>
            <span className={styles.searchIconLeft} aria-hidden="true">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>

            <input
              ref={inputRef}
              type="search"
              className={styles.searchInput}
              placeholder="Введіть вулицю та номер будинку (напр. Київська 21)…"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setIsOpen(true);
              }}
              onFocus={() => {
                if (results.length > 0) setIsOpen(true);
              }}
              onKeyDown={handleKeyDown}
              autoComplete="off"
              spellCheck="false"
              aria-expanded={isOpen}
              aria-autocomplete="list"
              aria-controls="address-results-list"
            />

            {isLoading && (
              <span className={styles.searchSpinner} aria-label="Пошук…">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="12" strokeLinecap="round" />
                </svg>
              </span>
            )}

            {query.length > 0 && !isLoading && (
              <button
                type="button"
                className={styles.searchClearBtn}
                onClick={handleClear}
                aria-label="Очистити поле пошуку"
              >
                ✕
              </button>
            )}

            {savedAddress && isEditing && (
              <button
                type="button"
                className={styles.searchCancelEditBtn}
                onClick={() => setIsEditing(false)}
              >
                Скасувати
              </button>
            )}
          </div>

          {/* ── Dropdown suggestions list ── */}
          {isOpen && results.length > 0 && (
            <ul
              id="address-results-list"
              className={styles.resultsDropdown}
              role="listbox"
            >
              {results.map((item, idx) => {
                const isSelected = selectedIndex === idx;
                const { streetQuery } = parseQueryParts(query);
                const itemQueueLabel = item.queue_label || `${item.queue?.[0]}.${item.queue?.[1]}`;
                const isCurrentActiveQueue = item.queue === currentQueue;

                return (
                  <li
                    key={`${item.street}-${item.queue}-${idx}`}
                    role="option"
                    aria-selected={isSelected}
                    className={`${styles.resultItem} ${isSelected ? styles.resultItemActive : ''} ${
                      isCurrentActiveQueue ? styles.resultItemCurrentQueue : ''
                    }`}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    onClick={() => handleSelect(item)}
                  >
                    <div className={styles.resultItemIcon}>
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
                      </svg>
                    </div>

                    <div className={styles.resultItemBody}>
                      <div className={styles.resultItemStreet}>
                        {highlightMatch(item.street, streetQuery || query)}
                        {item.matched_house && (
                          <span className={styles.matchedHouseChip}>
                            буд. {item.matched_house}
                          </span>
                        )}
                      </div>
                      <div className={styles.resultItemSubtitle}>
                        <span>{item.city || 'м. Житомир'}</span>
                        {item.rem && <span> · {item.rem} РЕМ</span>}
                        {item.houses_preview && (
                          <span className={styles.housesPreviewText}>
                            {' '}
                            · буд.: {item.houses_preview}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className={styles.resultItemBadge}>
                      <span className={styles.queueLabelBadge}>
                        Черга {itemQueueLabel}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {isOpen && !isLoading && query.trim().length >= 2 && results.length === 0 && (
            <div className={styles.noResultsBox}>
              <p>Адресу &ldquo;{query}&rdquo; не знайдено</p>
              <span>Спробуйте ввести тільки назву вулиці без скорочень</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

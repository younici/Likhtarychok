import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchAddressLocations, searchAddresses } from '../../lib/api.js';
import styles from './Graph.module.css';

function extractSearchTokens(query = '') {
  return query
    .trim()
    .replace(/[,;]/g, ' ')
    .split(/\s+/)
    .filter((tok) => tok.length >= 2 && !/^\d/.test(tok));
}

function highlightMatch(text, query) {
  if (!query || !text) return text;
  const tokens = extractSearchTokens(query);
  if (tokens.length === 0) return text;

  const escaped = tokens
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|');
  if (!escaped) return text;

  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);
  const lowerTokens = tokens.map((t) => t.toLowerCase());

  return parts.map((part, i) =>
    lowerTokens.includes(part.toLowerCase()) ? (
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
  const [selectedRem, setSelectedRem] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [locations, setLocations] = useState({
    rems: [],
    cities_by_rem: {},
  });
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
          if (parsed.rem) setSelectedRem(parsed.rem);
          if (parsed.city) setSelectedCity(parsed.city);
        }
      }
    } catch (_) {
      /* ignore storage errors */
    }
  }, []);

  // Load full oblast REMs & settlements hierarchy from backend
  useEffect(() => {
    const controller = new AbortController();
    fetchAddressLocations(controller.signal).then((data) => {
      if (Array.isArray(data?.rems) && data.rems.length > 0) {
        setLocations({
          rems: data.rems,
          cities_by_rem: data.cities_by_rem || {},
        });
      }
    });
    return () => controller.abort();
  }, []);

  const availableCities = useMemo(() => {
    if (!selectedRem) return [];
    return locations.cities_by_rem?.[selectedRem] || [];
  }, [selectedRem, locations.cities_by_rem]);

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

  // Search logic with debounce across the entire Zhytomyr Oblast
  useEffect(() => {
    const trimmed = query.trim();
    const hasLocationFilter = Boolean(selectedCity);

    // Require at least 2 characters unless a specific settlement (city) is selected
    if (trimmed.length < 2 && !hasLocationFilter) {
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
      const limit = hasLocationFilter && !trimmed ? 25 : 16;
      const data = await searchAddresses(
        trimmed,
        limit,
        controller.signal,
        selectedRem,
        selectedCity
      );

      if (data?.aborted) return;

      const apiItems = Array.isArray(data?.results) ? data.results : [];
      setResults(apiItems);
      setIsLoading(false);
      setIsOpen(apiItems.length > 0 || trimmed.length >= 2);
      setSelectedIndex(-1);
    }, 180);

    return () => {
      clearTimeout(timerId);
      controller.abort();
    };
  }, [query, selectedRem, selectedCity]);

  const handleSelect = useCallback(
    (item) => {
      if (!item) return;
      const chosen = {
        ...item,
        matched_house: item.matched_house || null,
      };

      try {
        localStorage.setItem('savedUserAddress', JSON.stringify(chosen));
      } catch (_) {
        /* ignore */
      }

      setSavedAddress(chosen);
      if (chosen.rem) setSelectedRem(chosen.rem);
      if (chosen.city) setSelectedCity(chosen.city);
      setIsEditing(false);
      setIsOpen(false);
      setQuery('');

      if (chosen.queue) {
        onSelectQueue(chosen.queue);
      }
    },
    [onSelectQueue]
  );

  const handleClear = () => {
    setQuery('');
    if (!selectedCity) {
      setResults([]);
      setIsOpen(false);
    }
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

  const handleRemChange = (e) => {
    const newRem = e.target.value;
    setSelectedRem(newRem);
    setSelectedCity('');
    setResults([]);
  };

  const handleCityChange = (e) => {
    const newCity = e.target.value;
    setSelectedCity(newCity);
    if (newCity) {
      setIsOpen(true);
    }
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
      } else if (results.length === 1) {
        handleSelect(results[0]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const hasMultiQueueWithoutHouse = useMemo(
    () =>
      results.some(
        (item) =>
          Number(item.total_queues_for_street) > 1 && !item.matched_house
      ),
    [results]
  );

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
                {savedAddress.houses_preview && ` · буд.: ${savedAddress.houses_preview}`}
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

      {/* ── Oblast Filters + Smart Search Input ── */}
      {(!savedAddress || isEditing) && (
        <div className={styles.searchInputWrapper}>
          {/* Optional REM & Settlement Filter Bar for all of Zhytomyr Oblast */}
          <div className={styles.locationFiltersRow}>
            <div className={styles.locationSelectWrap}>
              <select
                className={styles.locationSelect}
                value={selectedRem}
                onChange={handleRemChange}
                aria-label="Оберіть РЕМ (район Житомирської області)"
              >
                <option value="">Уся Житомирська область (усі РЕМ)</option>
                {locations.rems.map((remName) => (
                  <option key={remName} value={remName}>
                    {remName} РЕМ
                  </option>
                ))}
              </select>
            </div>

            {selectedRem && (
              <div className={styles.locationSelectWrap}>
                <select
                  className={styles.locationSelect}
                  value={selectedCity}
                  onChange={handleCityChange}
                  aria-label="Оберіть населений пункт"
                >
                  <option value="">
                    Усі населені пункти ({availableCities.length})
                  </option>
                  {availableCities.map((cityName) => (
                    <option key={cityName} value={cityName}>
                      {cityName}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className={styles.searchBar}>
            <span className={styles.searchIconLeft} aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>

            <input
              ref={inputRef}
              type="search"
              className={styles.searchInput}
              placeholder={
                selectedCity
                  ? `Введіть вулицю та будинок (${selectedCity})…`
                  : 'Місто/село, вулиця та будинок (напр. Київська 21, Бердичів Житомирська 131)…'
              }
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
                <svg
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    strokeDasharray="32"
                    strokeDashoffset="12"
                    strokeLinecap="round"
                  />
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
              {hasMultiQueueWithoutHouse && (
                <li className={styles.multiQueueHint} role="presentation">
                  Додайте номер будинку через пробіл (напр.{' '}
                  <strong>{results[0]?.street?.replace(/^вул\.\s*/i, '') || 'Київська'} 21</strong>
                  ), щоб система відфільтрувала точну чергу вашого будинку
                </li>
              )}

              {results.map((item, idx) => {
                const isSelected = selectedIndex === idx;
                const itemQueueLabel =
                  item.queue_label || `${item.queue?.[0]}.${item.queue?.[1]}`;
                const isCurrentActiveQueue = item.queue === currentQueue;

                return (
                  <li
                    key={`${item.rem}-${item.city}-${item.street}-${item.queue}-${idx}`}
                    role="option"
                    aria-selected={isSelected}
                    className={`${styles.resultItem} ${
                      isSelected ? styles.resultItemActive : ''
                    } ${isCurrentActiveQueue ? styles.resultItemCurrentQueue : ''}`}
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
                        <span>{highlightMatch(item.street, query)}</span>
                        {item.matched_house && (
                          <span className={styles.matchedHouseChip}>
                            буд. {item.matched_house}
                          </span>
                        )}
                      </div>
                      <div className={styles.resultItemSubtitle}>
                        <span className={styles.resultCityText}>
                          {highlightMatch(item.city || 'м. Житомир', query)}
                        </span>
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

          {isOpen &&
            !isLoading &&
            (query.trim().length >= 2 || selectedCity) &&
            results.length === 0 && (
              <div className={styles.noResultsBox}>
                <p>Адресу &ldquo;{query || selectedCity}&rdquo; не знайдено</p>
                <span>
                  Спробуйте обрати свій РЕМ та населений пункт вище або введіть назву
                  вулиці без скорочень
                </span>
              </div>
            )}
        </div>
      )}
    </div>
  );
}

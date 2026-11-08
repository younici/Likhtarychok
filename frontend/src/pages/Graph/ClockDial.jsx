import { useEffect, useMemo, useState } from 'react';
import styles from './Graph.module.css';

const CX = 180;
const CY = 180;
const R_INNER = 88;
const R_OUTER_ON = 132;
const R_OUTER_OFF = 138;
const R_HOVER_EXTRA = 6;

function polarToCartesian(cx, cy, radius, angleInDegrees) {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
  return {
    x: cx + radius * Math.cos(angleInRadians),
    y: cy + radius * Math.sin(angleInRadians),
  };
}

function describeAnnularSector(cx, cy, rInner, rOuter, startAngle, endAngle) {
  const startOuter = polarToCartesian(cx, cy, rOuter, endAngle);
  const endOuter = polarToCartesian(cx, cy, rOuter, startAngle);
  const startInner = polarToCartesian(cx, cy, rInner, endAngle);
  const endInner = polarToCartesian(cx, cy, rInner, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';

  return [
    'M', startOuter.x.toFixed(2), startOuter.y.toFixed(2),
    'A', rOuter, rOuter, 0, largeArcFlag, 0, endOuter.x.toFixed(2), endOuter.y.toFixed(2),
    'L', endInner.x.toFixed(2), endInner.y.toFixed(2),
    'A', rInner, rInner, 0, largeArcFlag, 1, startInner.x.toFixed(2), startInner.y.toFixed(2),
    'Z',
  ].join(' ');
}

function formatHalfHour(index) {
  if (index >= 48) return '24:00';
  const hours = Math.floor(index / 2);
  const minutes = index % 2 === 0 ? '00' : '30';
  return `${String(hours).padStart(2, '0')}:${minutes}`;
}

export default function ClockDial({ statuses = [], currentMinutes = 0, queueLabel = '' }) {
  const [now, setNow] = useState(() => new Date());
  const [activeSlot, setActiveSlot] = useState(null);

  // Update real-time seconds every 1000ms
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const totalSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
  const handAngleDeg = (totalSeconds / 86400) * 360;

  const currentSlotIndex = Math.floor(totalSeconds / 1800); // 0..47
  const currentSlotSafe = Math.min(Math.max(0, currentSlotIndex), 47);
  const isCurrentOff = Boolean(statuses[currentSlotSafe]);

  // Digital clock string
  const timeString = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

  // Countdown to next state change
  const countdownInfo = useMemo(() => {
    if (!statuses || statuses.length === 0) {
      return { text: 'Дані завантажуються…', targetStatus: null };
    }

    const currentStatus = Boolean(statuses[currentSlotSafe]);
    let changeSlot = null;

    for (let i = currentSlotSafe + 1; i < 48; i += 1) {
      if (Boolean(statuses[i]) !== currentStatus) {
        changeSlot = i;
        break;
      }
    }

    if (changeSlot === null) {
      // No change until midnight
      const minutesToMidnight = 1440 - (now.getHours() * 60 + now.getMinutes());
      const h = Math.floor(minutesToMidnight / 60);
      const m = minutesToMidnight % 60;
      if (currentStatus) {
        return {
          label: 'До кінця доби без світла',
          time: `${h}г ${m}хв`,
          targetStatus: false,
        };
      }
      return {
        label: 'Світло весь день',
        time: 'без відключень',
        targetStatus: null,
      };
    }

    const targetMinutes = changeSlot * 30;
    const diffMinutes = Math.max(0, targetMinutes - (now.getHours() * 60 + now.getMinutes()));
    const h = Math.floor(diffMinutes / 60);
    const m = diffMinutes % 60;

    const timeFormatted = h > 0 ? `${h}г ${m > 0 ? `${m}хв` : ''}` : `${m}хв`;

    if (currentStatus) {
      return {
        label: 'До включення',
        time: timeFormatted,
        targetStatus: true,
      };
    }
    return {
      label: 'До відключення',
      time: timeFormatted,
      targetStatus: false,
    };
  }, [statuses, currentSlotSafe, now]);

  // Coordinates for clock hand
  const tip = polarToCartesian(CX, CY, 142, handAngleDeg);
  const base = polarToCartesian(CX, CY, 76, handAngleDeg);

  // Hour labels around the dial (00..23)
  const hourTicks = useMemo(() => {
    const ticks = [];
    for (let h = 0; h < 24; h += 1) {
      const angle = h * 15;
      const isMajor = h % 3 === 0;
      const rInnerTick = isMajor ? 144 : 146;
      const rOuterTick = isMajor ? 152 : 149;
      const p1 = polarToCartesian(CX, CY, rInnerTick, angle);
      const p2 = polarToCartesian(CX, CY, rOuterTick, angle);
      const labelPos = polarToCartesian(CX, CY, 164, angle);

      ticks.push({
        h,
        angle,
        isMajor,
        p1,
        p2,
        labelPos,
        text: String(h).padStart(2, '0'),
      });
    }
    return ticks;
  }, []);

  // Displayed selected or hovered slot
  const inspectedSlot = activeSlot !== null ? activeSlot : currentSlotSafe;
  const isInspectedCurrent = inspectedSlot === currentSlotSafe;
  const inspectedIsOff = Boolean(statuses[inspectedSlot]);
  const inspectedRange = `${formatHalfHour(inspectedSlot)} – ${formatHalfHour(inspectedSlot + 1)}`;

  return (
    <div className={styles.dialContainer}>
      <div className={styles.dialSvgWrapper}>
        <svg
          className={styles.dialSvg}
          viewBox="0 0 360 360"
          role="img"
          aria-label={`Круговий циферблат графіка відключень черги ${queueLabel}`}
        >
          <defs>
            {/* Outage Amber-Coral gradient */}
            <linearGradient id="dial-outage-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ffc94a" />
              <stop offset="100%" stopColor="#ff7a5a" />
            </linearGradient>

            {/* Hand cyan gradient */}
            <linearGradient id="dial-hand-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#5ff5cb" />
              <stop offset="100%" stopColor="#ffffff" />
            </linearGradient>

            {/* Dial Outer Glow */}
            <filter id="dial-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Subtle shadow for sectors */}
            <filter id="dial-shadow" x="-10%" y="-10%" width="120%" height="120%">
              <feDropShadow dx="0" dy="1" stdDeviation="2" floodColor="#000000" floodOpacity="0.4" />
            </filter>
          </defs>

          {/* Background dial rim */}
          <circle
            cx={CX}
            cy={CY}
            r="153"
            fill="none"
            stroke="rgba(255, 255, 255, 0.05)"
            strokeWidth="1"
          />
          <circle
            cx={CX}
            cy={CY}
            r="87"
            fill="none"
            stroke="rgba(255, 255, 255, 0.06)"
            strokeWidth="1"
          />

          {/* 48 Half-hour annular sectors */}
          <g className={styles.dialSectors}>
            {statuses.map((isOff, idx) => {
              const startAngle = idx * 7.5;
              const endAngle = (idx + 1) * 7.5;
              // Clean gap between sectors
              const s = startAngle + 0.35;
              const e = endAngle - 0.35;

              const isHovered = activeSlot === idx;
              const isPast = idx < currentSlotSafe;
              const isCurrent = idx === currentSlotSafe;

              let rOuter = isOff ? R_OUTER_OFF : R_OUTER_ON;
              if (isHovered) rOuter += R_HOVER_EXTRA;

              const pathD = describeAnnularSector(CX, CY, R_INNER, rOuter, s, e);

              return (
                <path
                  key={idx}
                  d={pathD}
                  className={`${styles.dialSector} ${isOff ? styles.dialSectorOff : styles.dialSectorOn} ${isHovered ? styles.dialSectorHovered : ''} ${isCurrent ? styles.dialSectorCurrent : ''}`}
                  fill={isOff ? 'url(#dial-outage-grad)' : 'rgba(95, 245, 203, 0.14)'}
                  stroke={isOff ? 'rgba(255, 201, 74, 0.35)' : 'rgba(95, 245, 203, 0.28)'}
                  strokeWidth={isHovered ? 1.5 : 0.8}
                  opacity={isPast ? (isOff ? 0.45 : 0.08) : (isOff ? 0.94 : 0.22)}
                  filter={isOff && !isPast ? 'url(#dial-shadow)' : undefined}
                  tabIndex={0}
                  role="button"
                  aria-label={`${formatHalfHour(idx)}–${formatHalfHour(idx + 1)}: ${isOff ? 'Відключення' : 'Є світло'}`}
                  onMouseEnter={() => setActiveSlot(idx)}
                  onMouseLeave={() => setActiveSlot(null)}
                  onClick={() => setActiveSlot(activeSlot === idx ? null : idx)}
                  onKeyDown={(evt) => {
                    if (evt.key === 'Enter' || evt.key === ' ') {
                      evt.preventDefault();
                      setActiveSlot(activeSlot === idx ? null : idx);
                    }
                  }}
                />
              );
            })}
          </g>

          {/* Hour tick marks */}
          <g className={styles.dialTicks}>
            {hourTicks.map(({ h, p1, p2, isMajor }) => (
              <line
                key={h}
                x1={p1.x.toFixed(2)}
                y1={p1.y.toFixed(2)}
                x2={p2.x.toFixed(2)}
                y2={p2.y.toFixed(2)}
                stroke={isMajor ? 'rgba(255, 255, 255, 0.75)' : 'rgba(255, 255, 255, 0.2)'}
                strokeWidth={isMajor ? 2 : 1}
                strokeLinecap="round"
              />
            ))}
          </g>

          {/* Hour labels (00..23) */}
          <g className={styles.dialLabels}>
            {hourTicks.map(({ h, labelPos, text, isMajor }) => (
              <text
                key={h}
                x={labelPos.x.toFixed(2)}
                y={labelPos.y.toFixed(2)}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={isMajor ? '11.5' : '9'}
                fontWeight={isMajor ? '700' : '500'}
                fill={isMajor ? '#ffffff' : 'rgba(136, 153, 187, 0.65)'}
                fontFamily="var(--font)"
                className={isMajor ? styles.majorLabel : styles.minorLabel}
              >
                {text}
              </text>
            ))}
          </g>

          {/* Center dark glass circle */}
          <circle
            cx={CX}
            cy={CY}
            r="80"
            fill="rgba(9, 13, 22, 0.95)"
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth="1.5"
            className={styles.centerCircle}
          />
          <circle
            cx={CX}
            cy={CY}
            r="78"
            fill="none"
            stroke="rgba(95, 245, 203, 0.08)"
            strokeWidth="1"
          />

          {/* Clock Hand / Real-time Needle */}
          <g className={styles.clockHandGroup}>
            {/* Dashed faint center guide */}
            <line
              x1={CX}
              y1={CY}
              x2={base.x.toFixed(2)}
              y2={base.y.toFixed(2)}
              stroke="rgba(95, 245, 203, 0.25)"
              strokeWidth="1"
              strokeDasharray="2 3"
            />
            {/* Luminous main needle */}
            <line
              x1={base.x.toFixed(2)}
              y1={base.y.toFixed(2)}
              x2={tip.x.toFixed(2)}
              y2={tip.y.toFixed(2)}
              stroke="url(#dial-hand-grad)"
              strokeWidth="3.2"
              strokeLinecap="round"
              filter="url(#dial-glow)"
            />
            {/* Glow needle tip */}
            <circle
              cx={tip.x.toFixed(2)}
              cy={tip.y.toFixed(2)}
              r="4.5"
              fill="var(--cyan)"
              stroke="#07090f"
              strokeWidth="2"
              filter="url(#dial-glow)"
            />
          </g>
        </svg>

        {/* Central Overlay Box (Absolute Centered HTML for crisp typography) */}
        <div className={styles.centerOverlay}>
          <div className={styles.centerTime} title="Поточний точний час">
            {timeString}
          </div>

          <div
            className={`${styles.centerStatusBadge} ${
              isCurrentOff ? styles.centerStatusOff : styles.centerStatusOn
            }`}
          >
            <span className={styles.centerStatusDot} />
            <span className={styles.centerStatusText}>
              {isCurrentOff ? 'Без світла' : 'Є світло'}
            </span>
          </div>

          {countdownInfo && (
            <div className={styles.centerCountdown}>
              <span className={styles.centerCountdownLabel}>{countdownInfo.label}</span>
              <span className={styles.centerCountdownVal}>{countdownInfo.time}</span>
            </div>
          )}
        </div>
      </div>

      {/* Interactive bottom inspection bar */}
      <div className={styles.dialInspector}>
        <div className={styles.dialInspectorLeft}>
          <span className={styles.dialInspectorTag}>
            {isInspectedCurrent ? 'Зараз' : 'Обраний слот'}:
          </span>
          <span className={styles.dialInspectorTime}>{inspectedRange}</span>
        </div>
        <div className={styles.dialInspectorRight}>
          <span
            className={`${styles.dialInspectorBadge} ${
              inspectedIsOff ? styles.dialInspectorBadgeOff : styles.dialInspectorBadgeOn
            }`}
          >
            {inspectedIsOff ? 'Відключення за графіком' : 'Світло є'}
          </span>
          {activeSlot !== null && (
            <button
              type="button"
              className={styles.dialResetBtn}
              onClick={() => setActiveSlot(null)}
              title="Повернутися до поточного часу"
            >
              Скинути
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

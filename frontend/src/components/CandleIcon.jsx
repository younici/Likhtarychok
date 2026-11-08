import { useId } from "react";

export default function CandleIcon({ size = 26, className }) {
  const id = useId();
  const bodyGradId = `${id}-body`;
  const headGradId = `${id}-head`;
  const beamGradId = `${id}-beam`;

  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={bodyGradId} x1="6" y1="26" x2="20" y2="12" gradientUnits="userSpaceOnUse">
          <stop stopColor="#ff9d42" />
          <stop offset="1" stopColor="#ffd166" />
        </linearGradient>
        <linearGradient id={headGradId} x1="14" y1="18" x2="23" y2="9" gradientUnits="userSpaceOnUse">
          <stop stopColor="#ffe28a" />
          <stop offset="1" stopColor="#ffae42" />
        </linearGradient>
        <linearGradient id={beamGradId} x1="19" y1="13" x2="30" y2="2" gradientUnits="userSpaceOnUse">
          <stop stopColor="#fff5cc" stopOpacity="0.95" />
          <stop offset="0.55" stopColor="#ffc94a" stopOpacity="0.45" />
          <stop offset="1" stopColor="#ffc94a" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Warm light beam cone */}
      <path
        d="M18.5 9.2L27.5 2.2C29.2 3.4 30.1 4.8 29.8 6.5L22.8 13.5L18.5 9.2Z"
        fill={`url(#${beamGradId})`}
      />

      {/* Flashlight angled group (-45 deg around center) */}
      <g transform="rotate(-45 16 16)">
        {/* Tail cap */}
        <rect x="4" y="13" width="3" height="6" rx="1.5" fill="#d97724" />

        {/* Main handle body */}
        <rect x="6.5" y="12.5" width="9.5" height="7" rx="1.8" fill={`url(#${bodyGradId})`} />

        {/* Grip ribs */}
        <line x1="9" y1="13.8" x2="9" y2="18.2" stroke="#7a3e08" strokeOpacity="0.35" strokeWidth="1" strokeLinecap="round" />
        <line x1="11" y1="13.8" x2="11" y2="18.2" stroke="#7a3e08" strokeOpacity="0.35" strokeWidth="1" strokeLinecap="round" />

        {/* Power button indicator */}
        <circle cx="13.8" cy="16" r="1.2" fill="#07090f" fillOpacity="0.45" />
        <circle cx="13.8" cy="16" r="0.75" fill="#5ff5cb" />

        {/* Flared reflector head */}
        <path
          d="M15.5 12.5L19.8 10.6C20.5 10.3 21.2 10.8 21.2 11.5V20.5C21.2 21.2 20.5 21.7 19.8 21.4L15.5 19.5V12.5Z"
          fill={`url(#${headGradId})`}
        />

        {/* Glowing front lens */}
        <rect x="20.6" y="10.8" width="2" height="10.4" rx="1" fill="#fff7d6" />
      </g>
    </svg>
  );
}


import { useId } from "react";

function CandleIcon({ size = 26, className }) {
  const id = useId();
  const flameId = `${id}-flame`;

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
        <linearGradient id={id} x1="6" y1="4" x2="26" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="#ffca6b" />
          <stop offset="1" stopColor="#ff9d42" />
        </linearGradient>
        <linearGradient id={flameId} x1="16" y1="2" x2="16" y2="13" gradientUnits="userSpaceOnUse">
          <stop stopColor="#fff3c4" />
          <stop offset="1" stopColor="#ff9d42" />
        </linearGradient>
      </defs>
      <path d="M16 2.5c3 3.2 4 5.4 4 7.3a4 4 0 0 1-8 0c0-1.9 1-4.1 4-7.3Z" fill={`url(#${flameId})`} />
      <path d="M16 14v2.5" stroke="#fff3c4" strokeWidth="1.6" strokeLinecap="round" />
      <rect x="11" y="16" width="10" height="13" rx="2" fill={`url(#${id})`} />
      <rect x="9" y="28" width="14" height="2" rx="1" fill={`url(#${id})`} />
    </svg>
  );
}

export default CandleIcon;

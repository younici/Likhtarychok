import { useId } from "react";

function FlashlightIcon({ size = 26, className }) {
  const id = useId();

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
      </defs>
      <g stroke="#6cf0c2" strokeWidth="1.6" strokeLinecap="round" opacity="0.9">
        <path d="M16 1.5v2.2" />
        <path d="M8.2 4.2l1.5 1.6" />
        <path d="M23.8 4.2l-1.5 1.6" />
      </g>
      <path d="M9 8h14l-2.5 5h-9L9 8Z" fill={`url(#${id})`} />
      <rect x="11" y="13" width="10" height="15" rx="2.5" fill={`url(#${id})`} />
      <rect x="14.5" y="17" width="3" height="5" rx="1.5" fill="#292014" opacity="0.7" />
    </svg>
  );
}

export default FlashlightIcon;

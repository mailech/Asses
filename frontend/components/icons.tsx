/**
 * Inline icons, drawn on a 16px grid at 1.4 stroke so they sit at the same
 * visual weight as the surrounding text. Four of them is not worth a dependency.
 */

const base = {
  width: 16,
  height: 16,
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.4,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function BillsIcon() {
  return (
    <svg {...base}>
      <path d="M3.5 1.8h9v12.4l-1.8-1.2-1.8 1.2-1.9-1.2-1.8 1.2-1.7-1.2z" />
      <path d="M6 5.2h4M6 8h4" />
    </svg>
  );
}

export function PrintIcon() {
  return (
    <svg {...base}>
      <path d="M4.5 6V1.8h7V6" />
      <path d="M4.5 12H2.6V6.6h10.8V12H11.5" />
      <path d="M4.5 9.4h7v4.8h-7z" />
    </svg>
  );
}

export function LinkIcon() {
  return (
    <svg {...base}>
      <path d="M6.6 9.4a2.6 2.6 0 0 0 3.9.3l2-2a2.6 2.6 0 0 0-3.7-3.7l-1.1 1.1" />
      <path d="M9.4 6.6a2.6 2.6 0 0 0-3.9-.3l-2 2a2.6 2.6 0 0 0 3.7 3.7l1.1-1.1" />
    </svg>
  );
}

export function BackIcon() {
  return (
    <svg {...base}>
      <path d="M9.6 3.6 5.2 8l4.4 4.4" />
    </svg>
  );
}

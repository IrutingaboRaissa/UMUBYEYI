// Brand mark: a plain "U" (for Umubyeyi), set in the same serif used for headings.
export default function Mark({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden focusable="false">
      <text
        x="12" y="17.5" textAnchor="middle"
        fontFamily="'Fraunces', Georgia, serif" fontWeight={600} fontSize="16.5"
        fill="currentColor"
      >
        U
      </text>
    </svg>
  );
}

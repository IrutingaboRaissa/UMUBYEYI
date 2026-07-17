// Brand mark: a small sprout (new growth) in place of a generic lettered avatar circle.
export default function Mark({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable="false">
      <path d="M12 20V10" />
      <path d="M12 10C8 10 6 7 6 4c3 0 6 2 6 6Z" />
      <path d="M12 10c4 0 6-3 6-6-3 0-6 2-6 6Z" />
    </svg>
  );
}

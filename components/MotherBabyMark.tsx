// Decorative hero illustration: a mother with her baby at her shoulder, reduced to simple
// soft shapes in the same purple tones as the logo circle. Desktop-only accent (hidden on
// mobile via CSS in globals.css, not by JS).
export default function MotherBabyMark() {
  return (
    <svg viewBox="0 0 220 220" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden focusable="false">
      <defs>
        <radialGradient id="motherBabyGradient" cx="34%" cy="22%" r="80%">
          <stop offset="0%" stopColor="#9A7C9D" />
          <stop offset="100%" stopColor="#5E4A5E" />
        </radialGradient>
      </defs>
      {/* mother: head + shoulders (bust crop, not a full seated body) */}
      <circle cx="100" cy="70" r="46" fill="url(#motherBabyGradient)" />
      <path d="M30,220 C30,150 58,116 100,116 C142,116 170,150 170,220 Z" fill="url(#motherBabyGradient)" />
      {/* baby: own head + body, tucked at the mother's shoulder, offset and overlapping in front */}
      <circle cx="150" cy="140" r="24" fill="#F6EFE5" />
      <path d="M126,196 C126,172 137,160 150,160 C163,160 174,174 172,196 Z" fill="#F6EFE5" />
    </svg>
  );
}

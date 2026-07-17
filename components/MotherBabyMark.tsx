// Decorative hero illustration: a mother with her baby at her shoulder. Hair, a
// draped-shoulder silhouette, and baby-proportioned head+tuft are drawn in so the
// shapes read as "mother and baby" at a glance, not an abstract silhouette.
// Desktop-only accent (hidden on mobile via CSS in globals.css, not by JS).
export default function MotherBabyMark() {
  return (
    <svg viewBox="0 0 220 240" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden focusable="false">
      <defs>
        <radialGradient id="motherBabyGradient" cx="34%" cy="22%" r="80%">
          <stop offset="0%" stopColor="#9A7C9D" />
          <stop offset="100%" stopColor="#5E4A5E" />
        </radialGradient>
        <linearGradient id="motherHairGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#4A3A4C" />
          <stop offset="100%" stopColor="#3B2E3D" />
        </linearGradient>
      </defs>

      {/* hair: a fuller shape behind the head/shoulders, parted at the crown, so the
          head reads as a woman's rather than a plain circle */}
      <path
        d="M100,26 C132,26 152,52 150,86 C149,104 143,118 133,128
           L133,100 C133,78 119,64 100,64 C81,64 67,78 67,100 L67,128
           C57,118 51,104 50,86 C48,52 68,26 100,26 Z"
        fill="url(#motherHairGradient)"
      />

      {/* mother: face + shoulders/body (bust crop) */}
      <circle cx="100" cy="76" r="38" fill="url(#motherBabyGradient)" />
      <path
        d="M38,236 C38,172 62,132 100,132 C138,132 162,172 162,236 Z"
        fill="url(#motherBabyGradient)"
      />
      {/* collar/shoulder-drape line, so the body silhouette reads as clothing, not a blob */}
      <path
        d="M66,140 C80,152 120,152 134,140"
        stroke="#F6EFE5" strokeOpacity="0.35" strokeWidth="3" strokeLinecap="round" fill="none"
      />

      {/* baby: bigger head-to-body ratio (as in infants), tucked at the mother's
          shoulder, offset and overlapping in front, with a small hair tuft */}
      <path d="M148,120 C148,120 155,112 163,115 C160,108 152,106 148,112 Z" fill="#F6EFE5" />
      <circle cx="152" cy="138" r="22" fill="#F6EFE5" />
      <path d="M130,196 C130,174 140,162 152,162 C164,162 174,176 172,196 Z" fill="#F6EFE5" />
    </svg>
  );
}

// Brand mark: a tightly-cropped square version of the project's logo (see
// MotherBabyMark.tsx), sized for small avatar use in the topbar and chat bubbles.
// The "?v=" query bumps the URL so browsers can't keep serving an old cached
// copy from before an asset update -- bump it again if the PNG is replaced.
export default function Mark({ size = 20 }: { size?: number }) {
  // eslint-disable-next-line @next/next/no-img-element
  return <img src="/logo-icon.png?v=2" alt="" aria-hidden width={size} height={size} />;
}

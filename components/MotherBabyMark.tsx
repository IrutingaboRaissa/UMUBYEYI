// Brand mark: the project's logo (mother curled protectively around her baby),
// shown at every viewport size, scaled smaller on mobile via CSS in globals.css.
// The "?v=" query bumps the URL so browsers can't keep serving an old cached
// copy from before an asset update -- bump it again if the PNG is replaced.
export default function MotherBabyMark() {
  // eslint-disable-next-line @next/next/no-img-element
  return <img src="/logo.png?v=2" alt="" aria-hidden />;
}

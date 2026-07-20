export function BrandMark({ size = 28 }) {
  return <svg className="brand-mark" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
    <rect x="10" y="7" width="44" height="50" rx="10" fill="currentColor" fillOpacity="0.08" stroke="currentColor" strokeWidth="4" />
    <path d="M21 22h12M21 31h9" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
    <circle cx="42" cy="38" r="10" fill="var(--verified)" />
    <path d="m37.5 38 3 3 5.5-6" fill="none" stroke="var(--canvas)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>;
}

export function Brand() {
  return <span className="logo"><BrandMark /><span>Skill Passport</span></span>;
}

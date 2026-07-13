export function AmbientBackground() {
  return (
    <div className="ambient-bg pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <div className="ambient-base" />
      <div className="ambient-orb ambient-orb-1" />
      <div className="ambient-orb ambient-orb-2" />
      <div className="ambient-orb ambient-orb-3" />
      <div className="ambient-orb ambient-orb-4" />
      <div className="ambient-orb ambient-orb-5" />
      <div className="ambient-grid" />
      <div className="ambient-noise" />
    </div>
  );
}

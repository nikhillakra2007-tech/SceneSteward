/**
 * Infinite principles ticker. CSS-driven, duplicated rows for a seamless
 * loop; the second row is hidden from assistive tech. Reduced-motion
 * freezes it (the global guard kills the animation and the track sits
 * still, fully readable).
 */
export default function Marquee({ items }: { items: string[] }) {
  const Row = ({ hidden }: { hidden?: boolean }) => (
    <div className="marquee-row" aria-hidden={hidden || undefined}>
      {items.map((t, i) => (
        <span className="marquee-item" key={i}>
          <i className="marquee-diamond" aria-hidden="true" />
          {t}
        </span>
      ))}
    </div>
  );
  return (
    <div className="marquee" aria-label="SceneSteward principles">
      <div className="marquee-track">
        <Row />
        <Row hidden />
      </div>
    </div>
  );
}

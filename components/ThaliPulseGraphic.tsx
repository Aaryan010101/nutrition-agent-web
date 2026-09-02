"use client";

import { UtensilsCrossed } from "lucide-react";

const SIZE = 360;
const CENTER = SIZE / 2;
const RING_RADIUS = 118;
const RING_STROKE = 32;
const CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

// Macro split shown on the plate ring -- this is real content the
// agent's plans are built around, not decoration.
const WEDGES = [
  { label: "Carbs", pct: 0.45, color: "#E8A33D" }, // turmeric
  { label: "Protein", pct: 0.3, color: "#C1502E" }, // ember
  { label: "Fat", pct: 0.25, color: "#3E6B49" }, // saag rim
];

function pointOnCircle(radius: number, angleDeg: number) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: CENTER + radius * Math.cos(angleRad),
    y: CENTER + radius * Math.sin(angleRad),
  };
}

export default function ThaliPulseGraphic() {
  let cumulative = 0;
  const wedgeData = WEDGES.map((w) => {
    const startAngle = cumulative * 360;
    cumulative += w.pct;
    const endAngle = cumulative * 360;
    const midAngle = (startAngle + endAngle) / 2;
    const labelPoint = pointOnCircle(RING_RADIUS + 34, midAngle);
    return { ...w, startFrac: startAngle / 360, labelPoint };
  });

  const ticks = Array.from({ length: 32 }, (_, i) => i * (360 / 32));

  // A simple hand-drawn-feeling ECG trace, normalized with pathLength
  // so the draw-in animation always works regardless of exact geometry.
  const pulsePath =
    "M40,180 L96,180 L112,150 L128,214 L144,120 L160,180 L184,180 L200,158 L216,180 L320,180";

  return (
    <div className="relative mx-auto w-[280px] h-[280px] sm:w-[340px] sm:h-[340px]">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="w-full h-full"
        role="img"
        aria-label="Circular plate showing a 45/30/25 carb, protein and fat split with a pulse line crossing it"
      >
        {/* outer bezel */}
        <circle
          cx={CENTER}
          cy={CENTER}
          r={RING_RADIUS + RING_STROKE / 2 + 14}
          fill="none"
          stroke="#8B8677"
          strokeOpacity={0.35}
          strokeWidth={1}
        />

        {/* rim ticks like a fitness-tracker bezel */}
        {ticks.map((deg, i) => {
          const strong = i % 4 === 0;
          const inner = pointOnCircle(RING_RADIUS + RING_STROKE / 2 + 8, deg);
          const outer = pointOnCircle(
            RING_RADIUS + RING_STROKE / 2 + (strong ? 20 : 14),
            deg
          );
          return (
            <line
              key={deg}
              x1={inner.x}
              y1={inner.y}
              x2={outer.x}
              y2={outer.y}
              stroke={strong ? "#E8A33D" : "#8B8677"}
              strokeOpacity={strong ? 0.9 : 0.45}
              strokeWidth={strong ? 2.5 : 1.5}
              strokeLinecap="round"
            />
          );
        })}

        {/* macro wedges (the "thali") */}
        <g transform={`rotate(-90 ${CENTER} ${CENTER})`}>
          {wedgeData.map((w) => {
            const len = w.pct * CIRCUMFERENCE;
            const offset = -(w.startFrac * CIRCUMFERENCE);
            return (
              <circle
                key={w.label}
                cx={CENTER}
                cy={CENTER}
                r={RING_RADIUS}
                fill="none"
                stroke={w.color}
                strokeWidth={RING_STROKE}
                strokeDasharray={`${len} ${CIRCUMFERENCE - len}`}
                strokeDashoffset={offset}
              />
            );
          })}
        </g>

        {/* inner hole to read as a plate, not a solid disc */}
        <circle
          cx={CENTER}
          cy={CENTER}
          r={RING_RADIUS - RING_STROKE / 2 - 3}
          fill="#152A1D"
          stroke="#8B8677"
          strokeOpacity={0.4}
          strokeWidth={1}
        />

        {/* wedge labels */}
        {wedgeData.map((w) => (
          <text
            key={w.label}
            x={w.labelPoint.x}
            y={w.labelPoint.y}
            fill="#EDE7D8"
            fontSize="11"
            fontFamily="SFMono-Regular, Consolas, monospace"
            textAnchor="middle"
            dominantBaseline="middle"
          >
            {Math.round(w.pct * 100)}%
          </text>
        ))}

        {/* pulse line cutting across the plate */}
        <path
          d={pulsePath}
          fill="none"
          stroke="#F3EEE1"
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength={100}
          strokeDasharray={100}
          className="animate-drawline motion-reduce:[stroke-dashoffset:0]"
        />
      </svg>

      {/* center emblem, kept outside the spinning svg so it stays upright */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="rounded-full bg-saag-dark/90 p-3 border border-steel/40">
          <UtensilsCrossed className="w-6 h-6 text-cream" strokeWidth={1.5} />
        </div>
      </div>
    </div>
  );
}

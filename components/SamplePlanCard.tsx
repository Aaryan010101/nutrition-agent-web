const rows = [
  { time: "7:00 AM", meal: "Poha + peanuts", cost: "₹18" },
  { time: "1:00 PM", meal: "Dal, rice, sabzi", cost: "₹42" },
  { time: "4:30 PM", meal: "Roasted chana", cost: "₹8" },
  { time: "8:00 PM", meal: "Roti + palak paneer", cost: "₹55" },
];

export default function SamplePlanCard() {
  return (
    <div className="paper-card rounded-lg p-6 max-w-sm w-full border border-steel/20 shadow-xl -rotate-1">
      <div className="flex items-center justify-between mb-1">
        <p className="font-display text-base">Today&apos;s Thali</p>
        <span className="font-mono text-[10px] uppercase tracking-widest text-steel">
          Chandigarh
        </span>
      </div>
      <p className="font-mono text-[11px] text-steel mb-4">
        Goal: weight loss · Budget: ₹4,000/mo
      </p>

      <div className="ticket-dashed" />
      <div className="divide-y divide-steel/20">
        {rows.map((r) => (
          <div
            key={r.time}
            className="flex items-center justify-between py-2 font-mono text-xs"
          >
            <span className="text-steel w-16 shrink-0">{r.time}</span>
            <span className="flex-1 px-2 text-ink">{r.meal}</span>
            <span className="text-ember">{r.cost}</span>
          </div>
        ))}
      </div>
      <div className="ticket-dashed mt-1" />

      <div className="flex items-center justify-between pt-3 font-mono text-xs">
        <span className="text-steel uppercase tracking-wide">Day total</span>
        <span className="text-ink font-semibold">≈ ₹123</span>
      </div>
      <div className="flex items-center justify-between font-mono text-xs">
        <span className="text-steel uppercase tracking-wide">
          Monthly est.
        </span>
        <span className="text-ink font-semibold">≈ ₹3,690</span>
      </div>
    </div>
  );
}

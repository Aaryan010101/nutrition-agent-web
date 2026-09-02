import { LucideIcon } from "lucide-react";

interface Props {
  hindiName: string;
  englishName: string;
  description: string;
  Icon: LucideIcon;
}

export default function MenuFeatureCard({
  hindiName,
  englishName,
  description,
  Icon,
}: Props) {
  return (
    <div className="paper-card rounded-lg p-5 border border-steel/20 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <Icon className="w-6 h-6 text-ember" strokeWidth={1.75} />
        <span className="font-mono text-[10px] uppercase tracking-widest text-steel">
          Today&apos;s special
        </span>
      </div>
      <div>
        <p className="font-display text-lg leading-tight">{hindiName}</p>
        <p className="font-mono text-[11px] uppercase tracking-wide text-steel mt-0.5">
          {englishName}
        </p>
      </div>
      <p className="text-sm text-ink/80 leading-relaxed">{description}</p>
    </div>
  );
}

interface Props {
  index: number;
  title: string;
  description: string;
  isLast?: boolean;
}

export default function OrderTicketStep({
  index,
  title,
  description,
  isLast,
}: Props) {
  return (
    <div className={`py-5 ${!isLast ? "ticket-dashed" : ""} first:border-t-0`}>
      <div className="flex items-baseline gap-4">
        <span className="font-mono text-2xl text-turmeric shrink-0">
          {String(index).padStart(2, "0")}
        </span>
        <div>
          <p className="font-display text-lg text-cream">{title}</p>
          <p className="text-sm text-cream/70 mt-1 max-w-md">{description}</p>
        </div>
      </div>
    </div>
  );
}

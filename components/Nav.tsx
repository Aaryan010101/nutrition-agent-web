import Link from "next/link";
import { SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import { UtensilsCrossed } from "lucide-react";

export default function Nav() {
  return (
    <header className="sticky top-0 z-20 backdrop-blur bg-saag/85 border-b border-cream/10">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <span className="rounded-full border border-turmeric/60 p-1.5 group-hover:bg-turmeric/10 transition-colors">
            <UtensilsCrossed className="w-4 h-4 text-turmeric" strokeWidth={2} />
          </span>
          <span className="font-display text-lg tracking-tight">
            Thali &amp; Pulse
          </span>
        </Link>

        <nav className="flex items-center gap-3">
          <SignedOut>
            <Link
              href="/sign-in"
              className="font-mono text-xs uppercase tracking-widest text-cream/80 hover:text-cream px-3 py-2"
            >
              Sign in
            </Link>
            <Link
              href="/sign-up"
              className="font-mono text-xs uppercase tracking-widest bg-turmeric text-ink px-4 py-2 rounded-md hover:bg-turmeric-dim transition-colors"
            >
              Get started
            </Link>
          </SignedOut>
          <SignedIn>
            <Link
              href="/dashboard"
              className="font-mono text-xs uppercase tracking-widest bg-turmeric text-ink px-4 py-2 rounded-md hover:bg-turmeric-dim transition-colors"
            >
              Open agent
            </Link>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
        </nav>
      </div>
    </header>
  );
}

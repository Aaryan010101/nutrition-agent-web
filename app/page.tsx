import Link from "next/link";
import { Camera, MapPin, Wallet, CalendarDays } from "lucide-react";
import Nav from "@/components/Nav";
import ThaliPulseGraphic from "@/components/ThaliPulseGraphic";
import MenuFeatureCard from "@/components/MenuFeatureCard";
import OrderTicketStep from "@/components/OrderTicketStep";
import SamplePlanCard from "@/components/SamplePlanCard";

export default function Home() {
  return (
    <main className="min-h-screen bg-saag">
      <Nav />

      {/* HERO */}
      <section className="max-w-6xl mx-auto px-5 sm:px-8 pt-16 sm:pt-24 pb-20 grid md:grid-cols-2 gap-14 items-center">
        <div className="animate-risein">
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-turmeric mb-4">
            Nutrition, plated your way
          </p>
          <h1 className="font-display text-4xl sm:text-5xl leading-[1.05] tracking-tight text-cream">
            Fuel like it&apos;s a thali.
            <br />
            Train like it&apos;s a target.
          </h1>
          <p className="mt-6 text-cream/75 text-base sm:text-lg leading-relaxed max-w-md">
            An AI nutrition agent that reads your plate, respects your
            budget, and plans your day around what&apos;s actually sold in
            your city &mdash; not imported superfoods.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/sign-up"
              className="bg-ember hover:bg-ember-dim text-cream font-display px-6 py-3 rounded-md transition-colors"
            >
              Build my thali
            </Link>
            <Link
              href="/sign-in"
              className="font-mono text-xs uppercase tracking-widest text-cream/80 hover:text-cream"
            >
              I already have an account →
            </Link>
          </div>
        </div>

        <ThaliPulseGraphic />
      </section>

      {/* MENU / FEATURES */}
      <section className="max-w-6xl mx-auto px-5 sm:px-8 py-16 border-t border-cream/10">
        <div className="flex items-end justify-between mb-8 flex-wrap gap-3">
          <h2 className="font-display text-2xl sm:text-3xl text-cream">
            The full menu
          </h2>
          <p className="font-mono text-xs uppercase tracking-widest text-steel">
            4 things a normal diet app won&apos;t do
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MenuFeatureCard
            Icon={Camera}
            hindiName="थाली से पहचानो"
            englishName="Snap your plate"
            description="Describe or photograph what's in front of you and get an honest read on calories and balance."
          />
          <MenuFeatureCard
            Icon={MapPin}
            hindiName="अपने शहर का स्वाद"
            englishName="Local & regional"
            description="Suggestions built from dal, roti, and seasonal sabzi found in your own city — not quinoa and kale."
          />
          <MenuFeatureCard
            Icon={Wallet}
            hindiName="बजट में भरपेट"
            englishName="Budget-smart"
            description="Tell it your monthly food budget and every meal plan is costed to fit inside it."
          />
          <MenuFeatureCard
            Icon={CalendarDays}
            hindiName="पूरा महीना, एक नज़र में"
            englishName="Day & month charts"
            description="A full-day table or a rotating four-week plan, plus the grocery list to shop for it."
          />
        </div>
      </section>

      {/* HOW IT WORKS + SAMPLE PLAN */}
      <section className="max-w-6xl mx-auto px-5 sm:px-8 py-16 border-t border-cream/10 grid lg:grid-cols-2 gap-16 items-start">
        <div>
          <h2 className="font-display text-2xl sm:text-3xl text-cream mb-6">
            How the order goes
          </h2>
          <div>
            <OrderTicketStep
              index={1}
              title="Tell us about you"
              description="Age, goal, city, and how much you can spend on food each month."
            />
            <OrderTicketStep
              index={2}
              title="Show us your plate"
              description="Describe a meal you just ate, or ask what to eat next."
            />
            <OrderTicketStep
              index={3}
              title="Get your thali"
              description="A full day's plan with timing, cost per meal, and a shopping list."
            />
            <OrderTicketStep
              index={4}
              title="Repeat & refine"
              isLast
              description="Swap a meal, stretch it into a month, and keep the same budget."
            />
          </div>
        </div>

        <div className="flex justify-center lg:justify-end lg:pt-10">
          <SamplePlanCard />
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-cream/10">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="font-mono text-[11px] text-steel">
            Thali &amp; Pulse — a Personalized Nutrition Agent
          </p>
          <p className="font-mono text-[11px] text-steel">
            Powered by IBM watsonx Orchestrate · Not a substitute for medical
            advice
          </p>
        </div>
      </footer>
    </main>
  );
}

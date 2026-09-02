"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { Send, UtensilsCrossed } from "lucide-react";
import ChatBubble from "@/components/ChatBubble";

interface Message {
  role: "user" | "assistant";
  content: string;
  /** If set, this is what actually gets sent to the API instead of
   * `content` (used to silently attach the known profile to every
   * follow-up message, without cluttering what the user sees). */
  apiContent?: string;
}

interface Profile {
  age: string;
  weight: string;
  height: string;
  goal: string;
  city: string;
  budget: string;
  diet: string;
  allergies: string;
  medical: string;
  activity: string;
  mealPattern: string;
  favoriteFoods: string;
}

const EMPTY_PROFILE: Profile = {
  age: "",
  weight: "",
  height: "",
  goal: "Weight gain",
  city: "",
  budget: "",
  diet: "Vegetarian",
  allergies: "",
  medical: "",
  activity: "Moderately active",
  mealPattern: "",
  favoriteFoods: "",
};

const WELCOME: Message = {
  role: "assistant",
  content:
    "Hi! I'm your Personal Nutrition Assistant. Fill in your details on the left and I'll build you a thali that fits your age, goal, city, and budget.",
};

function buildIntakeMessage(p: Profile): string {
  const parts: string[] = [
    `I'm ${p.age} years old, ${p.weight}kg, ${p.height}cm.`,
    `My main goal is ${p.goal.toLowerCase()}.`,
    `I live in ${p.city}, with a monthly food budget of ₹${p.budget}.`,
    `My diet preference is ${p.diet.toLowerCase()}.`,
    `Food allergies or dislikes: ${p.allergies.trim() || "none"}.`,
    `Medical conditions: ${p.medical.trim() || "none"}.`,
    `My activity level is ${p.activity.toLowerCase()}.`,
  ];
  if (p.mealPattern.trim()) {
    parts.push(`My preferred meal pattern is: ${p.mealPattern.trim()}.`);
  }
  if (p.favoriteFoods.trim()) {
    parts.push(`Foods I especially enjoy: ${p.favoriteFoods.trim()}.`);
  }
  parts.push(
    "I've given you everything you need already — please don't ask me these again. Please go ahead and put together my personalized diet plan, a sample thali, and a grocery list within my budget."
  );
  return parts.join(" ");
}

function buildProfileTag(p: Profile): string {
  const bits = [
    `${p.age}y`,
    `${p.weight}kg`,
    `${p.height}cm`,
    p.goal.toLowerCase(),
    p.city,
    `₹${p.budget}/month budget`,
    p.diet.toLowerCase(),
    `allergies: ${p.allergies.trim() || "none"}`,
    `medical: ${p.medical.trim() || "none"}`,
    p.activity.toLowerCase(),
  ];
  if (p.mealPattern.trim()) bits.push(`meal pattern: ${p.mealPattern.trim()}`);
  if (p.favoriteFoods.trim()) bits.push(`likes: ${p.favoriteFoods.trim()}`);
  return `[My profile, already provided — do not ask for these again: ${bits.join(
    ", "
  )}.]`;
}

export default function Dashboard() {
  const [step, setStep] = useState<"intake" | "chat">("intake");
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [formError, setFormError] = useState<string | null>(null);
  // Controls whether the profile form panel is visible on MOBILE only.
  // On desktop (lg breakpoint) the panel is always shown side-by-side
  // regardless of this flag. On mobile it starts open, then auto-hides
  // once the first plan is generated, leaving just the chat -- the
  // user can tap "Edit profile" to bring it back.
  const [profileOpen, setProfileOpen] = useState(true);

  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | undefined>(undefined);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  function updateField<K extends keyof Profile>(key: K, value: Profile[K]) {
    setProfile((prev) => ({ ...prev, [key]: value }));
  }

  async function sendToAgent(nextMessages: Message[]) {
    setError(null);
    setLoading(true);
    try {
      // Send the API-augmented version of each message (falls back to
      // the plain content when no augmentation was attached).
      const historyForApi = nextMessages.map((m) => ({
        role: m.role,
        content: m.apiContent ?? m.content,
      }));

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ history: historyForApi, threadId }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data?.error || "The agent could not respond.");
      }

      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      if (data.threadId) {
        setThreadId(data.threadId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function handleStartPlan() {
    const required: [keyof Profile, string][] = [
      ["age", "age"],
      ["weight", "weight"],
      ["height", "height"],
      ["city", "city"],
      ["budget", "monthly food budget"],
    ];
    const missing = required.find(([key]) => !profile[key].trim());
    if (missing) {
      setFormError(`Please fill in your ${missing[1]}.`);
      return;
    }
    setFormError(null);

    const intakeText = buildIntakeMessage(profile);
    const nextMessages: Message[] = [
      WELCOME,
      { role: "user", content: intakeText },
    ];
    setMessages(nextMessages);
    setStep("chat");
    setProfileOpen(false);
    sendToAgent(nextMessages);
  }

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    // Silently attach the known profile to what's actually sent to the
    // agent, on every single follow-up -- so the model always has the
    // profile right next to the current question, instead of relying
    // on it correctly recalling something from earlier in a long
    // conversation. The user only ever sees their own typed text.
    const profileTag = buildProfileTag(profile);
    const augmented = `${trimmed}\n\n${profileTag}`;

    const newUserMessage: Message = {
      role: "user",
      content: trimmed,
      apiContent: augmented,
    };
    const nextMessages: Message[] = [...messages, newUserMessage];
    setMessages(nextMessages);
    setInput("");
    await sendToAgent(nextMessages);
  }

  const inputClasses =
    "w-full paper-card rounded-md px-3 py-2 text-sm text-ink placeholder:text-steel focus:outline-none border border-steel/20";
  const labelClasses =
    "block font-mono text-[10px] uppercase tracking-widest text-steel mb-1";

  return (
    <main className="h-screen h-[100dvh] flex flex-col bg-saag">
      {/* header */}
      <header className="flex items-center justify-between px-5 sm:px-8 h-16 border-b border-cream/10 shrink-0">
        <Link href="/" className="flex items-center gap-2">
          <span className="rounded-full border border-turmeric/60 p-1.5">
            <UtensilsCrossed className="w-4 h-4 text-turmeric" strokeWidth={2} />
          </span>
          <div className="leading-tight">
            <p className="font-display text-sm">Advance Nutrition Agent</p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-steel">
              Live on watsonx Orchestrate
            </p>
          </div>
        </Link>
        <UserButton afterSignOutUrl="/" />
      </header>

      <div className="flex-1 overflow-hidden flex flex-col lg:flex-row">
        {/* intake form (left panel on desktop, top on mobile) */}
        <div
          className={`${
            profileOpen ? "block" : "hidden"
          } lg:block max-h-[42vh] lg:max-h-none lg:w-[360px] shrink-0 border-b lg:border-b-0 lg:border-r border-cream/10 overflow-y-auto`}
        >
          <div className="p-5 sm:p-6 flex flex-col gap-4">
            <div>
              <p className="font-display text-sm">Your profile</p>
              <p className="text-xs text-steel mt-0.5">
                Fill this once — we'll send it all to the agent together so it
                never has to ask twice.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClasses}>Age</label>
                <input
                  type="number"
                  min={1}
                  value={profile.age}
                  onChange={(e) => updateField("age", e.target.value)}
                  className={inputClasses}
                  placeholder="20"
                />
              </div>
              <div>
                <label className={labelClasses}>Weight (kg)</label>
                <input
                  type="number"
                  min={1}
                  value={profile.weight}
                  onChange={(e) => updateField("weight", e.target.value)}
                  className={inputClasses}
                  placeholder="65"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClasses}>Height (cm)</label>
                <input
                  type="number"
                  min={1}
                  value={profile.height}
                  onChange={(e) => updateField("height", e.target.value)}
                  className={inputClasses}
                  placeholder="170"
                />
              </div>
              <div>
                <label className={labelClasses}>Goal</label>
                <select
                  value={profile.goal}
                  onChange={(e) => updateField("goal", e.target.value)}
                  className={inputClasses}
                >
                  <option>Weight gain</option>
                  <option>Weight loss</option>
                  <option>Weight maintenance</option>
                </select>
              </div>
            </div>

            <div>
              <label className={labelClasses}>City</label>
              <input
                type="text"
                value={profile.city}
                onChange={(e) => updateField("city", e.target.value)}
                className={inputClasses}
                placeholder="Chandigarh"
              />
            </div>

            <div>
              <label className={labelClasses}>Monthly food budget (₹)</label>
              <input
                type="number"
                min={1}
                value={profile.budget}
                onChange={(e) => updateField("budget", e.target.value)}
                className={inputClasses}
                placeholder="5000"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClasses}>Diet</label>
                <select
                  value={profile.diet}
                  onChange={(e) => updateField("diet", e.target.value)}
                  className={inputClasses}
                >
                  <option>Vegetarian</option>
                  <option>Non-vegetarian</option>
                  <option>Eggetarian</option>
                  <option>Vegan</option>
                </select>
              </div>
              <div>
                <label className={labelClasses}>Activity level</label>
                <select
                  value={profile.activity}
                  onChange={(e) => updateField("activity", e.target.value)}
                  className={inputClasses}
                >
                  <option>Sedentary</option>
                  <option>Lightly active</option>
                  <option>Moderately active</option>
                  <option>Very active</option>
                </select>
              </div>
            </div>

            <div>
              <label className={labelClasses}>Allergies / dislikes</label>
              <input
                type="text"
                value={profile.allergies}
                onChange={(e) => updateField("allergies", e.target.value)}
                className={inputClasses}
                placeholder="None"
              />
            </div>

            <div>
              <label className={labelClasses}>Medical conditions</label>
              <input
                type="text"
                value={profile.medical}
                onChange={(e) => updateField("medical", e.target.value)}
                className={inputClasses}
                placeholder="None"
              />
            </div>

            <div>
              <label className={labelClasses}>
                Meal pattern <span className="normal-case">(optional)</span>
              </label>
              <input
                type="text"
                value={profile.mealPattern}
                onChange={(e) => updateField("mealPattern", e.target.value)}
                className={inputClasses}
                placeholder="3 meals + 2 snacks"
              />
            </div>

            <div>
              <label className={labelClasses}>
                Favorite foods <span className="normal-case">(optional)</span>
              </label>
              <input
                type="text"
                value={profile.favoriteFoods}
                onChange={(e) => updateField("favoriteFoods", e.target.value)}
                className={inputClasses}
                placeholder="Dal, paneer, rajma"
              />
            </div>

            {formError && (
              <p className="text-xs text-ember">{formError}</p>
            )}

            <button
              onClick={handleStartPlan}
              disabled={loading}
              className="bg-ember hover:bg-ember-dim disabled:opacity-40 disabled:cursor-not-allowed text-cream font-display text-sm py-2.5 rounded-md transition-colors"
            >
              {step === "chat" ? "Regenerate plan" : "Build my thali plan"}
            </button>
          </div>
        </div>

        {/* chat area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {step === "chat" && (
            <div className="lg:hidden shrink-0 border-b border-cream/10 px-4 py-2 flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-widest text-steel">
                {profileOpen ? "Editing your profile" : "Chat with your plan"}
              </span>
              <button
                onClick={() => setProfileOpen((v) => !v)}
                className="font-display text-xs text-turmeric underline underline-offset-2"
              >
                {profileOpen ? "Hide profile" : "Edit profile"}
              </button>
            </div>
          )}
          <div ref={scrollRef} className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 flex flex-col gap-4">
              {messages.map((m, i) => (
                <ChatBubble key={i} role={m.role} content={m.content} />
              ))}

              {loading && (
                <div className="flex items-center gap-2 font-mono text-xs text-steel pl-1">
                  <span className="w-2 h-2 rounded-full bg-turmeric animate-blip" />
                  <span className="w-2 h-2 rounded-full bg-turmeric animate-blip [animation-delay:0.2s]" />
                  <span className="w-2 h-2 rounded-full bg-turmeric animate-blip [animation-delay:0.4s]" />
                  <span className="ml-1">plating your answer…</span>
                </div>
              )}

              {error && (
                <div className="paper-card border border-ember/40 rounded-lg px-4 py-3 text-sm text-ember">
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* composer */}
          <div className="border-t border-cream/10 shrink-0">
            <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-end gap-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                rows={1}
                placeholder={
                  step === "intake"
                    ? "Fill your profile on the left first…"
                    : "Ask a follow-up, or tell it what you ate…"
                }
                disabled={step === "intake"}
                className="flex-1 resize-none paper-card rounded-md px-4 py-3 text-sm text-ink placeholder:text-steel focus:outline-none border border-steel/20 disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim() || step === "intake"}
                aria-label="Send message"
                className="bg-ember hover:bg-ember-dim disabled:opacity-40 disabled:cursor-not-allowed text-cream p-3 rounded-md transition-colors shrink-0"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
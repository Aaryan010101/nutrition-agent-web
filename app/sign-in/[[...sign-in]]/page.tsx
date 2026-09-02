import { SignIn } from "@clerk/nextjs";

export default function Page() {
  return (
    <main className="min-h-screen bg-saag flex flex-col items-center justify-center px-4 py-16">
      <a
        href="/"
        className="mb-8 font-mono text-xs uppercase tracking-[0.2em] text-steel hover:text-turmeric transition-colors"
      >
        ← Back to home
      </a>
      <SignIn
        appearance={{
          variables: {
            colorBackground: "#F3EEE1",
            colorText: "#161510",
            colorTextSecondary: "#5B5648",
            colorInputBackground: "#FFFFFF",
            colorInputText: "#161510",
          },
          elements: {
            card: "paper-card shadow-2xl border border-steel/30",
            headerTitle: "font-display text-ink",
            headerSubtitle: "text-steel",
            socialButtonsBlockButton: "border border-steel/30",
            socialButtonsBlockButtonText: "text-ink",
            dividerText: "text-steel",
            dividerLine: "bg-steel/30",
            formFieldLabel: "text-ink",
            formFieldInput: "text-ink bg-white border border-steel/30",
            formButtonPrimary:
              "bg-ember hover:bg-ember-dim font-display normal-case",
            footerActionText: "text-steel",
            footerActionLink: "text-ember hover:text-ember-dim",
            identityPreviewText: "text-ink",
            identityPreviewEditButton: "text-ember",
          },
        }}
      />
    </main>
  );
}

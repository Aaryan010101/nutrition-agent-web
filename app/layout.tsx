import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "Thali & Pulse — Your Personal Nutrition Agent",
  description:
    "An AI nutrition agent that plans your day like a thali: balanced, budgeted, and built for your city.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider
      appearance={{
        variables: {
          colorPrimary: "#E8A33D",
          colorBackground: "#1F3A28",
          colorInputBackground: "#F3EEE1",
          colorInputText: "#161510",
          colorText: "#EDE7D8",
          colorTextSecondary: "#C9C2AC",
          colorNeutral: "#EDE7D8",
          borderRadius: "0.5rem",
          fontFamily: '"Segoe UI", Arial, sans-serif',
        },
        elements: {
          userButtonPopoverCard: "bg-saag border border-cream/20 shadow-2xl",
          userButtonPopoverMain: "bg-saag",
          userButtonPopoverActionButton: "hover:bg-cream/10",
          userButtonPopoverActionButtonText: "text-cream",
          userButtonPopoverActionButtonIcon: "text-cream",
          userButtonPopoverFooter: "bg-saag-dark",
          userPreviewMainIdentifier: "text-cream",
          userPreviewSecondaryIdentifier: "text-steel",
        },
      }}
    >
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}

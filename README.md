# Thali & Pulse — Nutrition Agent Website

A Next.js website for your **Advance Nutrition Agent** (built in IBM watsonx
Orchestrate). People sign up / sign in with Clerk, then chat with your agent
in a themed dashboard. The design blends nutrition (a thali/plate motif) with
fitness (a pulse line) instead of a generic AI chatbot look.

## What's inside

- `app/page.tsx` — landing page (hero, features, how-it-works, sample plan)
- `app/sign-in`, `app/sign-up` — Clerk auth pages
- `app/dashboard/page.tsx` — the protected chat screen
- `app/api/chat/route.ts` — server route that talks to your agent
- `lib/watsonxOrchestrate.ts` — the actual IBM watsonx Orchestrate connector
- `components/` — the visual pieces (hero graphic, cards, chat bubbles)

## 1. Install dependencies

```bash
npm install
```

## 2. Set up Clerk (sign up / sign in)

1. Go to https://dashboard.clerk.com and create a free application.
2. Copy your **Publishable key** and **Secret key**.
3. Copy `.env.local.example` to `.env.local` and paste them in.

## 3. Connect your watsonx Orchestrate agent

In watsonx Orchestrate, open your **Advance Nutrition Agent** and go to
**Settings → API details**. You need three values for `.env.local`:

| Env variable | Where to find it |
|---|---|
| `WXO_INSTANCE_URL` | "Service instance URL" on the API details page |
| `WXO_API_KEY` | Generate an API key on the same page |
| `WXO_AGENT_ID` | The last part of your agent's URL, e.g. `.../edit/6d01cb7b-c8da-46e2-bd66-b0394eacf293` |

> If your account/region uses a slightly different REST path, the only file
> you'll ever need to touch is `lib/watsonxOrchestrate.ts` — everything else
> in the app just calls the `sendMessageToAgent()` function from there.

## 4. Run it

```bash
npm run dev
```

Open http://localhost:3000 — you'll see the landing page. Click **Get
started** to sign up, and you'll land on the live chat dashboard.

## 5. Deploy (optional)

This is a standard Next.js app, so it deploys as-is to Vercel, Netlify, or
any Node hosting. Remember to add the same environment variables in your
hosting provider's dashboard.

## Customizing

- Colors and fonts: `tailwind.config.ts` and `app/globals.css`
- Landing page copy: `app/page.tsx`
- The macro-split shown on the hero plate graphic: `WEDGES` array in
  `components/ThaliPulseGraphic.tsx`
- The sample plan preview: `components/SamplePlanCard.tsx`

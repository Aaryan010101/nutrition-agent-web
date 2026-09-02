/**
 * watsonx Orchestrate connector
 * ------------------------------------------------------------------
 * This file talks to your deployed "Advance Nutrition Agent" running
 * on IBM watsonx Orchestrate.
 *
 * WHERE TO FIND YOUR CREDENTIALS
 * 1. Open your agent in watsonx Orchestrate (the one you built).
 * 2. Go to Settings -> API details.
 *    - Copy the "Service instance URL" -> WXO_INSTANCE_URL
 *      (looks like: https://api.jp-tok.watson-orchestrate.cloud.ibm.com/instances/XXXXXXXX)
 *    - Generate/copy an API key -> WXO_API_KEY
 * 3. Open your agent, look at the browser URL bar. The last segment
 *    of the URL (a long id like 6d01cb7b-c8da-46e2-bd66-b0394eacf293)
 *    is your agent id -> WXO_AGENT_ID
 * 4. Put all three in your .env.local file (see .env.local.example).
 *
 * CONVERSATION MEMORY
 * We deliberately do NOT rely on IBM's `thread_id` for memory. In
 * testing, sending `thread_id` back to IBM made the agent forget
 * earlier answers (IBM's own thread-side context seems to override
 * or replace what we send). Instead, we keep it simple and robust:
 * every request sends the FULL conversation history so far, and we
 * never send `thread_id`. This is a standard stateless chat-completion
 * call -- the frontend is the single source of truth for memory.
 *
 * NOTE: If IBM changes the exact REST path for your plan/region, this
 * is the only file you need to edit -- everything else in the app
 * just calls `sendMessageToAgent()` below.
 * ------------------------------------------------------------------
 */

 type ChatRole = "user" | "assistant" | "system";

 export interface ChatMessage {
   role: ChatRole;
   content: string;
 }
 
 export interface AgentReply {
   reply: string;
   threadId?: string;
 }
 
 const IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token";
 
 // Simple in-memory token cache so we don't fetch a new IAM token on
 // every single message. Good enough for a student project; resets
 // automatically if the server restarts.
 let cachedToken: { value: string; expiresAt: number } | null = null;
 
 async function getIamToken(apiKey: string): Promise<string> {
   if (cachedToken && cachedToken.expiresAt > Date.now() + 30_000) {
     return cachedToken.value;
   }
 
   const response = await fetch(IAM_TOKEN_URL, {
     method: "POST",
     headers: { "Content-Type": "application/x-www-form-urlencoded" },
     body: new URLSearchParams({
       grant_type: "urn:ibm:params:oauth:grant-type:apikey",
       apikey: apiKey,
     }),
     cache: "no-store",
   });
 
   if (!response.ok) {
     const text = await response.text();
     throw new Error(
       `Could not authenticate with IBM Cloud IAM (status ${response.status}): ${text}`
     );
   }
 
   const data = await response.json();
   cachedToken = {
     value: data.access_token,
     expiresAt: Date.now() + (data.expires_in ? data.expires_in * 1000 : 3600_000),
   };
   return cachedToken.value;
 }
 
 export async function sendMessageToAgent(
   history: ChatMessage[],
   threadId?: string
 ): Promise<AgentReply> {
   const instanceUrl = process.env.WXO_INSTANCE_URL;
   const agentId = process.env.WXO_AGENT_ID;
   const apiKey = process.env.WXO_API_KEY;
 
   if (!instanceUrl || !agentId || !apiKey) {
     throw new Error(
       "Missing WXO_INSTANCE_URL, WXO_AGENT_ID or WXO_API_KEY. Check your .env.local file."
     );
   }
 
   const token = await getIamToken(apiKey);
 
   const endpoint = `${instanceUrl.replace(/\/$/, "")}/v1/orchestrate/${agentId}/chat/completions`;
 
   // We always send the FULL conversation history on every request.
   // We deliberately do NOT send thread_id back to IBM (see comment
   // at the top of this file) -- the frontend's message array is the
   // only source of conversation memory.
   //
   // We also prepend a short "system" reminder on every call --
   // as the FIRST message, not the last. OpenAI-compatible chat APIs
   // (which this endpoint follows) expect the "system" role message
   // to be the first entry in the array; a system message placed at
   // the end is non-standard and can be deprioritized or ignored by
   // the backend. Even with full history sent, the underlying model
   // can occasionally re-ask something the user already answered
   // earlier in a long conversation -- this reminder, placed first,
   // nudges it to re-read everything before asking a new question.
   const reminder: ChatMessage = {
     role: "system",
     content:
       "This is a continuing conversation, and you MUST follow this " +
       "process before writing your reply:\n" +
       "STEP 1 - Build a checklist by scanning every earlier message " +
       "in this conversation (including messages split across several " +
       "of the user's turns) for each of these items: age, weight, " +
       "height, primary goal (weight loss/gain/maintenance), city, " +
       "monthly or daily food budget, diet type (veg/non-veg/etc.), " +
       "food allergies or dislikes, medical conditions, activity " +
       "level, and meal pattern preference.\n" +
       "STEP 2 - Mark each item as KNOWN if it was stated ANYWHERE " +
       "earlier in the conversation, in the user's own words or " +
       "units, even if phrased casually or given alongside other " +
       "info in the same message.\n" +
       "STEP 3 - In your reply, NEVER ask about an item you marked " +
       "KNOWN, and NEVER repeat your introduction/greeting after the " +
       "first message of the conversation. Only ask about items that " +
       "are genuinely still missing, and ask about ALL of those in " +
       "one message rather than one at a time.\n" +
       "If every item is KNOWN, do not ask any further questions -- " +
       "proceed straight to generating the plan.",
   };
 
   const requestBody: Record<string, unknown> = {
     messages: [reminder, ...history],
     stream: false,
   };
 
   const response = await fetch(endpoint, {
     method: "POST",
     headers: {
       Authorization: `Bearer ${token}`,
       "Content-Type": "application/json",
     },
     body: JSON.stringify(requestBody),
     cache: "no-store",
   });
 
   if (!response.ok) {
     const text = await response.text();
     throw new Error(
       `Agent request failed (status ${response.status}): ${text}`
     );
   }
 
   const rawText = await response.text();
 
   let reply: string | undefined;
   let returnedThreadId: string | undefined;
 
   // Case 1: normal JSON response
   try {
     const data = JSON.parse(rawText);
     reply = data?.choices?.[0]?.message?.content;
     returnedThreadId = data?.thread_id;
   } catch {
     // Case 2: SSE / streaming format ("data: {...}\n\ndata: {...}\n\n")
     const lines = rawText
       .split("\n")
       .filter((line) => line.startsWith("data:"));
 
     let combined = "";
     for (const line of lines) {
       const jsonPart = line.replace(/^data:\s*/, "").trim();
       if (!jsonPart || jsonPart === "[DONE]") continue;
 
       try {
         const chunk = JSON.parse(jsonPart);
         const delta =
           chunk?.choices?.[0]?.delta?.content ??
           chunk?.choices?.[0]?.message?.content ??
           "";
         combined += delta;
         returnedThreadId = returnedThreadId ?? chunk?.thread_id;
       } catch {
         // skip malformed chunk lines
       }
     }
 
     reply = combined || undefined;
   }
 
   if (!reply) {
     throw new Error(
       "The agent responded, but no message content was found in the payload."
     );
   }
 
   return { reply, threadId: returnedThreadId ?? threadId };
 }
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { sendMessageToAgent, ChatMessage } from "@/lib/watsonxOrchestrate";

export async function POST(req: NextRequest) {
  const { userId } = auth();
  if (!userId) {
    return NextResponse.json({ error: "Not signed in." }, { status: 401 });
  }

  try {
    const body = await req.json();
    const history = body?.history as ChatMessage[] | undefined;
    const threadId = body?.threadId as string | undefined;

    if (!Array.isArray(history) || history.length === 0) {
      return NextResponse.json(
        { error: "No conversation history provided." },
        { status: 400 }
      );
    }

    const { reply, threadId: newThreadId } = await sendMessageToAgent(
      history,
      threadId
    );

    return NextResponse.json({ reply, threadId: newThreadId });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Something went wrong.";
    console.error("[/api/chat]", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

interface Props {
  role: "user" | "assistant";
  content: string;
}

export default function ChatBubble({ role, content }: Props) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`rounded-lg px-4 py-3 leading-relaxed text-sm ${
          isUser
            ? "max-w-[85%] sm:max-w-[70%] bg-turmeric text-ink rounded-br-sm whitespace-pre-wrap"
            : "max-w-[95%] sm:max-w-[85%] paper-card rounded-bl-sm border border-steel/20"
        }`}
      >
        {isUser ? (
          content
        ) : (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
              {content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
import { useEffect, useRef, useState } from "react";
import QueryTrace from "./QueryTrace";
import { sendChatMessage } from "../api.js";

const EXAMPLES = [
  { label: "SST off Mumbai, last monsoon", q: "What was the sea surface temperature off Mumbai last monsoon season?" },
  { label: "Arabian Sea vs Bay of Bengal salinity", q: "Compare average salinity between the Arabian Sea and Bay of Bengal in 2023" },
  { label: "Float count near Chennai", q: "How many float profiles are there near Chennai in the last year?" },
  { label: "Depth profile near Goa", q: "Show me a depth profile near Goa in January 2024" },
];

export default function ChatPanel({ onResult }) {
  const [messages, setMessages] = useState([
    { role: "assistant", explanation: "Ask me about subsurface ocean conditions from India's ARGO float network — temperature, salinity, or pressure, for any coast or season. I resolve the location and time window, run a real query against the float database, and explain what actually came back." },
  ]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  async function send(text) {
    const trimmed = text.trim();
    if (!trimmed || pending) return;
    setMessages((m) => [...m, { role: "user", text: trimmed }]);
    setInput("");
    setPending(true);

    try {
      const data = await sendChatMessage(trimmed);
      if (data.clarification) {
        setMessages((m) => [...m, { role: "assistant", clarification: data.clarification }]);
      } else {
        setMessages((m) => [...m, { role: "assistant", explanation: data.explanation, usedSynthetic: data.used_synthetic_data, intent: data.intent, sql: data.sql, rowCount: data.row_count }]);
        onResult(data);
      }
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", error: err.message }]);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="chat-pane">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m, i) => {
          if (m.role === "user") return <div key={i} className="msg user">{m.text}</div>;
          if (m.error) return <div key={i} className="msg assistant error">Error: {m.error}</div>;
          if (m.clarification) return (
            <div key={i} className="msg assistant">
              <div className="badge">Needs clarification</div>
              <div className="explanation">{m.clarification}</div>
            </div>
          );
          return (
            <div key={i} className="msg assistant">
              {m.usedSynthetic && <div className="badge">Demo data</div>}
              <div className="explanation">{m.explanation}</div>
              {m.intent && <QueryTrace intent={m.intent} sql={m.sql} rowCount={m.rowCount} />}
            </div>
          );
        })}
        {pending && <div className="msg assistant pending">Parsing query, running against the float database…</div>}
      </div>

      <div className="examples">
        {EXAMPLES.map((ex) => (
          <button key={ex.label} onClick={() => send(ex.q)} disabled={pending}>{ex.label}</button>
        ))}
      </div>

      <div className="chat-input">
        <input
          type="text" value={input} placeholder="e.g. Salinity near Kochi during last monsoon season"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          disabled={pending}
        />
        <button onClick={() => send(input)} disabled={pending || !input.trim()}>Ask</button>
      </div>
    </div>
  );
}

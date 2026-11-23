import DraftPreviewPanel from "./DraftPreviewPanel";
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import {
  ArrowUp,
  BookOpen,
  CarFront,
  ChevronLeft,
  FileText,
  Menu,
  MessageCircle,
  Plus,
  Scale,
  Search,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";

import "./App.css";
import { ApiError, chatApi, type History, type Usage } from "./api/client";
import type { AuthControls } from "./components/AuthGate";

// ============================================
// TYPES
// ============================================

type ChatMessage = {
  id: string;
  role: "user" | "notice";
  content: string;
};

type Conversation = {
  id: string;
  title: string;
  messages: ChatMessage[];
};

// ============================================
// SUGGESTED QUESTIONS
// ============================================

const features = [
  {
    icon: CarFront,
    title: "Traffic laws",
    description: "Understand the rules",
    prompt:
      "বাংলাদেশের সড়ক পরিবহন আইনে গুরুত্বপূর্ণ ট্রাফিক নিয়মগুলো কী?",
  },
  {
    icon: FileText,
    title: "Fines & penalties",
    description: "Know the consequences",
    prompt:
      "হেলমেট ছাড়া মোটরসাইকেল চালালে কী শাস্তি?",
  },
  {
    icon: ShieldCheck,
    title: "Your rights",
    description: "Travel with confidence",
    prompt:
      "ট্রাফিক পুলিশ গাড়ি থামালে আমার কী কী অধিকার আছে?",
  },
];

const quickQuestions = [
  {
    label: "Helmet fine",
    question:
      "হেলমেট ছাড়া মোটরসাইকেল চালালে কী শাস্তি?",
  },
  {
    label: "Driving licence",
    question:
      "ড্রাইভিং লাইসেন্স ছাড়া গাড়ি চালালে কী হয়?",
  },
  {
    label: "Traffic police",
    question:
      "ট্রাফিক পুলিশ জরিমানা করলে কী করব?",
  },
];


// ============================================
// SIMPLE O + LAW BRAND LOGO
// ============================================

function BrandMark({
  className = "",
}: {
  className?: string;
}) {
  return (
    <svg
      className={className}
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden="true"
    >
      {/* Letter O */}
      <circle
        cx="32"
        cy="32"
        r="25"
        stroke="currentColor"
        strokeWidth="3"
      />

      {/* Justice balance */}
      <path
        d="M32 17V46
           M18 26H46
           M21 26L15 38H27L21 26Z
           M43 26L37 38H49L43 26Z
           M24 47H40"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ============================================
// TRANSPARENT CIRCULAR WAVE
//
// No dark disk, no solid background.
// Multiple irregular, moving light ribbons.
// ============================================

function CircleWave({
  variant = "hero",
}: {
  variant?: "hero" | "thinking";
}) {
  const gradientId = `odhikar-wave-${variant}`;
  const secondaryId = `odhikar-wave-secondary-${variant}`;
  const glowId = `odhikar-wave-glow-${variant}`;

  return (
    <div
      className={`circle-wave circle-wave-${variant}`}
      role="img"
      aria-label="Animated Royal Amethyst circular wave with a justice-scale logo"
    >
      <svg
        className="circle-wave-svg"
        viewBox="0 0 320 320"
        fill="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient
            id={gradientId}
            x1="0%"
            y1="15%"
            x2="100%"
            y2="85%"
          >
            <stop
              offset="0%"
              stopColor="#A755F5"
            />
            <stop
              offset="28%"
              stopColor="#7044B7"
            />
            <stop
              offset="59%"
              stopColor="#5663F0"
            />
            <stop
              offset="83%"
              stopColor="#35A7E8"
            />
            <stop
              offset="100%"
              stopColor="#9F76FF"
            />
          </linearGradient>

          <linearGradient
            id={secondaryId}
            x1="100%"
            y1="0%"
            x2="0%"
            y2="100%"
          >
            <stop
              offset="0%"
              stopColor="#5BD9FF"
            />
            <stop
              offset="38%"
              stopColor="#6555E7"
            />
            <stop
              offset="70%"
              stopColor="#B56CF2"
            />
            <stop
              offset="100%"
              stopColor="#EC8BD5"
            />
          </linearGradient>

          <filter
            id={glowId}
            x="-55%"
            y="-55%"
            width="210%"
            height="210%"
          >
            <feGaussianBlur stdDeviation="3.5" />
          </filter>
        </defs>

        {/* A very faint guide ring */}
        <circle
          cx="160"
          cy="160"
          r="106"
          stroke="#7044B7"
          strokeOpacity="0.08"
          strokeWidth="1"
        />

        {/* Diffused light: transparent SVG background */}
        <g className="wave-glow">
          <path
            d="M160 52
               C225 43 276 95 272 160
               C270 227 222 273 157 269
               C91 267 47 220 51 157
               C56 95 98 55 160 52Z"
            stroke={`url(#${gradientId})`}
            strokeOpacity="0.5"
            strokeWidth="9"
            filter={`url(#${glowId})`}
          />
        </g>

        {/* Main organic wave */}
        <g className="wave-wave-one">
          <path
            d="M160 52
               C226 42 278 95 270 164
               C263 233 220 274 155 268
               C91 263 45 220 51 155
               C56 97 101 55 160 52Z"
            stroke={`url(#${gradientId})`}
            strokeWidth="3.1"
            strokeLinecap="round"
          />

          <path
            d="M158 58
               C224 50 269 100 265 164
               C261 226 217 266 155 262
               C98 258 55 216 57 157
               C60 102 103 60 158 58Z"
            stroke={`url(#${secondaryId})`}
            strokeOpacity="0.42"
            strokeWidth="1.15"
          />
        </g>

        {/* Second wave, moving independently */}
        <g className="wave-wave-two">
          <path
            d="M164 53
               C230 58 272 105 269 165
               C264 231 212 273 151 267
               C86 261 49 212 53 151
               C58 89 106 47 164 53Z"
            stroke={`url(#${secondaryId})`}
            strokeWidth="2.6"
            strokeLinecap="round"
          />

          <path
            d="M164 61
               C225 65 264 105 261 165
               C258 226 213 265 152 260
               C93 254 57 209 60 152
               C65 96 107 55 164 61Z"
            stroke="#8472F5"
            strokeOpacity="0.38"
            strokeWidth="1"
          />
        </g>

        {/* Third flowing ribbon */}
        <g className="wave-wave-three">
          <path
            d="M157 51
               C219 53 271 99 271 157
               C272 219 229 269 164 269
               C101 270 52 229 51 166
               C50 103 93 50 157 51Z"
            stroke={`url(#${gradientId})`}
            strokeOpacity="0.78"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </g>

        {/* Fine luminous filaments */}
        <g className="wave-filaments">
          {Array.from({ length: 12 }, (_, i) => (
            <ellipse
              key={i}
              cx="160"
              cy="160"
              rx={106 - i * 0.9}
              ry={103 + i * 0.35}
              transform={`rotate(${i * 4 - 22} 160 160)`}
              stroke={
                i % 2 === 0
                  ? `url(#${gradientId})`
                  : `url(#${secondaryId})`
              }
              strokeWidth="0.65"
              strokeOpacity={0.25 - i * 0.01}
            />
          ))}
        </g>

        {/* Moving highlight */}
        <g className="wave-highlight">
          <circle
            cx="160"
            cy="54"
            r="3.4"
            fill="#B9C5FF"
            opacity="0.55"
            filter={`url(#${glowId})`}
          />
          <circle
            cx="160"
            cy="54"
            r="1.8"
            fill="#7E60E7"
          />
        </g>

        {/* Minimal law logo without any background */}
        <g className="wave-law-symbol">
          <circle
            cx="160"
            cy="160"
            r="26"
            stroke="#7044B7"
            strokeWidth="2.2"
          />

          <path
            d="M160 143V179
               M145 150H175
               M148 150L143 160H153L148 150Z
               M172 150L167 160H177L172 150Z
               M151 181H169"
            stroke="#7044B7"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
      </svg>
    </div>
  );
}

// ============================================
// MAIN APP
// ============================================

export default function App({ session, openAuth, signOut }: AuthControls) {
  const [conversations, setConversations] = useState<
    Conversation[]
  >([]);

  const [activeId, setActiveId] = useState<string | null>(
    null
  );

  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [error, setError] = useState("");
  const [limitReached, setLimitReached] = useState(false);
  const sendingRef = useRef(false);
  const liveRef = useRef(true);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] =
    useState(false);

  const [searchOpen, setSearchOpen] = useState(false);
  const [search, setSearch] = useState("");

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const mode = session.mode;

  function titleFromHistory(history: History): string {
    const first = history.messages.find((m) => m.role === "user")?.content;
    return first ? (first.length > 44 ? first.slice(0, 44) + "…" : first) : "New conversation";
  }

  async function refreshUsage() {
    try {
      const current = await chatApi.usage();
      if (liveRef.current) setUsage(current);
    } catch (err) {
      if (liveRef.current) setError(err instanceof Error ? err.message : "Unable to load quota.");
    }
  }

  useEffect(() => {
    liveRef.current = true;
    async function load() {
      try {
        const [threads, quota] = await Promise.all([chatApi.threads(mode), chatApi.usage()]);
        if (!liveRef.current) return;
        setUsage(quota);
        // Load conversations with first-question titles, in parallel.
        const histories = await Promise.all(threads.map(async (t) => {
          try { return await chatApi.history(mode, t.thread_id); }
          catch { return { thread_id: t.thread_id, messages: [] } as History; }
        }));
        if (!liveRef.current) return;
        setConversations(histories.map((history) => ({
          id: history.thread_id,
          title: titleFromHistory(history),
          messages: history.messages.map((message) => ({
            id: crypto.randomUUID(), role: message.role === "user" ? "user" as const : "notice" as const,
            content: message.content,
          })),
        })));
      } catch (err) {
        if (liveRef.current) setError(err instanceof Error ? err.message : "Unable to load chats.");
      }
    }
    void load();
    return () => { liveRef.current = false; };
  }, [mode]);

  const currentConversation = conversations.find(
    (conversation) => conversation.id === activeId
  );

  const hasMessages = Boolean(
    currentConversation?.messages.length
  );

  const filteredConversations = conversations.filter(
    (conversation) =>
      conversation.title
        .toLowerCase()
        .includes(search.toLowerCase())
  );

  // ------------------------------------------
  // CHAT NAVIGATION (avoid switching mid-request)
  // ------------------------------------------

  function newChat() {
    if (sendingRef.current) return;
    setActiveId(null);
    setDraft("");
    setError("");
    setSidebarOpen(false);
    requestAnimationFrame(() => inputRef.current?.focus());
  }

  function openChat(id: string) {
    if (sendingRef.current) return;
    setActiveId(id);
    setDraft("");
    setError("");
    setSidebarOpen(false);
  }

  async function deleteChat(id: string) {
    if (sendingRef.current) return;
    // Guest deletion is intentionally unavailable: no guest DELETE route exists.
    if (mode === "guest") {
      setError("Guest chat deletion is not yet supported by the backend.");
      return;
    }
    try {
      await chatApi.delete(id);
      setConversations((previous) => previous.filter((c) => c.id !== id));
      if (activeId === id) setActiveId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete chat.");
    }
  }

  // ------------------------------------------
  // SELECT SUGGESTED QUESTION
  // ------------------------------------------

  function chooseQuestion(question: string) {
    setDraft(question);
    inputRef.current?.focus();
  }

  // ------------------------------------------
  // REAL BACKEND AI CHAT
  // ------------------------------------------

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || sendingRef.current) return;
    if (usage && usage.remaining <= 0) {
      setLimitReached(true);
      return;
    }

    sendingRef.current = true;
    setThinking(true);
    setError("");
    let id = activeId;

    try {
      if (!id) {
        const created = await chatApi.create(mode);
        id = created.thread_id;
        setConversations((previous) => [{ id: created.thread_id, title: question.slice(0, 44), messages: [] }, ...previous]);
        setActiveId(id);
      }
      const threadId = id;
      const newMessage: ChatMessage = {
        id: crypto.randomUUID(), role: "user", content: question,
      };
      setConversations((previous) => previous.map((c) =>
        c.id === threadId ? {
          ...c,
          title: c.messages.length === 0 ? (question.length > 44 ? question.slice(0, 44) + "…" : question) : c.title,
          messages: [...c.messages, newMessage],
        } : c
      ));
      setDraft("");

      const reply = await chatApi.send(mode, threadId, question);
      if (liveRef.current) {
        setConversations((previous) => previous.map((c) => c.id === threadId ? {
          ...c,
          messages: [...c.messages, { id: crypto.randomUUID(), role: "notice" as const, content: reply.answer }],
        } : c));
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) setLimitReached(true);
      if (liveRef.current) setError(err instanceof Error ? err.message : "Unable to send message.");
      // Refresh the server-authoritative history in case the Gemini call failed after accepting the message.
      if (id) {
        try {
          const history = await chatApi.history(mode, id);
          if (liveRef.current) setConversations((previous) => previous.map((c) => c.id === id ? {
            ...c,
            title: titleFromHistory(history),
            messages: history.messages.map((m) => ({ id: crypto.randomUUID(), role: m.role === "user" ? "user" as const : "notice" as const, content: m.content })),
          } : c));
        } catch { /* Keep visible error; backend may be offline. */ }
      }
    } finally {
      sendingRef.current = false;
      if (liveRef.current) {
        setThinking(false);
        void refreshUsage();
      }
    }
  }

  // ------------------------------------------
  // ENTER TO SEND
  // SHIFT + ENTER FOR NEW LINE
  // ------------------------------------------

  function handleComposerKeyDown(
    event: KeyboardEvent<HTMLTextAreaElement>
  ) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  // ------------------------------------------
  // CTRL + N / CMD + N
  // ------------------------------------------

  useEffect(() => {
    function handleShortcut(event: globalThis.KeyboardEvent) {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "n"
      ) {
        event.preventDefault();

        if (sendingRef.current) return;
        setActiveId(null);
        setDraft("");
        setSidebarOpen(false);
        inputRef.current?.focus();
      }

      if (event.key === "Escape") {
        setSidebarOpen(false);
      }
    }

    window.addEventListener("keydown", handleShortcut);

    return () => {
      window.removeEventListener(
        "keydown",
        handleShortcut
      );
    };
  }, []);

  // ------------------------------------------
  // SCROLL TO LAST MESSAGE
  // ------------------------------------------

  useEffect(() => {
    if (hasMessages) {
      messagesEndRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [thinking, currentConversation?.messages.length, hasMessages]);

// Development-only Draft AI Preview
if (
  import.meta.env.DEV &&
  new URLSearchParams(window.location.search).get("draft-preview") === "1"
) {
  return <DraftPreviewPanel />;
}

  return (
    <div
      className={`app-shell ${
        sidebarCollapsed ? "sidebar-collapsed" : ""
      }`}
    >
      {/* MOBILE SIDEBAR OVERLAY */}

      {sidebarOpen && (
        <button
          type="button"
          className="mobile-overlay"
          aria-label="Close sidebar"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* SIDEBAR */}

      <aside
        className={`sidebar ${
          sidebarOpen ? "sidebar-open" : ""
        }`}
      >
        <div className="sidebar-header">
          <button
            className="brand-lockup"
            type="button"
            onClick={newChat}
            title="Odhikar BD home"
          >
            <span className="brand-icon">
              <BrandMark />
            </span>

            {!sidebarCollapsed && (
              <span className="brand-name">
                Odhikar <span>BD</span>
              </span>
            )}
          </button>

          <button
            className="sidebar-toggle"
            type="button"
            aria-label="Toggle sidebar"
            onClick={() => {
              if (
                window.matchMedia("(max-width: 900px)").matches
              ) {
                setSidebarOpen(false);
              } else {
                setSidebarCollapsed((value) => !value);
              }
            }}
          >
            <ChevronLeft size={18} />
          </button>

          <button
            className="mobile-close"
            type="button"
            aria-label="Close sidebar"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <button
          className="new-chat-button"
          type="button"
          onClick={newChat}
          title="New conversation"
        >
          <Plus size={19} />

          {!sidebarCollapsed && (
            <>
              <span>New conversation</span>
              <kbd>Ctrl N</kbd>
            </>
          )}
        </button>

        <nav className="sidebar-navigation">
          <button
            className="navigation-link selected"
            type="button"
            onClick={newChat}
            title="Chat"
          >
            <MessageCircle size={19} />

            {!sidebarCollapsed && (
              <span>Chat</span>
            )}
          </button>

          <button
            className="navigation-link"
            type="button"
            disabled
            title="Law library — coming soon"
          >
            <BookOpen size={19} />

            {!sidebarCollapsed && (
              <span>Law Library</span>
            )}
          </button>
        </nav>

        {!sidebarCollapsed && (
          <>
            <div className="sidebar-section-heading">
              <span>RECENT CHATS</span>

              <button
                type="button"
                aria-label="Search conversations"
                onClick={() => setSearchOpen((value) => !value)}
              >
                <Search size={16} />
              </button>
            </div>

            {searchOpen && (
              <div className="sidebar-search">
                <Search size={15} />
                <input
                  value={search}
                  onChange={(event) =>
                    setSearch(event.target.value)
                  }
                  placeholder="Search conversations"
                  aria-label="Search conversations"
                />
              </div>
            )}

            <div className="conversation-list">
              {filteredConversations.length === 0 ? (
                <p className="empty-conversations">
                  {search
                    ? "No conversations match your search."
                    : "Your conversations will appear here."}
                </p>
              ) : (
                filteredConversations.map(
                  (conversation) => (
                    <div
                      key={conversation.id}
                      className={`conversation-item ${
                        conversation.id === activeId
                          ? "conversation-active"
                          : ""
                      }`}
                    >
                      <button
                        className="conversation-open"
                        type="button"
                        onClick={() =>
                          openChat(conversation.id)
                        }
                      >
                        <MessageCircle size={15} />
                        <span>
                          {conversation.title}
                        </span>
                      </button>

                      <button
                        className="conversation-delete"
                        type="button"
                        aria-label={`Delete ${conversation.title}`}
                        title={mode === "guest" ? "Guest deletion is unavailable" : "Delete conversation"}
                        disabled={mode === "guest" || thinking}
                        onClick={() => { void deleteChat(conversation.id); }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  )
                )
              )}
            </div>
          </>
        )}

        <div className="sidebar-footer">
          {!sidebarCollapsed && (
            <div className="sidebar-quote">
              <span className="quote-line" />
              <strong>Know the law.</strong>
              <span>Know your rights.</span>
            </div>
          )}

          <div className="sidebar-footer-note">
            <Scale size={15} />

            {!sidebarCollapsed && (
              <span>Legal information assistant</span>
            )}
          </div>
        </div>
      </aside>

      {/* MAIN WORKSPACE */}

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu"
              type="button"
              aria-label="Open sidebar"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu size={22} />
            </button>

            <span className="topbar-brand">
              Odhikar BD
            </span>

            <span className="topbar-divider" />

            <span className="topbar-title">
              {currentConversation?.title ?? "Home"}
            </span>
          </div>

          <div className="topbar-right">
            {usage && <span style={{ fontSize: 12, color: "#7044B7", fontWeight: 600 }} title="Messages remaining">{usage.remaining}/{usage.limit} left</span>}
            {mode === "guest" ? (
              <button type="button" onClick={openAuth} style={{ border: "1px solid #d6c6ec", borderRadius: 9, padding: "7px 10px", background: "white", color: "#7044B7", cursor: "pointer" }}>Sign in</button>
            ) : (
              <button type="button" onClick={() => { void signOut().catch((err: unknown) => setError(err instanceof Error ? err.message : "Logout failed.")); }} style={{ border: "1px solid #e5dced", borderRadius: 9, padding: "7px 10px", background: "white", color: "#7044B7", cursor: "pointer" }}>Sign out</button>
            )}
            <span className="preview-indicator">
              <span className="preview-dot" />
              {mode === "guest" ? "GUEST MODE" : "SIGNED IN"}
            </span>

            <span
              className="topbar-avatar"
              aria-label={mode === "guest" ? "Guest account" : session.user?.display_name ?? "Account"}
            >
              {mode === "guest" ? "G" : (session.user?.display_name?.[0]?.toUpperCase() ?? "O")}
            </span>
          </div>
        </header>

        {error && <div role="alert" style={{ padding: "10px 18px", margin: "10px 20px 0", background: "#fff1f3", color: "#a63854", borderRadius: 10, fontSize: 13 }}>{error}</div>}
        {limitReached && <div role="dialog" aria-modal="true" aria-label="Message limit reached" style={{ position: "fixed", inset: 0, zIndex: 500, background: "#25133977", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ maxWidth: 390, width: "100%", borderRadius: 20, background: "#fff", padding: 28, boxShadow: "0 15px 60px #25133933" }}>
            <h2 style={{ margin: "0 0 10px", color: "#7044B7" }}>Message limit reached</h2>
            <p style={{ lineHeight: 1.7, fontSize: 14 }}>{mode === "guest" ? "You have used your 5 guest messages. Sign in to access 30 messages each day." : "You have used today's 30 messages. Your quota resets at midnight Bangladesh time."}</p>
            {mode === "guest" && <button type="button" onClick={() => { setLimitReached(false); openAuth(); }} style={{ background: "#7044B7", border: 0, color: "white", borderRadius: 9, padding: "11px 18px", marginRight: 10 }}>Sign in / Register</button>}
            <button type="button" onClick={() => setLimitReached(false)} style={{ border: "1px solid #e4d9f1", background: "white", color: "#7044B7", borderRadius: 9, padding: "11px 18px" }}>Close</button>
          </div>
        </div>}
        <main className="main-content">
          {!hasMessages ? (
            // HOME SCREEN
            <section className="welcome-screen">
              <div className="welcome-content">
                <div className="welcome-eyebrow">
                  YOUR LEGAL KNOWLEDGE COMPANION
                </div>

                <div className="welcome-wave">
                  <CircleWave variant="hero" />
                </div>

                <h1>
                  Understand the law.
                  <span> Know your rights.</span>
                </h1>

                <p className="welcome-description">
                  Clear, accessible information about
                  Bangladesh traffic laws, fines,
                  driving licences and your rights.
                </p>

                <div className="feature-grid">
                  {features.map((feature) => {
                    const Icon = feature.icon;

                    return (
                      <button
                        key={feature.title}
                        className="feature-card"
                        type="button"
                        onClick={() =>
                          chooseQuestion(feature.prompt)
                        }
                      >
                        <span className="feature-icon">
                          <Icon
                            size={21}
                            strokeWidth={1.75}
                          />
                        </span>

                        <span className="feature-text">
                          <strong>
                            {feature.title}
                          </strong>
                          <small>
                            {feature.description}
                          </small>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </section>
          ) : (
            // CHAT SCREEN
            <section className="chat-screen">
              <div className="chat-messages">
                {currentConversation?.messages.map(
                  (message) => (
                    <div
                      key={message.id}
                      className={`message-row ${
                        message.role === "user"
                          ? "message-user"
                          : "message-notice"
                      }`}
                    >
                      {message.role === "notice" && (
                        <span className="assistant-avatar">
                          <BrandMark />
                        </span>
                      )}

                      <div className="message-content">
                        {message.content}
                      </div>
                    </div>
                  )
                )}

                {thinking && (
                  <div
                    className="thinking-state"
                    role="status"
                    aria-live="polite"
                  >
                    <CircleWave variant="thinking" />

                    <div className="thinking-copy">
                      <strong>
                        Processing your question
                      </strong>
                      <span>
                        Checking Bangladesh traffic-law information…
                      </span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </section>
          )}
        </main>

        {/* MESSAGE COMPOSER */}

        <div className="composer-section">
          <div className="composer-container">
            <form
              className="composer"
              onSubmit={sendMessage}
            >
              <textarea
                ref={inputRef}
                rows={2}
                value={draft}
                maxLength={5000}
                onChange={(event) =>
                  setDraft(event.target.value)
                }
                onKeyDown={handleComposerKeyDown}
                placeholder="Ask Odhikar BD anything..."
                aria-label="Ask a legal question"
              />

              <div className="composer-actions">
                <span>
                  Enter to send · Shift + Enter for new line
                </span>

                <button
                  type="submit"
                  className="send-button"
                  aria-label="Send message"
                  disabled={!draft.trim() || thinking}
                >
                  <ArrowUp size={20} />
                </button>
              </div>
            </form>

            {!hasMessages && (
              <div className="quick-questions">
                <span>TRY ASKING</span>

                {quickQuestions.map((question) => (
                  <button
                    type="button"
                    key={question.label}
                    onClick={() =>
                      chooseQuestion(question.question)
                    }
                  >
                    {question.label}
                  </button>
                ))}
              </div>
            )}

            <p className="legal-disclaimer">
              Odhikar BD provides legal information,
              not professional legal advice.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

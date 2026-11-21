import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck, UserRound } from "lucide-react";
import { ApiError, authApi, guestApi, type Mode, type User } from "../api/client";
import "./AuthGate.css";

export type AuthSession = { mode: Mode; user: User | null };
export type AuthControls = {
  session: AuthSession;
  openAuth: () => void;
  signOut: () => Promise<void>;
};

type Props = { children: (controls: AuthControls) => ReactNode };
export default function AuthGate({ children }: Props) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [showAuth, setShowAuth] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    async function restore() {
      try {
        const user = await authApi.me(controller.signal);
        if (!controller.signal.aborted) setSession({ mode: "member", user });
      } catch (err) {
        if (controller.signal.aborted) return;
        if (err instanceof ApiError && err.status === 401) {
          setSession(null);
        } else {
          setError(err instanceof Error ? err.message : "Unable to connect to the server.");
        }
      } finally {
        if (!controller.signal.aborted) setChecking(false);
      }
    }
    void restore();
    return () => controller.abort();
  }, []);

  function switchMode(next: "login" | "register") {
    setMode(next); setPassword(""); setError(""); setNotice("");
  }

  async function continueGuest() {
    setSubmitting(true); setError("");
    try {
      await guestApi.session();
      setSession({ mode: "guest", user: null });
      setShowAuth(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create guest session.");
    } finally { setSubmitting(false); }
  }

  async function signOut() {
    await authApi.logout();
    setSession(null);
    setShowAuth(false);
    setPassword("");
    // Don't automatically reinstate a guest identity after logout.
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true); setError(""); setNotice("");
    try {
      if (mode === "register") {
        if (!name.trim()) throw new Error("Enter your name.");
        await authApi.register({ display_name: name.trim(), email: email.trim(), password });
        setPassword(""); setMode("login"); setNotice("Account created. Please sign in.");
        return;
      }
      const result = await authApi.login({ email: email.trim(), password });
      setPassword(""); setSession({ mode: "member", user: result.user }); setShowAuth(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error.");
    } finally { setSubmitting(false); }
  }

  if (checking) return <div className="auth-loading" role="status"><div className="auth-loading-mark">O</div><p>Opening Odhikar BD...</p></div>;

  if (session && !showAuth) {
    return <>{children({ session, openAuth: () => { setShowAuth(true); setError(""); }, signOut })}</>;
  }

  return (
    <div className="auth-page">
      <div className="auth-background-orb orb-one" aria-hidden="true" />
      <div className="auth-background-orb orb-two" aria-hidden="true" />
      <header className="auth-header"><div className="auth-brand"><span className="auth-brand-symbol">O</span><span>Odhikar <b>BD</b></span></div><span className="auth-header-label">KNOW YOUR RIGHTS</span></header>
      <main className="auth-main">
        <section className="auth-intro"><div className="auth-eyebrow">YOUR LEGAL KNOWLEDGE COMPANION</div><h1>Knowledge brings<span> confidence.</span></h1><p>Understand Bangladesh traffic laws and your rights. Try five AI questions without an account.</p><div className="auth-trust"><ShieldCheck size={18}/><span>Secure account and guest access</span></div></section>
        <section className="auth-card">
          <div className="auth-card-top"><div className="auth-card-icon"><LockKeyhole size={22}/></div><h2>{mode === "register" ? "Create your account" : "Welcome to Odhikar BD"}</h2><p>{mode === "register" ? "Sign up for 30 questions per day." : "Sign in or continue without an account."}</p></div>
          <form className="auth-form" onSubmit={(event) => { void submit(event); }}>
            {mode === "register" && <label className="auth-field"><span>Full name</span><div className="auth-input-wrap"><UserRound size={17}/><input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" maxLength={100} autoComplete="name" required/></div></label>}
            <label className="auth-field"><span>Email address</span><div className="auth-input-wrap"><Mail size={17}/><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" maxLength={254} required/></div></label>
            <label className="auth-field"><span>Password</span><div className="auth-input-wrap"><LockKeyhole size={17}/><input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder={mode === "register" ? "At least 12 characters" : "Your password"} minLength={mode === "register" ? 12 : 1} maxLength={128} autoComplete={mode === "register" ? "new-password" : "current-password"} required/><button className="auth-password-toggle" type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((x) => !x)}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>
            {error && <p className="auth-error" role="alert">{error}</p>}
            {notice && <p className="auth-notice" role="status">{notice}</p>}
            <button className="auth-submit" disabled={submitting} type="submit"><span>{submitting ? "Please wait..." : mode === "register" ? "Create account" : "Sign in"}</span><ArrowRight size={18}/></button>
          </form>
          <div className="auth-switch"><span>{mode === "register" ? "Already registered?" : "New to Odhikar BD?"}</span><button type="button" onClick={() => switchMode(mode === "register" ? "login" : "register")}>{mode === "register" ? "Sign in" : "Create an account"}</button></div>
          <div style={{ borderTop: "1px solid #eee9f3", paddingTop: 18, marginTop: 18 }}>
            <button className="auth-submit" type="button" disabled={submitting} onClick={() => { void continueGuest(); }} style={{ background: "#f2ecfb", color: "#7044b7" }}>Continue as guest · 5 free messages</button>
            {session?.mode === "guest" && <button type="button" onClick={() => setShowAuth(false)} style={{ display: "block", margin: "13px auto 0", color: "#7044b7", background: "none", border: 0 }}>Back to guest chat</button>}
            {session?.mode === "member" && <button type="button" onClick={() => setShowAuth(false)} style={{ display: "block", margin: "13px auto 0", color: "#7044b7", background: "none", border: 0 }}>Back to chat</button>}
          </div>
        </section>
      </main>
      <footer className="auth-footer"><span>© Odhikar BD</span><span>Legal information, not professional legal advice.</span></footer>
    </div>
  );
}

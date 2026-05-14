import { useEffect, useState } from 'react';
import TenderMonitor from './pages/TenderMonitor.jsx';
import { setAccessToken } from './services/api.js';
import { isSupabaseAuthConfigured, supabase } from './services/supabaseClient.js';

function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleLogin(event) {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (signInError) {
        throw signInError;
      }
    } catch (err) {
      setError('ورود انجام نشد. ایمیل یا رمز عبور را بررسی کنید.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  if (!isSupabaseAuthConfigured) {
    return (
      <main className="login-shell" dir="rtl">
        <section className="login-card">
          <p className="eyebrow">Niroban Rev 1E</p>
          <h1>نیروبان</h1>
          <div className="message message-error">
            تنظیمات ورود کامل نیست. متغیرهای VITE_SUPABASE_URL و VITE_SUPABASE_ANON_KEY را در Vercel یا فایل محلی تنظیم کنید.
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="login-shell" dir="rtl">
      <section className="login-card">
        <p className="eyebrow">Niroban Rev 1E</p>
        <h1>نیروبان</h1>
        <p className="hero-subtitle">ورود خصوصی برای سامانه پایش روزانه مناقصات و استعلام‌های گسترش انرژی.</p>

        {error ? <div className="message message-error">{error}</div> : null}

        <form className="login-form" onSubmit={handleLogin}>
          <label>
            ایمیل
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@example.com"
              autoComplete="email"
              required
              dir="ltr"
            />
          </label>

          <label>
            رمز عبور
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              dir="ltr"
            />
          </label>

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'در حال ورود...' : 'ورود به داشبورد'}
          </button>
        </form>
      </section>
    </main>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    if (!supabase) {
      setCheckingSession(false);
      return undefined;
    }

    supabase.auth.getSession().then(({ data }) => {
      const activeSession = data.session || null;
      setSession(activeSession);
      setAccessToken(activeSession?.access_token || '');
      setCheckingSession(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, activeSession) => {
      setSession(activeSession || null);
      setAccessToken(activeSession?.access_token || '');
      setCheckingSession(false);
    });

    return () => listener.subscription.unsubscribe();
  }, []);

  async function handleSignOut() {
    if (supabase) {
      await supabase.auth.signOut();
    }
    setSession(null);
    setAccessToken('');
  }

  if (checkingSession) {
    return (
      <main className="login-shell" dir="rtl">
        <section className="login-card">
          <p className="eyebrow">Niroban Rev 1E</p>
          <h1>نیروبان</h1>
          <p className="hero-subtitle">در حال بررسی وضعیت ورود...</p>
        </section>
      </main>
    );
  }

  if (!session) {
    return <LoginScreen />;
  }

  return <TenderMonitor user={session.user} onSignOut={handleSignOut} />;
}

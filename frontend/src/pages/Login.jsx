import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { post } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AuthLayout from "./AuthLayout";

// Simple maths captcha -- no external service, checked entirely in the
// browser. Good enough to stop trivial scripted login attempts for a
// prototype; not a substitute for a real bot-detection service.
function randomCaptcha() {
  return { a: 1 + Math.floor(Math.random() * 9), b: 1 + Math.floor(Math.random() * 9) };
}

export default function Login() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [captcha, setCaptcha] = useState(randomCaptcha);
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function refreshCaptcha() {
    setCaptcha(randomCaptcha());
    setCaptchaAnswer("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (Number(captchaAnswer) !== captcha.a + captcha.b) {
      setError(t("Incorrect captcha answer. Try again."));
      refreshCaptcha();
      return;
    }

    setLoading(true);
    try {
      const data = await post("/auth/login", { email, password });
      // Login is step 1 of 2. Carry the pending_token to the OTP page.
      sessionStorage.setItem("pending_token", data.pending_token);
      navigate("/otp");
    } catch (err) {
      setError(err.response?.data?.detail || t("Login failed"));
      refreshCaptcha();
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout title={t("Sign in")} subtitle={t("Enter your registered email and password to continue")}>
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="mb-5 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1.5" htmlFor="email">
            {t("Email")}
          </label>
          <input
            id="email"
            type="email"
            placeholder="you@company.com"
            className="w-full border border-slate-300 rounded-md px-3.5 py-2.5 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-1.5" htmlFor="password">
            {t("Password")}
          </label>
          <input
            id="password"
            type="password"
            placeholder="••••••••"
            className="w-full border border-slate-300 rounded-md px-3.5 py-2.5 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-1.5" htmlFor="captcha_answer">
            {t("Security check")}
          </label>
          <div className="flex items-center gap-2">
            <div className="bg-slate-100 border border-slate-300 rounded-md px-4 py-2.5 text-slate-800 font-semibold tracking-wide select-none">
              {captcha.a} + {captcha.b} = ?
            </div>
            <input
              id="captcha_answer"
              inputMode="numeric"
              className="flex-1 border border-slate-300 rounded-md px-3.5 py-2.5 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600"
              value={captchaAnswer}
              onChange={(e) => setCaptchaAnswer(e.target.value.replace(/\D/g, ""))}
              required
            />
            <button
              type="button"
              onClick={refreshCaptcha}
              title={t("New question")}
              aria-label={t("New question")}
              className="shrink-0 text-slate-500 hover:text-slate-700 border border-slate-300 rounded-md w-10 h-10 flex items-center justify-center"
            >
              ↻
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-800 text-white rounded-md py-2.5 font-medium hover:bg-indigo-900 transition-colors disabled:opacity-60"
        >
          {loading ? t("Signing in...") : t("Sign in")}
        </button>

        <p className="text-sm text-slate-500 mt-6 text-center">
          {t("New vendor?")}{" "}
          <Link to="/register" className="text-indigo-800 font-medium hover:text-indigo-900">
            {t("Register here")}
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}

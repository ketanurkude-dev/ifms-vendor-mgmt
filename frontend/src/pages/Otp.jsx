import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { post } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AuthLayout from "./AuthLayout";

export default function Otp() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [pendingToken] = useState(() => sessionStorage.getItem("pending_token"));

  useEffect(() => {
    if (!pendingToken) {
      navigate("/login");
    }
  }, [pendingToken, navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await post("/auth/verify-otp", {
        pending_token: pendingToken,
        otp: otp,
      });
      localStorage.setItem("access_token", data.access_token);
      sessionStorage.removeItem("pending_token");
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || t("OTP verification failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title={t("Verify OTP")}
      subtitle={t("Enter the 6-digit code sent to your registered mobile (demo: any 6 digits work)")}
    >
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="mb-5 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-1.5" htmlFor="otp">
            {t("OTP")}
          </label>
          <input
            id="otp"
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            className="w-full border border-slate-300 rounded-md px-3.5 py-2.5 tracking-[0.5em] text-center text-xl font-medium text-slate-800 placeholder:tracking-normal placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading || otp.length !== 6}
          className="w-full bg-indigo-800 text-white rounded-md py-2.5 font-medium hover:bg-indigo-900 transition-colors disabled:opacity-60"
        >
          {loading ? t("Verifying...") : t("Verify & continue")}
        </button>
      </form>
    </AuthLayout>
  );
}

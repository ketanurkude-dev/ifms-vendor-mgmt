import { useLanguage } from "../i18n/LanguageContext";

// Shared two-column layout for the login, OTP and register screens:
// a branded left panel, and the form on the right.
export default function AuthLayout({ title, subtitle, children }) {
  const { language, setLanguage, t } = useLanguage();

  return (
    <div className="h-screen flex bg-slate-50 overflow-hidden">
      <div className="hidden lg:flex lg:w-1/2 h-full relative flex-col justify-between bg-indigo-900 p-12 text-white border-r border-indigo-950">
        <div className="absolute top-0 left-0 w-full h-1.5 bg-amber-500" />

        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded bg-white/10 border border-white/20 flex items-center justify-center text-sm font-semibold">
              VP
            </div>
            <span className="text-base font-semibold tracking-wide">{t("Vendor Portal")}</span>
          </div>
          <p className="text-indigo-100/70 text-sm ml-[48px]">{t("Integrated Financial Management System")}</p>
        </div>

        <div className="max-w-sm">
          <h2 className="text-2xl font-semibold leading-snug mb-4">
            {t("One account for your registration, contracts and invoices")}
          </h2>
          <p className="text-indigo-100/80 text-sm leading-relaxed">
            {t(
              "Register as a vendor, track your registration and document review, raise invoices against your contracts, and follow their approval and payment status."
            )}
          </p>
        </div>

        <p className="text-xs text-indigo-100/50">
          &copy; {new Date().getFullYear()} {t("Vendor Portal")}. {t("For authorised use only.")}
        </p>
      </div>

      <div className="w-full lg:w-1/2 h-full overflow-y-auto flex justify-center p-6 sm:p-10">
        <div className="w-full max-w-md my-auto">
          <div className="flex items-center justify-between mb-8">
            <div className="lg:hidden flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-indigo-800 text-white flex items-center justify-center text-sm font-semibold">
                VP
              </div>
              <span className="font-semibold text-slate-800">{t("Vendor Portal")}</span>
            </div>
            <div className="flex border border-slate-300 rounded overflow-hidden text-xs font-medium ml-auto">
              <button
                onClick={() => setLanguage("en", false)}
                className={`px-2.5 py-1 ${language === "en" ? "bg-indigo-800 text-white" : "text-slate-600 hover:bg-slate-100"}`}
              >
                EN
              </button>
              <button
                onClick={() => setLanguage("hi", false)}
                className={`px-2.5 py-1 ${language === "hi" ? "bg-indigo-800 text-white" : "text-slate-600 hover:bg-slate-100"}`}
              >
                हिं
              </button>
            </div>
          </div>

          <h1 className="text-2xl font-semibold text-slate-800 mb-1">{title}</h1>
          {subtitle && <p className="text-sm text-slate-500 mb-8">{subtitle}</p>}

          {children}

          <div className="flex items-center justify-center gap-2 mt-10 text-xs text-slate-400">
            <span>{t("Developed by")}</span>
            <img src="/virtualgalaxy-logo.webp" alt="Virtual Galaxy" className="h-5" />
          </div>
        </div>
      </div>
    </div>
  );
}

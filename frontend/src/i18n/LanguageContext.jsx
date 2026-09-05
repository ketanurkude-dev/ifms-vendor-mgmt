import { createContext, useContext, useState } from "react";
import { put } from "../api/apiService";
import { hi } from "./hi";

const LanguageContext = createContext(null);

// Per FR-VEP-011: switchable from any screen, retained across sessions.
// localStorage gives instant same-browser persistence. syncWithAccount()
// (called once the vendor record is known, post-login) reconciles the
// account's saved preference with whatever is active locally, the same
// way the other two IFMS portals do it -- see their LanguageContext for
// the full rationale.
export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(() => localStorage.getItem("language") || "en");

  function setLanguage(next, persist = true) {
    setLanguageState(next);
    localStorage.setItem("language", next);
    localStorage.setItem("language_explicit", "1");
    if (persist) {
      put("/vendor/language", { language: next }).catch(() => {});
    }
  }

  function syncWithAccount(accountLanguage) {
    if (!accountLanguage) return;
    const explicit = localStorage.getItem("language_explicit") === "1";
    if (explicit) {
      if (accountLanguage !== language) {
        put("/vendor/language", { language }).catch(() => {});
      }
      return;
    }
    if (accountLanguage !== language) {
      setLanguageState(accountLanguage);
      localStorage.setItem("language", accountLanguage);
    }
  }

  function t(key) {
    if (language === "hi") {
      return hi[key] || key;
    }
    return key;
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, syncWithAccount, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within a LanguageProvider");
  return ctx;
}

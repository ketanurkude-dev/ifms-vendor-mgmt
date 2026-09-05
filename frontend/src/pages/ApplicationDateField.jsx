import { useLanguage } from "../i18n/LanguageContext";

// Shown (read-only) on every request/application form, same way a paper
// government form is date-stamped on submission. The real, authoritative
// date is server_date, set by the backend when the record is created --
// this is purely a visible cue for the person filling the form.
export default function ApplicationDateField() {
  const { t } = useLanguage();
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">{t("Application date")}</label>
      <input
        type="text"
        value={today}
        readOnly
        className="w-full border border-slate-200 rounded-md px-3.5 py-2.5 bg-slate-50 text-slate-500 cursor-not-allowed"
      />
    </div>
  );
}

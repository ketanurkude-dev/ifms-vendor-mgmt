import { useLanguage } from "../i18n/LanguageContext";

// Status chip used across applications, invoices and payments. Colour
// AND label both convey status, so it never relies on colour alone.
export function StatusChip({ status }) {
  const { t } = useLanguage();
  const styles = {
    Draft: "bg-slate-100 text-slate-600 border-slate-200",
    Submitted: "bg-amber-50 text-amber-700 border-amber-200",
    "Under Review": "bg-amber-50 text-amber-700 border-amber-200",
    Approved: "bg-green-50 text-green-700 border-green-200",
    Rejected: "bg-red-50 text-red-700 border-red-200",
    Returned: "bg-orange-50 text-orange-700 border-orange-200",
    Verified: "bg-green-50 text-green-700 border-green-200",
    Mismatch: "bg-orange-50 text-orange-700 border-orange-200",
    Failed: "bg-red-50 text-red-700 border-red-200",
    "Not Available": "bg-slate-100 text-slate-600 border-slate-200",
    "Manual Review Required": "bg-amber-50 text-amber-700 border-amber-200",
    Pending: "bg-amber-50 text-amber-700 border-amber-200",
    "Payment Initiated": "bg-amber-50 text-amber-700 border-amber-200",
    Processing: "bg-blue-50 text-blue-700 border-blue-200",
    "Paid / Credited": "bg-green-50 text-green-700 border-green-200",
    "Payment Failed": "bg-red-50 text-red-700 border-red-200",
    "Payment Returned": "bg-orange-50 text-orange-700 border-orange-200",
    "Payment Reversed": "bg-orange-50 text-orange-700 border-orange-200",
    Active: "bg-green-50 text-green-700 border-green-200",
    Completed: "bg-green-50 text-green-700 border-green-200",
    Terminated: "bg-slate-100 text-slate-600 border-slate-200",
    Delayed: "bg-red-50 text-red-700 border-red-200",
    Initiated: "bg-amber-50 text-amber-700 border-amber-200",
    Credited: "bg-green-50 text-green-700 border-green-200",
    Reversed: "bg-orange-50 text-orange-700 border-orange-200",
    Matched: "bg-green-50 text-green-700 border-green-200",
    Exception: "bg-red-50 text-red-700 border-red-200",
  };
  const style = styles[status] || "bg-slate-100 text-slate-600 border-slate-200";
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded border ${style}`}>
      {t(status)}
    </span>
  );
}

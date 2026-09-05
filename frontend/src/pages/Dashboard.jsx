import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { get } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";
import { StatusChip } from "./StatusChip";

export default function Dashboard() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    get("/vendor/dashboard")
      .then(setData)
      .catch(() => {
        setError(t("Session expired. Please log in again."));
        localStorage.removeItem("access_token");
        setTimeout(() => navigate("/login"), 1500);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  if (error) {
    return <div className="min-h-screen flex items-center justify-center text-slate-600">{error}</div>;
  }

  if (!data) {
    return <div className="min-h-screen flex items-center justify-center text-slate-600">{t("Loading...")}</div>;
  }

  const { vendor } = data;

  if (vendor.role === "reviewer") {
    return (
      <AppLayout>
        <div className="bg-white border border-slate-200 rounded p-6">
          <h1 className="text-xl font-semibold text-slate-800 mb-1">{vendor.company_name}</h1>
          <p className="text-sm text-slate-500">
            {t("Reviewer account. Use the Approver page to review vendor applications, documents, invoices and payments.")}
          </p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="bg-white border border-slate-200 rounded p-6">
          <div className="flex items-center justify-between mb-1">
            <h1 className="text-xl font-semibold text-slate-800">{vendor.company_name}</h1>
            <StatusChip status={vendor.status} />
          </div>
          <p className="text-sm text-slate-500 mb-4">{t("Welcome to your vendor dashboard")}</p>

          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span>{t("Profile completeness")}</span>
              <span>{data.profile_completeness_percent}%</span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-700" style={{ width: `${data.profile_completeness_percent}%` }} />
            </div>
          </div>

          {vendor.status === "Approved" && (
            <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
              {t("Your registration is approved. Vendor code:")} {vendor.vendor_code}. {t("You can now view your contracts and raise invoices.")}
            </p>
          )}
          {vendor.status === "Rejected" && (
            <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
              {t("Your application was rejected:")} {vendor.review_remarks}
            </p>
          )}
        </div>

        {data.pending_actions.length > 0 && (
          <div className="bg-white border border-slate-200 rounded p-6">
            <h2 className="text-sm font-semibold text-slate-700 mb-3">{t("Pending actions")}</h2>
            <ul className="space-y-2">
              {data.pending_actions.map((action, idx) => (
                <li key={idx} className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                  {action.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white border border-slate-200 rounded p-4">
            <h3 className="text-xs uppercase tracking-wide text-slate-400 mb-2">{t("Invoices")}</h3>
            {Object.keys(data.invoice_summary).length === 0 && <p className="text-sm text-slate-400">{t("None yet")}</p>}
            {Object.entries(data.invoice_summary).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between text-sm py-0.5">
                <StatusChip status={status} />
                <span className="text-slate-700 font-medium">{count}</span>
              </div>
            ))}
          </div>
          <div className="bg-white border border-slate-200 rounded p-4">
            <h3 className="text-xs uppercase tracking-wide text-slate-400 mb-2">{t("Payments")}</h3>
            <p className="text-sm text-slate-700">{t("Count")}: {data.payment_summary.payment_count}</p>
            <p className="text-sm text-slate-700">{t("Total credited")}: Rs. {data.payment_summary.total_credited}</p>
            <p className="text-sm text-slate-700">{t("Pending amount")}: Rs. {data.payment_summary.pending_amount}</p>
          </div>
          <div className="bg-white border border-slate-200 rounded p-4">
            <h3 className="text-xs uppercase tracking-wide text-slate-400 mb-2">{t("Contracts")}</h3>
            <p className="text-2xl font-semibold text-slate-800">{data.contract_count}</p>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded p-6">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              [t("Application reference"), vendor.application_reference],
              [t("Contact person"), vendor.contact_person_name],
              [t("Email"), vendor.email],
              [t("Mobile"), vendor.mobile],
              [t("PAN"), vendor.pan_number],
              [t("GSTIN"), vendor.gstin_number],
              [t("Bank"), vendor.bank_name],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs uppercase tracking-wide text-slate-400">{label}</dt>
                <dd className="text-sm text-slate-800 mt-0.5">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </AppLayout>
  );
}

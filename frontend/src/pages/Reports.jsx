import { useEffect, useState } from "react";
import { get } from "../api/apiService";
import { useCurrentVendor } from "../api/useCurrentVendor";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";

const VENDOR_REPORTS = [
  { key: "registration-status", label: "Registration status" },
  { key: "profile-document-status", label: "Profile & document status" },
  { key: "invoice-register", label: "Invoice register" },
  { key: "payment-status", label: "Payment status" },
  { key: "contract-summary", label: "Contract summary" },
  { key: "vendor-performance", label: "Vendor performance" },
];

const REVIEWER_REPORTS = [
  { key: "registration-pipeline", label: "Registration pipeline" },
  { key: "verification-exceptions", label: "Verification exceptions" },
  { key: "invoice-aging", label: "Invoice aging" },
  { key: "payment-aging", label: "Payment aging" },
  { key: "vendor-payment-summary", label: "Vendor-wise payment summary" },
  { key: "contract-performance", label: "Contract & performance" },
  { key: "notification-delivery", label: "Notification delivery" },
];

function JsonTable({ data }) {
  if (Array.isArray(data)) {
    if (data.length === 0) return <p className="text-slate-400 text-sm">No data</p>;
    if (typeof data[0] !== "object") {
      return <ul className="text-sm list-disc pl-5">{data.map((v, i) => <li key={i}>{String(v)}</li>)}</ul>;
    }
    const columns = Object.keys(data[0]);
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left uppercase tracking-wide text-slate-400 border-b border-slate-200">
              {columns.map((c) => <th key={c} className="py-2 pr-3">{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-b border-slate-100">
                {columns.map((c) => <td key={c} className="py-2 pr-3">{String(row[c] ?? "-")}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (data && typeof data === "object") {
    return (
      <div className="space-y-4">
        {Object.entries(data).map(([key, value]) => (
          <div key={key}>
            <h4 className="text-xs font-semibold uppercase text-slate-500 mb-2">{key.replace(/_/g, " ")}</h4>
            <JsonTable data={value} />
          </div>
        ))}
      </div>
    );
  }
  return <p className="text-sm">{String(data)}</p>;
}

export default function Reports() {
  const { t } = useLanguage();
  const vendor = useCurrentVendor();
  const isReviewer = vendor && vendor.role === "reviewer";
  const reportList = isReviewer ? REVIEWER_REPORTS : VENDOR_REPORTS;
  const [activeKey, setActiveKey] = useState(null);
  const [data, setData] = useState(null);

  useEffect(() => {
    if (activeKey) {
      get(`/reports/${activeKey}`).then(setData);
    }
  }, [activeKey]);

  if (!vendor) {
    return <div className="min-h-screen flex items-center justify-center text-slate-600">{t("Loading...")}</div>;
  }

  return (
    <AppLayout>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded p-4 lg:col-span-1 h-fit">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">{t("Reports")}</h2>
          <div className="space-y-1">
            {reportList.map((r) => (
              <button
                key={r.key}
                onClick={() => setActiveKey(r.key)}
                className={`w-full text-left text-sm px-3 py-2 rounded ${activeKey === r.key ? "bg-indigo-800 text-white" : "text-slate-600 hover:bg-slate-100"}`}
              >
                {t(r.label)}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded p-4 lg:col-span-3">
          {!activeKey && <p className="text-slate-400 text-center py-6">{t("Select a report")}</p>}
          {activeKey && !data && <p className="text-slate-400 text-center py-6">{t("Loading...")}</p>}
          {activeKey && data && <JsonTable data={data} />}
        </div>
      </div>
    </AppLayout>
  );
}

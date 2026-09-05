import { useEffect, useState } from "react";
import api from "../api/client";
import { get } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";
import { StatusChip } from "./StatusChip";

async function downloadAdvice(paymentId, reference) {
  const res = await api.get(`/payments/${paymentId}/advice`, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = `payment_advice_${reference}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

const emptyFilters = { status: "", search: "", date_from: "", date_to: "", min_amount: "", max_amount: "" };

export default function Payments() {
  const { t } = useLanguage();
  const [payments, setPayments] = useState(null);
  const [filters, setFilters] = useState(emptyFilters);

  function refresh() {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    get(`/payments?${params.toString()}`).then(setPayments);
  }

  useEffect(refresh, [filters]);

  const inputClass = "border border-slate-300 rounded-md px-2 py-1.5 text-xs";

  if (!payments) {
    return <div className="min-h-screen flex items-center justify-center text-slate-600">{t("Loading...")}</div>;
  }

  return (
    <AppLayout>
      <div className="bg-white border border-slate-200 rounded p-6">
        <h1 className="text-lg font-semibold text-slate-800 mb-4">{t("Payments")}</h1>

        <div className="flex flex-wrap gap-2 mb-4">
          <input
            className={inputClass}
            placeholder={t("Search invoice or reference")}
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
          <select className={inputClass} value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">{t("All statuses")}</option>
            <option value="Initiated">{t("Initiated")}</option>
            <option value="Processing">{t("Processing")}</option>
            <option value="Credited">{t("Credited")}</option>
            <option value="Failed">{t("Failed")}</option>
            <option value="Returned">{t("Returned")}</option>
            <option value="Reversed">{t("Reversed")}</option>
          </select>
          <input type="date" className={inputClass} value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} title={t("From date")} />
          <input type="date" className={inputClass} value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} title={t("To date")} />
          <input type="number" className={`${inputClass} w-24`} placeholder={t("Min amount")} value={filters.min_amount} onChange={(e) => setFilters({ ...filters, min_amount: e.target.value })} />
          <input type="number" className={`${inputClass} w-24`} placeholder={t("Max amount")} value={filters.max_amount} onChange={(e) => setFilters({ ...filters, max_amount: e.target.value })} />
          {Object.values(filters).some(Boolean) && (
            <button onClick={() => setFilters(emptyFilters)} className="text-xs text-slate-500 hover:text-slate-700">
              {t("Clear filters")}
            </button>
          )}
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-200">
              <th className="py-2">{t("Invoice no.")}</th>
              <th className="py-2">{t("Reference")}</th>
              <th className="py-2">{t("Payment date")}</th>
              <th className="py-2">{t("Amount")}</th>
              <th className="py-2">{t("Bank reference")}</th>
              <th className="py-2">{t("Expected by")}</th>
              <th className="py-2">{t("Credited on")}</th>
              <th className="py-2">{t("Reconciliation")}</th>
              <th className="py-2">{t("Status")}</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id} className="border-b border-slate-100">
                <td className="py-2">{p.invoice_number}</td>
                <td className="py-2">{p.payment_reference}</td>
                <td className="py-2">{p.server_date?.slice(0, 10)}</td>
                <td className="py-2">Rs. {p.amount}</td>
                <td className="py-2">{p.bank_reference || "-"}</td>
                <td className="py-2">{p.expected_completion_date || "-"}</td>
                <td className="py-2">{p.processed_at?.slice(0, 10) || "-"}</td>
                <td className="py-2"><StatusChip status={p.reconciliation_status} /></td>
                <td className="py-2"><StatusChip status={p.status} /></td>
                <td className="py-2">
                  <button onClick={() => downloadAdvice(p.id, p.payment_reference)} className="text-xs text-indigo-700 font-medium">
                    {t("Download advice")}
                  </button>
                </td>
              </tr>
            ))}
            {payments.length === 0 && (
              <tr><td colSpan={10} className="py-4 text-center text-slate-400">{t("No payments yet")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </AppLayout>
  );
}

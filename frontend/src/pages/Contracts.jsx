import { useEffect, useState } from "react";
import { get } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";
import { StatusChip } from "./StatusChip";

export default function Contracts() {
  const { t } = useLanguage();
  const [contracts, setContracts] = useState(null);
  const [filters, setFilters] = useState({ contract_number: "", status: "" });

  function refresh() {
    const params = new URLSearchParams();
    if (filters.contract_number) params.set("contract_number", filters.contract_number);
    if (filters.status) params.set("status", filters.status);
    get(`/contracts?${params.toString()}`).then(setContracts);
  }

  useEffect(refresh, [filters]);

  if (!contracts) {
    return <div className="min-h-screen flex items-center justify-center text-slate-600">{t("Loading...")}</div>;
  }

  return (
    <AppLayout>
      <div className="bg-white border border-slate-200 rounded p-6">
        <h1 className="text-lg font-semibold text-slate-800 mb-4">{t("Contracts")}</h1>

        <div className="flex flex-wrap gap-3 mb-4">
          <input
            className="border border-slate-300 rounded-md px-3 py-1.5 text-sm"
            placeholder={t("Search contract number")}
            value={filters.contract_number}
            onChange={(e) => setFilters({ ...filters, contract_number: e.target.value })}
          />
          <select
            className="border border-slate-300 rounded-md px-3 py-1.5 text-sm"
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">{t("All statuses")}</option>
            <option value="Active">{t("Active")}</option>
            <option value="Completed">{t("Completed")}</option>
            <option value="Terminated">{t("Terminated")}</option>
          </select>
        </div>

        <div className="space-y-3">
          {contracts.map((c) => (
            <div key={c.id} className="border border-slate-200 rounded p-4">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-medium text-slate-800">{c.title}</h3>
                <StatusChip status={c.status} />
              </div>
              <p className="text-sm text-slate-500 mb-2">{c.description}</p>
              <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm mb-2">
                <div><dt className="text-xs text-slate-400">{t("Contract no.")}</dt><dd>{c.contract_number}</dd></div>
                <div><dt className="text-xs text-slate-400">{t("PO no.")}</dt><dd>{c.po_number}</dd></div>
                <div><dt className="text-xs text-slate-400">{t("Department")}</dt><dd>{c.department}</dd></div>
                <div><dt className="text-xs text-slate-400">{t("Value")}</dt><dd>{c.currency} {c.contract_value}</dd></div>
                <div><dt className="text-xs text-slate-400">{t("Period")}</dt><dd>{c.start_date} {t("to")} {c.end_date}</dd></div>
                <div><dt className="text-xs text-slate-400">{t("Payment terms")}</dt><dd>{c.payment_terms}</dd></div>
              </dl>
              {c.performance_rating && (
                <p className="text-sm text-slate-600 mb-2">
                  {t("Performance rating")}: {c.performance_rating}/5 {c.performance_remarks && `— ${c.performance_remarks}`}
                </p>
              )}
              {c.milestones.length > 0 && (
                <div className="border-t border-slate-100 pt-2 mt-2">
                  <h4 className="text-xs uppercase tracking-wide text-slate-400 mb-1">{t("Milestones")}</h4>
                  <table className="w-full text-xs">
                    <tbody>
                      {c.milestones.map((m) => (
                        <tr key={m.id}>
                          <td className="py-1">{m.title}</td>
                          <td className="py-1 text-slate-500">{m.due_date}</td>
                          <td className="py-1 text-slate-500">{c.currency} {m.amount}</td>
                          <td className="py-1"><StatusChip status={m.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
          {contracts.length === 0 && <p className="text-slate-400 text-center py-6">{t("No contracts yet")}</p>}
        </div>
      </div>
    </AppLayout>
  );
}

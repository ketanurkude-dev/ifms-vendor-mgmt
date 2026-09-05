import { useState } from "react";
import api from "../api/client";
import { get } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";

async function downloadCsv(params) {
  const res = await api.get(`/audit/logs/export?${params.toString()}`, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = "audit_log.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export default function AuditLog() {
  const { t } = useLanguage();
  const [logs, setLogs] = useState([]);
  const [filters, setFilters] = useState({ entity_type: "", action: "", vendor_id: "", result: "" });

  function buildParams() {
    const params = new URLSearchParams();
    if (filters.entity_type) params.set("entity_type", filters.entity_type);
    if (filters.action) params.set("action", filters.action);
    if (filters.vendor_id) params.set("vendor_id", filters.vendor_id);
    if (filters.result) params.set("result", filters.result);
    return params;
  }

  function handleSearch() {
    get(`/audit/logs?${buildParams().toString()}`).then(setLogs);
  }

  const inputClass = "border border-slate-300 rounded-md px-3 py-1.5 text-sm";

  return (
    <AppLayout>
      <div className="bg-white border border-slate-200 rounded p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-semibold text-slate-800">{t("Audit log")}</h1>
          <button onClick={() => downloadCsv(buildParams())} className="text-xs text-indigo-700 font-medium">
            {t("Export CSV")}
          </button>
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          <input className={inputClass} placeholder={t("Entity type")} value={filters.entity_type} onChange={(e) => setFilters({ ...filters, entity_type: e.target.value })} />
          <input className={inputClass} placeholder={t("Action contains...")} value={filters.action} onChange={(e) => setFilters({ ...filters, action: e.target.value })} />
          <input className={inputClass} placeholder={t("Vendor ID")} value={filters.vendor_id} onChange={(e) => setFilters({ ...filters, vendor_id: e.target.value })} />
          <select className={inputClass} value={filters.result} onChange={(e) => setFilters({ ...filters, result: e.target.value })}>
            <option value="">{t("Any result")}</option>
            <option value="Success">{t("Success")}</option>
            <option value="Failure">{t("Failure")}</option>
          </select>
          <button onClick={handleSearch} className="bg-indigo-800 text-white rounded-md px-4 py-1.5 text-sm font-medium hover:bg-indigo-900">
            {t("Search")}
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left uppercase tracking-wide text-slate-400 border-b border-slate-200">
                <th className="py-2 pr-3">{t("Time")}</th>
                <th className="py-2 pr-3">{t("Actor")}</th>
                <th className="py-2 pr-3">{t("Role")}</th>
                <th className="py-2 pr-3">{t("Action")}</th>
                <th className="py-2 pr-3">{t("Entity")}</th>
                <th className="py-2 pr-3">{t("Result")}</th>
                <th className="py-2 pr-3">{t("Details")}</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-slate-100">
                  <td className="py-2 pr-3 text-slate-500">{log.server_date}</td>
                  <td className="py-2 pr-3">{log.actor_id || "-"}</td>
                  <td className="py-2 pr-3">{log.actor_role || "-"}</td>
                  <td className="py-2 pr-3">{log.action}</td>
                  <td className="py-2 pr-3">{log.entity_type}{log.entity_id ? ` #${log.entity_id}` : ""}</td>
                  <td className="py-2 pr-3">
                    <span className={log.result === "Success" ? "text-green-700" : "text-red-700"}>{log.result}</span>
                  </td>
                  <td className="py-2 pr-3 text-slate-500">{log.details || log.after_value || "-"}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={7} className="py-4 text-center text-slate-400">{t("Run a search to see results")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  );
}

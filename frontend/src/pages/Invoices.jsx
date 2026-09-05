import { useEffect, useState } from "react";
import { downloadFile, get, post, postForm, viewFile } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";
import ApplicationDateField from "./ApplicationDateField";
import { StatusChip } from "./StatusChip";

const emptyForm = {
  contract_id: "",
  invoice_number: "",
  invoice_date: "",
  bill_period: "",
  description: "",
  amount: "",
  tax_amount: "0",
};

export default function Invoices() {
  const { t } = useLanguage();
  const [invoices, setInvoices] = useState(null);
  const [contracts, setContracts] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [resubmitTarget, setResubmitTarget] = useState(null);
  const [docForm, setDocForm] = useState({ invoiceId: null, doc_type: "Tax invoice", file: null });

  function refresh() {
    get("/invoices").then(setInvoices);
    get("/contracts").then(setContracts);
  }

  useEffect(refresh, []);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const payload = { ...form, contract_id: Number(form.contract_id), amount: Number(form.amount), tax_amount: Number(form.tax_amount) };
      if (resubmitTarget) {
        await post(`/invoices/${resubmitTarget}/resubmit`, payload);
      } else {
        await post("/invoices", payload);
      }
      setForm(emptyForm);
      setShowForm(false);
      setResubmitTarget(null);
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || t("Could not raise invoice"));
    }
  }

  function startResubmit(invoice) {
    setForm({
      contract_id: String(invoice.contract_id), invoice_number: invoice.invoice_number + "-R",
      invoice_date: invoice.invoice_date, bill_period: invoice.bill_period || "",
      description: invoice.description, amount: String(invoice.amount), tax_amount: String(invoice.tax_amount),
    });
    setResubmitTarget(invoice.id);
    setShowForm(true);
  }

  async function handleUploadDoc(e) {
    e.preventDefault();
    if (!docForm.file) return;
    const formData = new FormData();
    formData.append("doc_type", docForm.doc_type);
    formData.append("file", docForm.file);
    await postForm(`/invoices/${docForm.invoiceId}/documents`, formData);
    setDocForm({ invoiceId: null, doc_type: "Tax invoice", file: null });
    refresh();
  }

  async function handleViewDoc(doc) {
    await viewFile(`/invoices/documents/${doc.id}/view`);
  }

  async function handleDownloadDoc(doc) {
    await downloadFile(`/invoices/documents/${doc.id}/download`, doc.file_name);
  }

  if (!invoices) {
    return <div className="min-h-screen flex items-center justify-center text-slate-600">{t("Loading...")}</div>;
  }

  const inputClass = "border border-slate-300 rounded-md px-3 py-2 text-sm w-full";
  const selectedContract = contracts.find((c) => String(c.id) === String(form.contract_id));

  return (
    <AppLayout>
      <div className="bg-white border border-slate-200 rounded p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-semibold text-slate-800">{t("Invoices")}</h1>
          <button
            onClick={() => { setShowForm(!showForm); setResubmitTarget(null); setForm(emptyForm); }}
            className="bg-indigo-800 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-indigo-900"
          >
            {showForm ? t("Cancel") : t("Raise invoice")}
          </button>
        </div>

        {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 mb-4">{error}</p>}

        {showForm && (
          <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6 border border-slate-200 rounded p-4">
            {resubmitTarget && <p className="sm:col-span-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">{t("Resubmitting a corrected invoice")}</p>}
            <ApplicationDateField />
            <div>
              <label className="block text-xs text-slate-500 mb-1">{t("Contract")}</label>
              <select name="contract_id" className={inputClass} value={form.contract_id} onChange={handleChange} required>
                <option value="">{t("Select contract")}</option>
                {contracts.map((c) => (
                  <option key={c.id} value={c.id}>{c.contract_number} — {c.title}</option>
                ))}
              </select>
              {selectedContract && (
                <p className="text-xs text-slate-500 mt-1">
                  {t("Remaining payable value")}: {selectedContract.currency} {selectedContract.remaining_value}
                </p>
              )}
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">{t("Invoice number")}</label>
              <input name="invoice_number" className={inputClass} value={form.invoice_number} onChange={handleChange} required />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">{t("Invoice date")}</label>
              <input name="invoice_date" type="date" className={inputClass} value={form.invoice_date} onChange={handleChange} required />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">{t("Bill period")}</label>
              <input name="bill_period" placeholder="e.g. Aug 2026" className={inputClass} value={form.bill_period} onChange={handleChange} />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">{t("Amount")}</label>
              <input name="amount" type="number" className={inputClass} value={form.amount} onChange={handleChange} required />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">{t("Tax amount")}</label>
              <input name="tax_amount" type="number" className={inputClass} value={form.tax_amount} onChange={handleChange} />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs text-slate-500 mb-1">{t("Description")}</label>
              <input name="description" className={inputClass} value={form.description} onChange={handleChange} required />
            </div>
            <div className="sm:col-span-2">
              <button type="submit" className="bg-indigo-800 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-indigo-900">
                {resubmitTarget ? t("Resubmit invoice") : t("Submit invoice")}
              </button>
            </div>
          </form>
        )}

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-200">
              <th className="py-2">{t("Invoice no.")}</th>
              <th className="py-2">{t("Date")}</th>
              <th className="py-2">{t("Amount")}</th>
              <th className="py-2">{t("Status")}</th>
              <th className="py-2">{t("Documents")}</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id} className="border-b border-slate-100 align-top">
                <td className="py-2">{inv.invoice_number}</td>
                <td className="py-2">{inv.invoice_date}</td>
                <td className="py-2">Rs. {inv.total_amount}</td>
                <td className="py-2"><StatusChip status={inv.status} /></td>
                <td className="py-2">
                  <ul className="text-xs text-slate-500">
                    {inv.documents.map((d) => (
                      <li key={d.id}>
                        {d.doc_type}: {d.file_name}{" "}
                        {d.has_file && (
                          <>
                            <button onClick={() => handleViewDoc(d)} className="text-indigo-700 hover:text-indigo-900">
                              ({t("View")})
                            </button>{" "}
                            <button onClick={() => handleDownloadDoc(d)} className="text-indigo-700 hover:text-indigo-900">
                              ({t("Download")})
                            </button>
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                  {docForm.invoiceId === inv.id ? (
                    <form onSubmit={handleUploadDoc} className="flex flex-col gap-1 mt-1">
                      <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png"
                        className="text-xs w-40"
                        onChange={(e) => setDocForm({ ...docForm, file: e.target.files[0] || null })}
                        required
                      />
                      <button type="submit" className="text-xs text-indigo-700 self-start">{t("Add")}</button>
                    </form>
                  ) : (
                    <button onClick={() => setDocForm({ invoiceId: inv.id, doc_type: "Tax invoice", file: null })} className="text-xs text-indigo-700 mt-1">
                      + {t("Attach document")}
                    </button>
                  )}
                </td>
                <td className="py-2">
                  {(inv.status === "Rejected" || inv.status === "Returned") && (
                    <button onClick={() => startResubmit(inv)} className="text-xs text-amber-700 font-medium">{t("Resubmit")}</button>
                  )}
                </td>
              </tr>
            ))}
            {invoices.length === 0 && (
              <tr><td colSpan={6} className="py-4 text-center text-slate-400">{t("No invoices raised yet")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </AppLayout>
  );
}

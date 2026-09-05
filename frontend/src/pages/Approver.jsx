import { useEffect, useState } from "react";
import { get, post } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";
import { StatusChip } from "./StatusChip";

const TABS = ["Applications", "Profile changes", "Contracts", "Invoices", "Payments"];

function ApplicationsTab() {
  const { t } = useLanguage();
  const [queue, setQueue] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [remarks, setRemarks] = useState("");
  const [error, setError] = useState("");

  function refreshQueue() {
    get("/approver/applications").then(setQueue);
  }

  useEffect(refreshQueue, []);

  useEffect(() => {
    if (selectedId) {
      get(`/approver/applications/${selectedId}`).then(setDetail);
    } else {
      setDetail(null);
    }
  }, [selectedId]);

  function refreshDetail() {
    if (selectedId) get(`/approver/applications/${selectedId}`).then(setDetail);
  }

  async function handleReview(newStatus) {
    setError("");
    if ((newStatus === "Returned" || newStatus === "Rejected") && !remarks) {
      setError(t("Remarks are required to return or reject an application"));
      return;
    }
    try {
      await post(`/approver/applications/${selectedId}/review`, { status: newStatus, review_remarks: remarks || null });
      setSelectedId(null);
      setRemarks("");
      refreshQueue();
    } catch (err) {
      setError(err.response?.data?.detail || t("Could not review application"));
    }
  }

  async function handleDocumentReview(docId, verification_status) {
    await post(`/approver/documents/${docId}/review`, { verification_status });
    refreshDetail();
  }

  async function handleCredentialDecision(verificationId, status) {
    await post(`/approver/credential-verifications/${verificationId}/decision`, { status });
    refreshDetail();
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="bg-white border border-slate-200 rounded p-4">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">{t("Pending applications")}</h2>
        <div className="space-y-2">
          {queue.map((item) => (
            <button
              key={item.id}
              onClick={() => setSelectedId(item.id)}
              className={`w-full text-left border rounded p-3 ${selectedId === item.id ? "border-amber-500 bg-amber-50" : "border-slate-200 hover:bg-slate-50"}`}
            >
              <p className="text-sm font-medium text-slate-800">{item.company_name}</p>
              <p className="text-xs text-slate-500">{item.application_reference} · {item.email}</p>
              <p className="text-xs text-slate-400 mt-0.5">{t("Submitted")}: {item.submitted_at?.slice(0, 10)}</p>
            </button>
          ))}
          {queue.length === 0 && <p className="text-slate-400 text-center py-6">{t("No pending applications")}</p>}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded p-4">
        {!detail && <p className="text-slate-400 text-center py-6">{t("Select an application to review")}</p>}
        {detail && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-700">{detail.vendor.company_name}</h2>
              <StatusChip status={detail.vendor.status} />
            </div>
            <dl className="grid grid-cols-2 gap-2 text-sm mb-4">
              <div><dt className="text-xs text-slate-400">{t("Vendor type")}</dt><dd>{detail.vendor.vendor_type}</dd></div>
              <div><dt className="text-xs text-slate-400">PAN</dt><dd>{detail.vendor.pan_number}</dd></div>
              <div><dt className="text-xs text-slate-400">GSTIN</dt><dd>{detail.vendor.gstin_number}</dd></div>
              <div><dt className="text-xs text-slate-400">{t("Bank")}</dt><dd>{detail.vendor.bank_name}</dd></div>
              <div><dt className="text-xs text-slate-400">{t("Account")}</dt><dd>{detail.vendor.bank_account_number}</dd></div>
            </dl>

            <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">{t("Automatic credential verification")}</h3>
            <div className="space-y-2 mb-4">
              {detail.credential_verifications.map((cv) => (
                <div key={cv.id} className="border border-slate-200 rounded p-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-700">{cv.credential_type} — {cv.reference_number}</span>
                    <StatusChip status={cv.status} />
                  </div>
                  {cv.mismatch_reason && <p className="text-xs text-orange-700">{cv.mismatch_reason}</p>}
                  {["Mismatch", "Failed", "Manual Review Required"].includes(cv.status) && (
                    <div className="flex gap-2 mt-1">
                      <button onClick={() => handleCredentialDecision(cv.id, "Verified")} className="text-xs text-green-700 font-medium">{t("Mark verified")}</button>
                      <button onClick={() => handleCredentialDecision(cv.id, "Failed")} className="text-xs text-red-700 font-medium">{t("Mark failed")}</button>
                    </div>
                  )}
                </div>
              ))}
              {detail.credential_verifications.length === 0 && <p className="text-slate-400 text-sm">{t("Not yet run")}</p>}
            </div>

            <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">{t("Documents")}</h3>
            <div className="space-y-2 mb-4">
              {detail.documents.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between border border-slate-200 rounded p-2">
                  <div>
                    <p className="text-sm text-slate-700">{doc.doc_type} (v{doc.version})</p>
                    <p className="text-xs text-slate-400">{doc.file_name}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusChip status={doc.verification_status} />
                    {doc.verification_status === "Pending" && (
                      <>
                        <button onClick={() => handleDocumentReview(doc.id, "Verified")} className="text-xs text-green-700 font-medium">{t("Verify")}</button>
                        <button onClick={() => handleDocumentReview(doc.id, "Rejected")} className="text-xs text-red-700 font-medium">{t("Reject")}</button>
                      </>
                    )}
                  </div>
                </div>
              ))}
              {detail.documents.length === 0 && <p className="text-slate-400 text-sm">{t("No documents uploaded")}</p>}
            </div>

            {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 mb-3">{error}</p>}

            <textarea
              placeholder={t("Remarks (required to reject or return)")}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm mb-3"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
            />
            <div className="flex gap-2">
              <button onClick={() => handleReview("Approved")} className="bg-green-700 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-green-800">{t("Approve")}</button>
              <button onClick={() => handleReview("Returned")} className="bg-orange-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-orange-700">{t("Return")}</button>
              <button onClick={() => handleReview("Rejected")} className="bg-red-700 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-red-800">{t("Reject")}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ProfileChangesTab() {
  const { t } = useLanguage();
  const [changes, setChanges] = useState([]);

  function refresh() {
    get("/approver/profile-changes").then(setChanges);
  }

  useEffect(refresh, []);

  async function handleDecision(id, status) {
    await post(`/approver/profile-changes/${id}/review`, { status });
    refresh();
  }

  return (
    <div className="bg-white border border-slate-200 rounded p-4">
      <h2 className="text-sm font-semibold text-slate-700 mb-3">{t("Pending profile change requests")}</h2>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-200"><th className="py-2">{t("Vendor ID")}</th><th className="py-2">{t("Field")}</th><th className="py-2">{t("Old value")}</th><th className="py-2">{t("New value")}</th><th className="py-2">{t("Requested on")}</th><th className="py-2">{t("Reason")}</th><th className="py-2"></th></tr></thead>
        <tbody>
          {changes.map((c) => (
            <tr key={c.id} className="border-b border-slate-100">
              <td className="py-2">{c.vendor_id}</td>
              <td className="py-2">{c.field_name}</td>
              <td className="py-2 text-slate-500">{c.old_value}</td>
              <td className="py-2">{c.new_value}</td>
              <td className="py-2 text-slate-500">{c.server_date?.slice(0, 10)}</td>
              <td className="py-2 text-slate-500">{c.reason}</td>
              <td className="py-2 flex gap-2">
                <button onClick={() => handleDecision(c.id, "Approved")} className="text-xs text-green-700 font-medium">{t("Approve")}</button>
                <button onClick={() => handleDecision(c.id, "Rejected")} className="text-xs text-red-700 font-medium">{t("Reject")}</button>
              </td>
            </tr>
          ))}
          {changes.length === 0 && <tr><td colSpan={6} className="py-4 text-center text-slate-400">{t("Nothing pending")}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function ContractsTab() {
  const { t } = useLanguage();
  const [contracts, setContracts] = useState([]);
  const [form, setForm] = useState({
    vendor_id: "", contract_number: "", po_number: "", title: "", description: "",
    department: "GNCTD Procurement Cell", currency: "INR", payment_terms: "Net 30 days from invoice approval",
    start_date: "", end_date: "", contract_value: "",
  });
  const [milestoneForm, setMilestoneForm] = useState({ contractId: null, title: "", due_date: "", amount: "" });
  const [error, setError] = useState("");

  function refresh() {
    get("/contracts").then(setContracts);
  }

  useEffect(refresh, []);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await post("/contracts", { ...form, vendor_id: Number(form.vendor_id), contract_value: Number(form.contract_value) });
      setForm({ ...form, vendor_id: "", contract_number: "", po_number: "", title: "", description: "", start_date: "", end_date: "", contract_value: "" });
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || t("Could not issue contract"));
    }
  }

  async function handleAddMilestone(e) {
    e.preventDefault();
    await post(`/contracts/${milestoneForm.contractId}/milestones`, {
      title: milestoneForm.title, due_date: milestoneForm.due_date, amount: Number(milestoneForm.amount),
    });
    setMilestoneForm({ contractId: null, title: "", due_date: "", amount: "" });
    refresh();
  }

  const inputClass = "border border-slate-300 rounded-md px-3 py-2 text-sm w-full";

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <h2 className="text-sm font-semibold text-slate-700 sm:col-span-2">{t("Issue a new contract")}</h2>
        {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 sm:col-span-2">{error}</p>}
        <div><label className="block text-xs text-slate-500 mb-1">{t("Vendor ID (approved vendor)")}</label><input name="vendor_id" className={inputClass} value={form.vendor_id} onChange={handleChange} required /></div>
        <div><label className="block text-xs text-slate-500 mb-1">{t("Contract number")}</label><input name="contract_number" className={inputClass} value={form.contract_number} onChange={handleChange} required /></div>
        <div><label className="block text-xs text-slate-500 mb-1">{t("PO number")}</label><input name="po_number" className={inputClass} value={form.po_number} onChange={handleChange} required /></div>
        <div><label className="block text-xs text-slate-500 mb-1">{t("Value")}</label><input name="contract_value" type="number" className={inputClass} value={form.contract_value} onChange={handleChange} required /></div>
        <div className="sm:col-span-2"><label className="block text-xs text-slate-500 mb-1">{t("Title")}</label><input name="title" className={inputClass} value={form.title} onChange={handleChange} required /></div>
        <div className="sm:col-span-2"><label className="block text-xs text-slate-500 mb-1">{t("Description")}</label><input name="description" className={inputClass} value={form.description} onChange={handleChange} required /></div>
        <div><label className="block text-xs text-slate-500 mb-1">{t("Department")}</label><input name="department" className={inputClass} value={form.department} onChange={handleChange} /></div>
        <div><label className="block text-xs text-slate-500 mb-1">{t("Payment terms")}</label><input name="payment_terms" className={inputClass} value={form.payment_terms} onChange={handleChange} /></div>
        <div><label className="block text-xs text-slate-500 mb-1">{t("Start date")}</label><input name="start_date" type="date" className={inputClass} value={form.start_date} onChange={handleChange} required /></div>
        <div><label className="block text-xs text-slate-500 mb-1">{t("End date")}</label><input name="end_date" type="date" className={inputClass} value={form.end_date} onChange={handleChange} required /></div>
        <div className="sm:col-span-2"><button type="submit" className="bg-indigo-800 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-indigo-900">{t("Issue contract")}</button></div>
      </form>

      <div className="bg-white border border-slate-200 rounded p-4">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">{t("All contracts")}</h2>
        <div className="space-y-3">
          {contracts.map((c) => (
            <div key={c.id} className="border border-slate-200 rounded p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium">{c.contract_number} — {t("vendor")} #{c.vendor_id}</span>
                <StatusChip status={c.status} />
              </div>
              {c.milestones.map((m) => (
                <div key={m.id} className="text-xs text-slate-500 flex justify-between border-t border-slate-100 py-1">
                  <span>{m.title} ({m.due_date})</span>
                  <StatusChip status={m.status} />
                </div>
              ))}
              {milestoneForm.contractId === c.id ? (
                <form onSubmit={handleAddMilestone} className="flex flex-wrap gap-2 mt-2">
                  <input placeholder={t("Title")} className="border border-slate-300 rounded px-2 py-1 text-xs" value={milestoneForm.title} onChange={(e) => setMilestoneForm({ ...milestoneForm, title: e.target.value })} required />
                  <input type="date" className="border border-slate-300 rounded px-2 py-1 text-xs" value={milestoneForm.due_date} onChange={(e) => setMilestoneForm({ ...milestoneForm, due_date: e.target.value })} required />
                  <input type="number" placeholder={t("Amount")} className="border border-slate-300 rounded px-2 py-1 text-xs w-24" value={milestoneForm.amount} onChange={(e) => setMilestoneForm({ ...milestoneForm, amount: e.target.value })} required />
                  <button type="submit" className="text-xs text-indigo-700 font-medium">{t("Add")}</button>
                </form>
              ) : (
                <button onClick={() => setMilestoneForm({ contractId: c.id, title: "", due_date: "", amount: "" })} className="text-xs text-indigo-700 mt-2">+ {t("Add milestone")}</button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function InvoicesTab() {
  const { t } = useLanguage();
  const [invoices, setInvoices] = useState([]);
  const [remarksFor, setRemarksFor] = useState(null);
  const [remarksText, setRemarksText] = useState("");
  const [error, setError] = useState("");

  function refresh() {
    get("/invoices").then(setInvoices);
  }

  useEffect(refresh, []);

  async function handleReview(id, status, review_remarks = null) {
    setError("");
    if (status !== "Approved" && !review_remarks) {
      setError(t("Remarks are required to reject or return an invoice"));
      return;
    }
    await post(`/invoices/${id}/review`, { status, review_remarks });
    setRemarksFor(null);
    setRemarksText("");
    refresh();
  }

  return (
    <div className="bg-white border border-slate-200 rounded p-4">
      <h2 className="text-sm font-semibold text-slate-700 mb-3">{t("All invoices")}</h2>
      {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 mb-3">{error}</p>}
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-200"><th className="py-2">{t("Invoice no.")}</th><th className="py-2">{t("Vendor ID")}</th><th className="py-2">{t("Date")}</th><th className="py-2">{t("Amount")}</th><th className="py-2">{t("Status")}</th><th className="py-2">{t("Action")}</th></tr></thead>
        <tbody>
          {invoices.map((inv) => (
            <tr key={inv.id} className="border-b border-slate-100 align-top">
              <td className="py-2">{inv.invoice_number}</td>
              <td className="py-2">{inv.vendor_id}</td>
              <td className="py-2">{inv.invoice_date}</td>
              <td className="py-2">Rs. {inv.total_amount}</td>
              <td className="py-2"><StatusChip status={inv.status} /></td>
              <td className="py-2">
                {inv.status === "Submitted" && (
                  <div>
                    <div className="flex gap-2 mb-1">
                      <button onClick={() => handleReview(inv.id, "Approved")} className="text-xs text-green-700 font-medium">{t("Approve")}</button>
                      <button onClick={() => setRemarksFor(remarksFor === inv.id ? null : inv.id)} className="text-xs text-orange-700 font-medium">{t("Return")} / {t("Reject")}</button>
                    </div>
                    {remarksFor === inv.id && (
                      <div className="flex flex-col gap-1">
                        <input
                          className="border border-slate-300 rounded px-2 py-1 text-xs"
                          placeholder={t("Remarks (required)")}
                          value={remarksText}
                          onChange={(e) => setRemarksText(e.target.value)}
                        />
                        <div className="flex gap-2">
                          <button onClick={() => handleReview(inv.id, "Returned", remarksText)} className="text-xs text-orange-700 font-medium">{t("Return")}</button>
                          <button onClick={() => handleReview(inv.id, "Rejected", remarksText)} className="text-xs text-red-700 font-medium">{t("Reject")}</button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </td>
            </tr>
          ))}
          {invoices.length === 0 && <tr><td colSpan={5} className="py-4 text-center text-slate-400">{t("No invoices")}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function PaymentsTab() {
  const { t } = useLanguage();
  const [invoices, setInvoices] = useState([]);
  const [payments, setPayments] = useState([]);

  function refresh() {
    get("/invoices").then(setInvoices);
    get("/payments").then(setPayments);
  }

  useEffect(refresh, []);

  async function handleInitiate(invoiceId) {
    await post(`/payments/invoices/${invoiceId}/initiate`, {});
    refresh();
  }

  async function handleStatus(paymentId, status) {
    await post(`/payments/${paymentId}/status`, {
      status, bank_reference: `UTR${Math.floor(Math.random() * 1e9)}`,
      response_code: "00", response_message: `${status} by bank simulation`,
    });
    refresh();
  }

  const approvedUnpaid = invoices.filter((inv) => inv.status === "Approved");

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded p-4">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">{t("Approved invoices awaiting payment")}</h2>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-200"><th className="py-2">{t("Invoice no.")}</th><th className="py-2">{t("Amount")}</th><th className="py-2">{t("Action")}</th></tr></thead>
          <tbody>
            {approvedUnpaid.map((inv) => (
              <tr key={inv.id} className="border-b border-slate-100">
                <td className="py-2">{inv.invoice_number}</td>
                <td className="py-2">Rs. {inv.total_amount}</td>
                <td className="py-2"><button onClick={() => handleInitiate(inv.id)} className="text-xs text-indigo-700 font-medium">{t("Initiate payment")}</button></td>
              </tr>
            ))}
            {approvedUnpaid.length === 0 && <tr><td colSpan={3} className="py-4 text-center text-slate-400">{t("Nothing pending")}</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="bg-white border border-slate-200 rounded p-4">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">{t("Payments (simulated banking callback)")}</h2>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-200"><th className="py-2">{t("Reference")}</th><th className="py-2">{t("Amount")}</th><th className="py-2">{t("Status")}</th><th className="py-2">{t("Action")}</th></tr></thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id} className="border-b border-slate-100">
                <td className="py-2">{p.payment_reference}</td>
                <td className="py-2">Rs. {p.amount}</td>
                <td className="py-2"><StatusChip status={p.status} /></td>
                <td className="py-2">
                  {p.status === "Initiated" && (
                    <div className="flex gap-2">
                      <button onClick={() => handleStatus(p.id, "Processing")} className="text-xs text-blue-700 font-medium">{t("Mark processing")}</button>
                      <button onClick={() => handleStatus(p.id, "Failed")} className="text-xs text-red-700 font-medium">{t("Mark failed")}</button>
                    </div>
                  )}
                  {p.status === "Processing" && (
                    <div className="flex gap-2">
                      <button onClick={() => handleStatus(p.id, "Credited")} className="text-xs text-green-700 font-medium">{t("Mark credited")}</button>
                      <button onClick={() => handleStatus(p.id, "Returned")} className="text-xs text-orange-700 font-medium">{t("Mark returned")}</button>
                      <button onClick={() => handleStatus(p.id, "Failed")} className="text-xs text-red-700 font-medium">{t("Mark failed")}</button>
                    </div>
                  )}
                  {p.status === "Credited" && (
                    <button onClick={() => handleStatus(p.id, "Reversed")} className="text-xs text-orange-700 font-medium">{t("Reverse")}</button>
                  )}
                </td>
              </tr>
            ))}
            {payments.length === 0 && <tr><td colSpan={4} className="py-4 text-center text-slate-400">{t("No payments yet")}</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Approver() {
  const { t } = useLanguage();
  const [tab, setTab] = useState("Applications");

  return (
    <AppLayout>
      <div className="mb-4 flex gap-2 border-b border-slate-200 flex-wrap">
        {TABS.map((tabName) => (
          <button
            key={tabName}
            onClick={() => setTab(tabName)}
            className={`px-4 py-2 text-sm font-medium border-b-2 ${tab === tabName ? "border-amber-600 text-amber-700" : "border-transparent text-slate-500 hover:text-slate-700"}`}
          >
            {t(tabName)}
          </button>
        ))}
      </div>

      {tab === "Applications" && <ApplicationsTab />}
      {tab === "Profile changes" && <ProfileChangesTab />}
      {tab === "Contracts" && <ContractsTab />}
      {tab === "Invoices" && <InvoicesTab />}
      {tab === "Payments" && <PaymentsTab />}
    </AppLayout>
  );
}

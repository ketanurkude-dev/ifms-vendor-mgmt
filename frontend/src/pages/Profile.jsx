import { useEffect, useState } from "react";
import { get, put, post } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";
import ApplicationDateField from "./ApplicationDateField";
import { StatusChip } from "./StatusChip";

const CRITICAL_FIELDS = ["legal_name", "pan_number", "gstin_number", "bank_account_number", "bank_ifsc", "email", "mobile"];

export default function Profile() {
  const { t } = useLanguage();
  const [vendor, setVendor] = useState(null);
  const [changes, setChanges] = useState([]);
  const [editForm, setEditForm] = useState({ trade_name: "", contact_person_name: "", address: "", bank_name: "" });
  const [changeField, setChangeField] = useState(CRITICAL_FIELDS[0]);
  const [changeValue, setChangeValue] = useState("");
  const [changeReason, setChangeReason] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function refresh() {
    get("/vendor/me").then((v) => {
      setVendor(v);
      setEditForm({ trade_name: v.trade_name || "", contact_person_name: v.contact_person_name, address: v.address, bank_name: v.bank_name });
    });
    get("/vendor/profile-changes").then(setChanges);
  }

  useEffect(refresh, []);

  async function handleSaveProfile(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await put("/vendor/profile", editForm);
      setMessage(t("Profile updated."));
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || t("Could not update profile"));
    }
  }

  async function handleRequestChange(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await post("/vendor/profile-changes", { field_name: changeField, new_value: changeValue, reason: changeReason });
      setMessage(t("Change request submitted for review."));
      setChangeValue("");
      setChangeReason("");
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || t("Could not submit change request"));
    }
  }

  if (!vendor) {
    return <div className="min-h-screen flex items-center justify-center text-slate-600">{t("Loading...")}</div>;
  }

  const inputClass = "w-full border border-slate-300 rounded-md px-3 py-2 text-sm";

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="bg-white border border-slate-200 rounded p-6">
          <h1 className="text-lg font-semibold text-slate-800 mb-6">{t("Profile")}</h1>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              [t("Application reference"), vendor.application_reference],
              [t("Vendor code"), vendor.vendor_code || t("Not yet assigned")],
              [t("Vendor type"), vendor.vendor_type],
              [t("Legal name"), vendor.legal_name],
              [t("Trade name"), vendor.trade_name || "-"],
              [t("Email"), vendor.email],
              [t("Mobile"), vendor.mobile],
              [t("PAN"), vendor.pan_number],
              [t("GSTIN"), vendor.gstin_number],
              [t("Bank account number"), vendor.bank_account_number],
              [t("Bank IFSC"), vendor.bank_ifsc],
              [t("Email verified"), vendor.email_verified ? t("Yes") : t("No")],
              [t("Mobile verified"), vendor.mobile_verified ? t("Yes") : t("No")],
              [t("Profile version"), vendor.profile_version],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs uppercase tracking-wide text-slate-400">{label}</dt>
                <dd className="text-sm text-slate-800 mt-0.5">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
        {message && <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">{message}</p>}

        <form onSubmit={handleSaveProfile} className="bg-white border border-slate-200 rounded p-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <h2 className="text-sm font-semibold text-slate-700 sm:col-span-2">{t("Edit basic details")}</h2>
          <div>
            <label className="block text-xs text-slate-500 mb-1">{t("Trade name")}</label>
            <input className={inputClass} value={editForm.trade_name} onChange={(e) => setEditForm({ ...editForm, trade_name: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">{t("Contact person")}</label>
            <input className={inputClass} value={editForm.contact_person_name} onChange={(e) => setEditForm({ ...editForm, contact_person_name: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs text-slate-500 mb-1">{t("Address")}</label>
            <input className={inputClass} value={editForm.address} onChange={(e) => setEditForm({ ...editForm, address: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">{t("Bank name")}</label>
            <input className={inputClass} value={editForm.bank_name} onChange={(e) => setEditForm({ ...editForm, bank_name: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <button type="submit" className="bg-indigo-800 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-indigo-900">
              {t("Save changes")}
            </button>
          </div>
        </form>

        <div className="bg-white border border-slate-200 rounded p-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-1">{t("Request a critical field change")}</h2>
          <p className="text-xs text-slate-500 mb-4">
            {t("Changes to legal name, PAN, GSTIN, bank details, email, or mobile require reviewer approval before they take effect.")}
          </p>
          <form onSubmit={handleRequestChange} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <ApplicationDateField />
            <div>
              <label className="block text-xs text-slate-500 mb-1">{t("Field")}</label>
              <select className={inputClass} value={changeField} onChange={(e) => setChangeField(e.target.value)}>
                {CRITICAL_FIELDS.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">{t("New value")}</label>
              <input className={inputClass} value={changeValue} onChange={(e) => setChangeValue(e.target.value)} required />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs text-slate-500 mb-1">{t("Reason")}</label>
              <input className={inputClass} value={changeReason} onChange={(e) => setChangeReason(e.target.value)} required />
            </div>
            <div className="sm:col-span-2">
              <button type="submit" className="bg-slate-800 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-900">
                {t("Submit change request")}
              </button>
            </div>
          </form>

          {changes.length > 0 && (
            <table className="w-full text-sm mt-5">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-200">
                  <th className="py-2">{t("Field")}</th>
                  <th className="py-2">{t("New value")}</th>
                  <th className="py-2">{t("Requested on")}</th>
                  <th className="py-2">{t("Status")}</th>
                  <th className="py-2">{t("Remarks")}</th>
                </tr>
              </thead>
              <tbody>
                {changes.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100">
                    <td className="py-2">{c.field_name}</td>
                    <td className="py-2">{c.new_value}</td>
                    <td className="py-2 text-slate-500">{c.server_date?.slice(0, 10)}</td>
                    <td className="py-2"><StatusChip status={c.status} /></td>
                    <td className="py-2 text-slate-500">{c.review_remarks || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

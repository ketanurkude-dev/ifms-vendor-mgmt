import { useEffect, useState } from "react";
import { del, downloadFile, get, post, postForm, viewFile } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";
import ApplicationDateField from "./ApplicationDateField";
import { StatusChip } from "./StatusChip";

const DOC_TYPES = [
  "PAN card",
  "GSTIN registration certificate",
  "Company registration certificate",
  "Cancelled cheque / bank proof",
  "Other supporting document",
];

function OtpVerifyBox({ label, verified, onSend, onVerify }) {
  const { t } = useLanguage();
  const [sent, setSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSend() {
    setError("");
    const res = await onSend();
    setMessage(res.message);
    setSent(true);
  }

  async function handleVerify(e) {
    e.preventDefault();
    setError("");
    try {
      await onVerify(otp);
      setMessage(t("Verified successfully."));
    } catch (err) {
      setError(err.response?.data?.detail || t("Verification failed"));
    }
  }

  if (verified) {
    return (
      <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
        {label} {t("verified")}
      </div>
    );
  }

  return (
    <div className="border border-slate-200 rounded p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-700">{label} {t("not verified")}</span>
        <button type="button" onClick={handleSend} className="text-xs text-indigo-700 hover:text-indigo-900 font-medium">
          {sent ? t("Resend OTP") : t("Send OTP")}
        </button>
      </div>
      {message && <p className="text-xs text-slate-500 mb-2">{message}</p>}
      {sent && (
        <form onSubmit={handleVerify} className="flex items-center gap-2">
          <input
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            className="border border-slate-300 rounded-md px-3 py-1.5 text-sm tracking-widest w-32"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
          />
          <button type="submit" className="text-sm bg-indigo-800 text-white rounded-md px-3 py-1.5 hover:bg-indigo-900">
            {t("Verify")}
          </button>
        </form>
      )}
      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
    </div>
  );
}

export default function Documents() {
  const { t } = useLanguage();
  const [vendor, setVendor] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [file, setFile] = useState(null);
  const [expiryDate, setExpiryDate] = useState("");
  const [error, setError] = useState("");
  const [submitMessage, setSubmitMessage] = useState("");

  function refresh() {
    get("/vendor/me").then(setVendor);
    get("/vendor/documents").then(setDocuments);
  }

  useEffect(refresh, []);

  async function handleUpload(e) {
    e.preventDefault();
    setError("");
    if (!file) {
      setError(t("Choose a file to upload"));
      return;
    }
    try {
      const formData = new FormData();
      formData.append("doc_type", docType);
      if (expiryDate) formData.append("expiry_date", expiryDate);
      formData.append("file", file);
      await postForm("/vendor/documents", formData);
      setFile(null);
      setExpiryDate("");
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || t("Upload failed"));
    }
  }

  async function handleDelete(id) {
    await del(`/vendor/documents/${id}`);
    refresh();
  }

  async function handleView(doc) {
    await viewFile(`/vendor/documents/${doc.id}/view`);
  }

  async function handleDownload(doc) {
    await downloadFile(`/vendor/documents/${doc.id}/download`, doc.file_name);
  }

  async function handleSubmitApplication() {
    setError("");
    setSubmitMessage("");
    try {
      await post("/vendor/submit-application");
      setSubmitMessage(t("Application submitted for review."));
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || t("Submission failed"));
    }
  }

  if (!vendor) {
    return <div className="min-h-screen flex items-center justify-center text-slate-600">{t("Loading...")}</div>;
  }

  const canSubmit = vendor.status === "Draft" || vendor.status === "Returned";

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="bg-white border border-slate-200 rounded p-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-lg font-semibold text-slate-800">{t("Registration status")}</h1>
            <StatusChip status={vendor.status} />
          </div>
          <p className="text-xs text-slate-400 mb-4">{t("Application reference")}: {vendor.application_reference}</p>

          {canSubmit && (
            <div className="max-w-xs mb-4">
              <ApplicationDateField />
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
            <OtpVerifyBox
              label={t("Email")}
              verified={vendor.email_verified}
              onSend={() => post("/vendor/send-email-otp")}
              onVerify={async (otp) => {
                await post("/vendor/verify-email-otp", { otp });
                refresh();
              }}
            />
            <OtpVerifyBox
              label={t("Mobile")}
              verified={vendor.mobile_verified}
              onSend={() => post("/vendor/send-mobile-otp")}
              onVerify={async (otp) => {
                await post("/vendor/verify-mobile-otp", { otp });
                refresh();
              }}
            />
          </div>

          {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 mb-3">{error}</p>}
          {submitMessage && (
            <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2 mb-3">
              {submitMessage}
            </p>
          )}

          {canSubmit && (
            <button
              onClick={handleSubmitApplication}
              className="bg-indigo-800 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-indigo-900"
            >
              {t("Submit application for review")}
            </button>
          )}
          {!canSubmit && vendor.status === "Submitted" && (
            <p className="text-sm text-slate-500">{t("Your application is with the reviewer.")}</p>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">{t("Documents")}</h2>

          {canSubmit && (
            <form onSubmit={handleUpload} className="flex flex-wrap items-end gap-3 mb-5">
              <div>
                <label className="block text-xs text-slate-500 mb-1">{t("Document type")}</label>
                <select
                  className="border border-slate-300 rounded-md px-3 py-2 text-sm"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                >
                  {DOC_TYPES.map((dt) => (
                    <option key={dt} value={dt}>{t(dt)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">{t("File (PDF, JPG, PNG)")}</label>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  className="border border-slate-300 rounded-md px-3 py-1.5 text-sm"
                  onChange={(e) => setFile(e.target.files[0] || null)}
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">{t("Expiry date (optional)")}</label>
                <input
                  type="date"
                  className="border border-slate-300 rounded-md px-3 py-2 text-sm"
                  value={expiryDate}
                  onChange={(e) => setExpiryDate(e.target.value)}
                />
              </div>
              <button type="submit" className="bg-slate-800 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-900">
                {t("Upload")}
              </button>
            </form>
          )}

          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-200">
                <th className="py-2">{t("Document type")}</th>
                <th className="py-2">{t("File name")}</th>
                <th className="py-2">{t("Uploaded on")}</th>
                <th className="py-2">{t("Version")}</th>
                <th className="py-2">{t("Expiry")}</th>
                <th className="py-2">{t("Verification")}</th>
                <th className="py-2">{t("Remarks")}</th>
                <th className="py-2"></th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b border-slate-100">
                  <td className="py-2">{t(doc.doc_type)}</td>
                  <td className="py-2">{doc.file_name}</td>
                  <td className="py-2 text-slate-500">{doc.server_date?.slice(0, 10)}</td>
                  <td className="py-2">v{doc.version}</td>
                  <td className="py-2">{doc.expiry_date || "-"}</td>
                  <td className="py-2"><StatusChip status={doc.verification_status} /></td>
                  <td className="py-2 text-slate-500">{doc.remarks || "-"}</td>
                  <td className="py-2">
                    <div className="flex gap-2">
                      {doc.has_file && (
                        <button onClick={() => handleView(doc)} className="text-xs text-indigo-700 hover:text-indigo-900">
                          {t("View")}
                        </button>
                      )}
                      {doc.has_file && (
                        <button onClick={() => handleDownload(doc)} className="text-xs text-indigo-700 hover:text-indigo-900">
                          {t("Download")}
                        </button>
                      )}
                      {canSubmit && (
                        <button onClick={() => handleDelete(doc.id)} className="text-xs text-red-600 hover:text-red-800">
                          {t("Delete")}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {documents.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-4 text-center text-slate-400">{t("No documents uploaded yet")}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  );
}

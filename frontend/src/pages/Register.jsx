import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { post } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AuthLayout from "./AuthLayout";

const emptyForm = {
  vendor_type: "Supplier",
  legal_name: "",
  trade_name: "",
  contact_person_name: "",
  email: "",
  mobile: "",
  address: "",
  pan_number: "",
  gstin_number: "",
  bank_account_number: "",
  bank_ifsc: "",
  bank_name: "",
  password: "",
  role: "vendor",
};

export default function Register() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const errorRef = useRef(null);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await post("/auth/register", form);
      navigate("/login", { state: { applicationReference: data.application_reference } });
    } catch (err) {
      setError(err.response?.data?.detail || t("Registration failed"));
      errorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "w-full border border-slate-300 rounded-md px-3.5 py-2.5 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600";
  const labelClass = "block text-sm font-medium text-slate-700 mb-1.5";

  return (
    <AuthLayout title={t("Create account")} subtitle={t("Register your company as a vendor")}>
      <form onSubmit={handleSubmit}>
        {error && (
          <div
            ref={errorRef}
            className="mb-5 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2 flex items-start gap-2"
          >
            <span aria-hidden="true">⚠</span>
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          <div>
            <label className={labelClass}>{t("Application date")}</label>
            <input
              type="text"
              value={new Date().toISOString().slice(0, 10)}
              readOnly
              className={`${inputClass} bg-slate-50 text-slate-500 cursor-not-allowed`}
            />
          </div>
          <div>
            <label className={labelClass} htmlFor="vendor_type">{t("Vendor type")}</label>
            <select id="vendor_type" name="vendor_type" className={inputClass} value={form.vendor_type} onChange={handleChange}>
              <option value="Supplier">{t("Supplier")}</option>
              <option value="Contractor">{t("Contractor")}</option>
              <option value="Consultant">{t("Consultant")}</option>
              <option value="Service Provider">{t("Service Provider")}</option>
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="trade_name">{t("Trade name (optional)")}</label>
            <input id="trade_name" name="trade_name" className={inputClass} value={form.trade_name} onChange={handleChange} />
          </div>
          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="legal_name">{t("Legal name")}</label>
            <input id="legal_name" name="legal_name" className={inputClass} value={form.legal_name} onChange={handleChange} required />
          </div>
          <div>
            <label className={labelClass} htmlFor="contact_person_name">{t("Contact person")}</label>
            <input id="contact_person_name" name="contact_person_name" className={inputClass} value={form.contact_person_name} onChange={handleChange} required />
          </div>
          <div>
            <label className={labelClass} htmlFor="email">{t("Email")}</label>
            <input id="email" name="email" type="email" className={inputClass} value={form.email} onChange={handleChange} required />
          </div>
          <div>
            <label className={labelClass} htmlFor="mobile">{t("Mobile")}</label>
            <input id="mobile" name="mobile" className={inputClass} value={form.mobile} onChange={handleChange} required />
          </div>
          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="address">{t("Registered address")}</label>
            <input id="address" name="address" className={inputClass} value={form.address} onChange={handleChange} required />
          </div>
          <div>
            <label className={labelClass} htmlFor="pan_number">{t("PAN number")}</label>
            <input id="pan_number" name="pan_number" placeholder="ABCDE1234F" maxLength={10} className={inputClass} value={form.pan_number} onChange={handleChange} required />
          </div>
          <div>
            <label className={labelClass} htmlFor="gstin_number">{t("GSTIN")}</label>
            <input id="gstin_number" name="gstin_number" placeholder="07ABCDE1234F1Z5" maxLength={15} className={inputClass} value={form.gstin_number} onChange={handleChange} required />
          </div>
          <div>
            <label className={labelClass} htmlFor="bank_account_number">{t("Bank account number")}</label>
            <input id="bank_account_number" name="bank_account_number" className={inputClass} value={form.bank_account_number} onChange={handleChange} required />
          </div>
          <div>
            <label className={labelClass} htmlFor="bank_ifsc">{t("Bank IFSC")}</label>
            <input id="bank_ifsc" name="bank_ifsc" className={inputClass} value={form.bank_ifsc} onChange={handleChange} required />
          </div>
          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="bank_name">{t("Bank name")}</label>
            <input id="bank_name" name="bank_name" className={inputClass} value={form.bank_name} onChange={handleChange} required />
          </div>
          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="password">{t("Password")}</label>
            <input id="password" name="password" type="password" className={inputClass} value={form.password} onChange={handleChange} required minLength={6} />
          </div>
          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="role">{t("Role (for demo/testing a reviewer account)")}</label>
            <select id="role" name="role" className={inputClass} value={form.role} onChange={handleChange}>
              <option value="vendor">{t("Vendor")}</option>
              <option value="reviewer">{t("Reviewer")}</option>
            </select>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-800 text-white rounded-md py-2.5 font-medium hover:bg-indigo-900 transition-colors disabled:opacity-60"
        >
          {loading ? t("Registering...") : t("Register")}
        </button>

        <p className="text-sm text-slate-500 mt-6 text-center">
          {t("Already registered?")}{" "}
          <Link to="/login" className="text-indigo-800 font-medium hover:text-indigo-900">
            {t("Sign in")}
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}

import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { post } from "../api/apiService";
import { useCurrentVendor } from "../api/useCurrentVendor";
import { useLanguage } from "../i18n/LanguageContext";
import {
  ApproverIcon,
  AuditIcon,
  ContractIcon,
  DashboardIcon,
  DocumentIcon,
  InvoiceIcon,
  NotificationIcon,
  PaymentIcon,
  ProfileIcon,
  ReportIcon,
} from "./Icons";

const navItems = [
  { to: "/dashboard", label: "Dashboard", Icon: DashboardIcon },
  { to: "/profile", label: "Profile", Icon: ProfileIcon },
  { to: "/documents", label: "Registration & documents", Icon: DocumentIcon },
  { to: "/contracts", label: "Contracts", Icon: ContractIcon },
  { to: "/invoices", label: "Invoices", Icon: InvoiceIcon },
  { to: "/payments", label: "Payments", Icon: PaymentIcon },
  { to: "/notifications", label: "Notifications", Icon: NotificationIcon },
  { to: "/reports", label: "Reports", Icon: ReportIcon },
];

// Shared header + left sidebar nav for every page after login.
export default function AppLayout({ children }) {
  const navigate = useNavigate();
  const vendor = useCurrentVendor();
  const isReviewer = vendor && vendor.role === "reviewer";
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const { language, setLanguage, syncWithAccount, t } = useLanguage();

  // Once we know the vendor's saved preference, adopt it (per FR-VEP-011
  // the choice follows the account, not just the browser).
  useEffect(() => {
    if (vendor?.preferred_language) {
      syncWithAccount(vendor.preferred_language);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vendor?.preferred_language]);

  async function handleLogout() {
    try {
      await post("/auth/logout");
    } catch {
      // best-effort audit log entry -- logging out proceeds either way
    }
    localStorage.removeItem("access_token");
    navigate("/login");
  }

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-md ${
      isActive ? "bg-indigo-800 text-white" : "text-slate-600 hover:bg-slate-100"
    }`;

  const approverLinkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-md ${
      isActive ? "bg-amber-600 text-white" : "text-amber-700 hover:bg-amber-50"
    }`;

  // Reviewers don't hold contracts/invoices themselves, so keep their
  // sidebar focused on the workbench and their own account pages.
  const visibleNavItems = isReviewer
    ? navItems.filter((item) => ["/dashboard", "/profile", "/notifications"].includes(item.to))
    : navItems;

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      <header className="bg-indigo-900 text-white shrink-0">
        <div className="px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarVisible(!sidebarVisible)}
              className="mr-1 p-1.5 rounded hover:bg-white/10"
              aria-label={t("Toggle sidebar")}
              title={t("Toggle sidebar")}
            >
              <div className="w-5 h-0.5 bg-white mb-1" />
              <div className="w-5 h-0.5 bg-white mb-1" />
              <div className="w-5 h-0.5 bg-white" />
            </button>
            <div className="w-7 h-7 rounded bg-white/10 border border-white/20 flex items-center justify-center text-xs font-semibold">
              VP
            </div>
            <span className="font-semibold text-sm">{t("Vendor Portal")}</span>
            {vendor && (
              <>
                <span className="text-sm text-white/90 ml-3 hidden sm:inline">{vendor.company_name}</span>
                <span className="text-xs text-indigo-100/70 border border-white/20 rounded px-2 py-0.5 ml-2">
                  {t(vendor.role)}
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex border border-white/30 rounded overflow-hidden text-xs font-medium">
              <button
                onClick={() => setLanguage("en")}
                className={`px-2.5 py-1 ${language === "en" ? "bg-white text-indigo-900" : "hover:bg-white/10"}`}
              >
                EN
              </button>
              <button
                onClick={() => setLanguage("hi")}
                className={`px-2.5 py-1 ${language === "hi" ? "bg-white text-indigo-900" : "hover:bg-white/10"}`}
              >
                हिं
              </button>
            </div>
            <button
              onClick={handleLogout}
              className="text-sm border border-white/30 hover:bg-white/10 px-3 py-1.5 rounded"
            >
              {t("Logout")}
            </button>
          </div>
        </div>
        <div className="h-1 bg-amber-500" />
      </header>

      <div className="flex flex-1 min-h-0">
        {sidebarVisible && (
          <aside className="w-56 shrink-0 bg-white border-r border-slate-200 h-full overflow-y-auto p-3">
            <nav className="space-y-1">
              {visibleNavItems.map(({ to, label, Icon }) => (
                <NavLink key={to} to={to} className={linkClass}>
                  <Icon style={{ width: 18, height: 18 }} className="shrink-0" />
                  {t(label)}
                </NavLink>
              ))}
              {isReviewer && (
                <>
                  <NavLink to="/approver" className={approverLinkClass}>
                    <ApproverIcon style={{ width: 18, height: 18 }} className="shrink-0" />
                    {t("Approver")}
                  </NavLink>
                  <NavLink to="/audit-log" className={approverLinkClass}>
                    <AuditIcon style={{ width: 18, height: 18 }} className="shrink-0" />
                    {t("Audit log")}
                  </NavLink>
                  <NavLink to="/reports" className={approverLinkClass}>
                    <ReportIcon style={{ width: 18, height: 18 }} className="shrink-0" />
                    {t("Reports")}
                  </NavLink>
                </>
              )}
            </nav>
          </aside>
        )}

        <main className="flex-1 min-w-0 h-full overflow-y-auto px-4 sm:px-6 py-6">
          <div className="max-w-5xl mx-auto">{children}</div>
        </main>
      </div>

      <footer className="shrink-0 bg-white border-t border-slate-200 px-4 sm:px-6 py-2 flex items-center justify-end gap-2 text-xs text-slate-400">
        <span>{t("Developed by")}</span>
        <img src="/virtualgalaxy-logo.webp" alt="Virtual Galaxy" className="h-5" />
      </footer>
    </div>
  );
}

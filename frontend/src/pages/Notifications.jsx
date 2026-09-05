import { useEffect, useState } from "react";
import { get, post } from "../api/apiService";
import { useLanguage } from "../i18n/LanguageContext";
import AppLayout from "./AppLayout";

export default function Notifications() {
  const { t } = useLanguage();
  const [notifications, setNotifications] = useState(null);

  function refresh() {
    get("/notifications").then(setNotifications);
  }

  useEffect(refresh, []);

  async function handleMarkRead(id) {
    await post(`/notifications/${id}/read`);
    refresh();
  }

  if (!notifications) {
    return <div className="min-h-screen flex items-center justify-center text-slate-600">{t("Loading...")}</div>;
  }

  return (
    <AppLayout>
      <div className="bg-white border border-slate-200 rounded p-6">
        <h1 className="text-lg font-semibold text-slate-800 mb-4">{t("Notifications")}</h1>
        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`border rounded p-3 ${n.is_read ? "border-slate-200 bg-white" : "border-indigo-200 bg-indigo-50"}`}
            >
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-sm font-medium text-slate-800">{n.title}</h3>
                {!n.is_read && (
                  <button
                    onClick={() => handleMarkRead(n.id)}
                    className="text-xs text-indigo-700 hover:text-indigo-900 font-medium"
                  >
                    {t("Mark read")}
                  </button>
                )}
              </div>
              <p className="text-sm text-slate-600">{n.message}</p>
              <p className="text-xs text-slate-400 mt-1">{n.category}</p>
            </div>
          ))}
          {notifications.length === 0 && <p className="text-slate-400 text-center py-6">{t("No notifications")}</p>}
        </div>
      </div>
    </AppLayout>
  );
}

import { Navigate, Route, Routes } from "react-router-dom";
import Login from "./pages/Login";
import Otp from "./pages/Otp";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Documents from "./pages/Documents";
import Contracts from "./pages/Contracts";
import Invoices from "./pages/Invoices";
import Payments from "./pages/Payments";
import Notifications from "./pages/Notifications";
import Reports from "./pages/Reports";
import AuditLog from "./pages/AuditLog";
import Approver from "./pages/Approver";

function RequireAuth({ children }) {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/login" replace />;
}

const protectedRoutes = [
  { path: "/dashboard", element: <Dashboard /> },
  { path: "/profile", element: <Profile /> },
  { path: "/documents", element: <Documents /> },
  { path: "/contracts", element: <Contracts /> },
  { path: "/invoices", element: <Invoices /> },
  { path: "/payments", element: <Payments /> },
  { path: "/notifications", element: <Notifications /> },
  { path: "/reports", element: <Reports /> },
  { path: "/audit-log", element: <AuditLog /> },
  { path: "/approver", element: <Approver /> },
];

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/otp" element={<Otp />} />
      <Route path="/register" element={<Register />} />
      {protectedRoutes.map(({ path, element }) => (
        <Route key={path} path={path} element={<RequireAuth>{element}</RequireAuth>} />
      ))}
    </Routes>
  );
}

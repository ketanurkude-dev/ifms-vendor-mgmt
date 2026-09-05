// Small set of hand-drawn outline icons (no icon library, no emoji).

const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  viewBox: "0 0 24 24",
};

export function DashboardIcon(props) {
  return (
    <svg {...base} {...props}>
      <rect x="3.5" y="3.5" width="7.5" height="7.5" rx="1.2" />
      <rect x="13" y="3.5" width="7.5" height="4.5" rx="1.2" />
      <rect x="13" y="10.5" width="7.5" height="10" rx="1.2" />
      <rect x="3.5" y="13.5" width="7.5" height="7" rx="1.2" />
    </svg>
  );
}

export function ProfileIcon(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="7.5" r="3.5" />
      <path d="M4.5 20c0-3.6 3.4-6 7.5-6s7.5 2.4 7.5 6" />
    </svg>
  );
}

export function DocumentIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M6.5 3.5h8l3 3v13a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1v-15a1 1 0 0 1 1-1z" />
      <path d="M14 3.5v3h3" />
      <path d="M8.5 12.5h7M8.5 15.5h7M8.5 9.5h4" />
    </svg>
  );
}

export function ContractIcon(props) {
  return (
    <svg {...base} {...props}>
      <rect x="4.5" y="3.5" width="15" height="17" rx="1.5" />
      <path d="M8 8h8M8 11h8M8 14h5" />
      <path d="M9 17.5l1.8 1.8L15 15" />
    </svg>
  );
}

export function InvoiceIcon(props) {
  return (
    <svg {...base} {...props}>
      <rect x="3.5" y="5.5" width="17" height="13" rx="1.5" />
      <circle cx="12" cy="12" r="2.6" />
      <path d="M3.5 9.5h1.5M19 9.5h1.5M3.5 14.5h1.5M19 14.5h1.5" />
    </svg>
  );
}

export function PaymentIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M4 10.5 12 4l8 6.5" />
      <path d="M5.5 10v9h13v-9" />
      <path d="M10 19v-5h4v5" />
    </svg>
  );
}

export function NotificationIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M6 9.5a6 6 0 0 1 12 0v4l1.5 2.5h-15L6 13.5z" />
      <path d="M9.5 18.5a2.5 2.5 0 0 0 5 0" />
    </svg>
  );
}

export function ApproverIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3.5 5 6v6c0 4.5 3 7.5 7 8.5 4-1 7-4 7-8.5V6z" />
      <path d="M9 12l2 2 4-4.5" />
    </svg>
  );
}

export function ReportIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M5 3.5h14v17H5z" />
      <path d="M8.5 13.5v4M12 10.5v7M15.5 7.5v10" />
    </svg>
  );
}

export function AuditIcon(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="M16.2 16.2 21 21" />
      <path d="M8.5 11h5M11 8.5v5" />
    </svg>
  );
}

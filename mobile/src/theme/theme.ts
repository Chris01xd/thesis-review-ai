export const colors = {
  primary: "#2563eb",
  secondary: "#0f172a",
  background: "#f8fafc",
  card: "#ffffff",
  text: "#111827",
  muted: "#64748b",
  success: "#16a34a",
  warning: "#d97706",
  danger: "#dc2626",
  border: "#e5e7eb"
};

export const severityColor = (severity: string) => {
  if (severity === "Crítico") return colors.danger;
  if (severity === "Mayor") return "#ea580c";
  if (severity === "Menor") return colors.warning;
  return colors.primary;
};

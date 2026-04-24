export function Alert({ kind, message }: { kind: "success" | "error"; message: string }) {
  if (!message) return null;
  const cls =
    kind === "success"
      ? "bg-[oklch(0.95_0.06_155)] text-[oklch(0.35_0.13_155)]"
      : "bg-[oklch(0.95_0.06_25)] text-[oklch(0.45_0.18_25)]";
  return (
    <div className={`rounded-md px-3 py-2 text-sm ${cls}`}>
      {message}
    </div>
  );
}

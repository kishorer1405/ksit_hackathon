import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { api } from "../lib/api";
import { Alert } from "../components/Alert";

export const Route = createFileRoute("/authority/login")({
  component: AuthorityLogin,
});

const DEPARTMENTS = ["fire", "water", "electricity", "road"] as const;

function AuthorityLogin() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ phone: "", password: "", department: "fire" });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string }>({ kind: "success", text: "" });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg({ kind: "success", text: "" });
    try {
      await api("/authority/login", { method: "POST", body: JSON.stringify(form) });
      localStorage.setItem("department", form.department);
      navigate({ to: "/authority/dashboard" });
    } catch (err: any) {
      setMsg({ kind: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-10 sm:py-16">
      <div className="crs-card">
        <h1 className="text-2xl font-bold">Authority login</h1>
        <p className="text-sm text-muted-foreground mt-1">Access your department's queue.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="crs-label">Phone</label>
            <input className="crs-input" required value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div>
            <label className="crs-label">Password</label>
            <input className="crs-input" type="password" required value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
          <div>
            <label className="crs-label">Department</label>
            <select className="crs-input" value={form.department}
              onChange={(e) => setForm({ ...form, department: e.target.value })}>
              {DEPARTMENTS.map((d) => (
                <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
              ))}
            </select>
          </div>
          <Alert kind={msg.kind} message={msg.text} />
          <button disabled={loading} className="crs-btn w-full">
            {loading ? "Logging in..." : "Login"}
          </button>
          <p className="text-sm text-center text-muted-foreground">
            New authority? <Link to="/authority/register" className="text-primary font-medium">Register</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

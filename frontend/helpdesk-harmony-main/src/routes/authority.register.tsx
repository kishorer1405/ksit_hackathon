import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { api } from "../lib/api";
import { Alert } from "../components/Alert";

export const Route = createFileRoute("/authority/register")({
  component: AuthorityRegister,
});

const DEPARTMENTS = ["fire", "water", "electricity", "road"] as const;

function AuthorityRegister() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    phone: "",
    department: "fire",
    password: "",
    confirm: "",
  });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string }>({ kind: "success", text: "" });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg({ kind: "success", text: "" });
    if (form.password !== form.confirm) {
      setMsg({ kind: "error", text: "Passwords do not match." });
      return;
    }
    setLoading(true);
    try {
      await api("/authority/register", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          phone: form.phone,
          department: form.department,
          password: form.password,
        }),
      });
      setMsg({ kind: "success", text: "Registered! Redirecting..." });
      setTimeout(() => navigate({ to: "/authority/login" }), 900);
    } catch (err: any) {
      setMsg({ kind: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-10 sm:py-16">
      <div className="crs-card">
        <h1 className="text-2xl font-bold">Authority registration</h1>
        <p className="text-sm text-muted-foreground mt-1">Join your department's response team.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="crs-label">Name</label>
            <input className="crs-input" required value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="crs-label">Phone</label>
            <input className="crs-input" required value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })} />
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
          <div>
            <label className="crs-label">Password</label>
            <input className="crs-input" type="password" required value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
          <div>
            <label className="crs-label">Confirm Password</label>
            <input className="crs-input" type="password" required value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })} />
          </div>
          <Alert kind={msg.kind} message={msg.text} />
          <button disabled={loading} className="crs-btn w-full">
            {loading ? "Registering..." : "Register"}
          </button>
          <p className="text-sm text-center text-muted-foreground">
            Already registered? <Link to="/authority/login" className="text-primary font-medium">Login</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { api } from "../lib/api";
import { Alert } from "../components/Alert";

export const Route = createFileRoute("/user/register")({
  component: UserRegister,
});

function UserRegister() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", phone: "", password: "", confirm: "" });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string }>({ kind: "success", text: "" });

  const update = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg({ kind: "success", text: "" });
    if (form.password !== form.confirm) {
      setMsg({ kind: "error", text: "Passwords do not match." });
      return;
    }
    setLoading(true);
    try {
      await api("/user/register", {
        method: "POST",
        body: JSON.stringify({ name: form.name, phone: form.phone, password: form.password }),
      });
      setMsg({ kind: "success", text: "Registered! Redirecting to login..." });
      setTimeout(() => navigate({ to: "/user/login" }), 900);
    } catch (err: any) {
      setMsg({ kind: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-10 sm:py-16">
      <div className="crs-card">
        <h1 className="text-2xl font-bold">Create your account</h1>
        <p className="text-sm text-muted-foreground mt-1">Register as a citizen to file complaints.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="crs-label">Full Name</label>
            <input className="crs-input" required value={form.name} onChange={update("name")} />
          </div>
          <div>
            <label className="crs-label">Phone Number</label>
            <input className="crs-input" required value={form.phone} onChange={update("phone")} />
          </div>
          <div>
            <label className="crs-label">Password</label>
            <input className="crs-input" type="password" required value={form.password} onChange={update("password")} />
          </div>
          <div>
            <label className="crs-label">Confirm Password</label>
            <input className="crs-input" type="password" required value={form.confirm} onChange={update("confirm")} />
          </div>
          <Alert kind={msg.kind} message={msg.text} />
          <button type="submit" disabled={loading} className="crs-btn w-full">
            {loading ? "Registering..." : "Register"}
          </button>
          <p className="text-sm text-center text-muted-foreground">
            Already have an account? <Link to="/user/login" className="text-primary font-medium">Login</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

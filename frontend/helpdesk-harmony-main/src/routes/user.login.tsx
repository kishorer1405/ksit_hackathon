import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { api } from "../lib/api";
import { Alert } from "../components/Alert";

export const Route = createFileRoute("/user/login")({
  component: UserLogin,
});

function UserLogin() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ phone: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string }>({ kind: "success", text: "" });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg({ kind: "success", text: "" });
    try {
      const data = await api<{ user_id?: string; id?: string; user?: { id?: string | number } }>("/user/login", {
        method: "POST",
        body: JSON.stringify(form),
      });
      const id = data?.user_id ?? data?.id ?? data?.user?.id;
      if (!id) throw new Error("No user_id returned from server.");
      localStorage.setItem("user_id", String(id));
      navigate({ to: "/user/dashboard" });
    } catch (err: any) {
      setMsg({ kind: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-10 sm:py-16">
      <div className="crs-card">
        <h1 className="text-2xl font-bold">Welcome back</h1>
        <p className="text-sm text-muted-foreground mt-1">Login to manage your complaints.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="crs-label">Phone Number</label>
            <input className="crs-input" required value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div>
            <label className="crs-label">Password</label>
            <input className="crs-input" type="password" required value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
          <Alert kind={msg.kind} message={msg.text} />
          <button type="submit" disabled={loading} className="crs-btn w-full">
            {loading ? "Logging in..." : "Login"}
          </button>
          <p className="text-sm text-center text-muted-foreground">
            New here? <Link to="/user/register" className="text-primary font-medium">Register</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

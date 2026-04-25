import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, useCallback } from "react";
import { api, fileToBase64 } from "../lib/api";
import { Alert } from "../components/Alert";
import { LocationHeatmap } from "../components/LocationHeatmap";

export const Route = createFileRoute("/user/dashboard")({
  component: UserDashboard,
});

type Complaint = {
  id?: string;
  _id?: string;
  text: string;
  category?: string;
  department?: string;
  priority?: string;
  status?: string;
  response?: string;
  location?: string;
  created_at?: string;
};

const statusClass = (s?: string) => {
  const v = (s || "").toLowerCase();
  if (v.includes("complete")) return "crs-badge crs-badge-completed";
  if (v.includes("process")) return "crs-badge crs-badge-process";
  if (v.includes("reject")) return "crs-badge crs-badge-rejected";
  return "crs-badge crs-badge-pending";
};

function UserDashboard() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [location, setLocation] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitMsg, setSubmitMsg] = useState<{ kind: "success" | "error"; text: string }>({ kind: "success", text: "" });
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [listError, setListError] = useState("");

  useEffect(() => {
    const id = localStorage.getItem("user_id");
    if (!id) {
      navigate({ to: "/user/login" });
      return;
    }
    setUserId(id);
  }, [navigate]);

  const fetchList = useCallback(async (id: string) => {
    setLoadingList(true);
    setListError("");
    try {
      const data = await api<Complaint[] | { complaints: Complaint[] }>(`/user/complaints/${id}`);
      const list = Array.isArray(data) ? data : data?.complaints ?? [];
      setComplaints(list);
    } catch (err: any) {
      setListError(err.message);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    if (userId) fetchList(userId);
  }, [userId, fetchList]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId) return;
    setSubmitting(true);
    setSubmitMsg({ kind: "success", text: "" });
    try {
      const image = imageFile ? await fileToBase64(imageFile) : null;
      await api("/complaint", {
        method: "POST",
        body: JSON.stringify({ user_id: userId, text, location, image }),
      });
      setSubmitMsg({ kind: "success", text: "Complaint submitted successfully." });
      setText("");
      setLocation("");
      setImageFile(null);
      fetchList(userId);
    } catch (err: any) {
      setSubmitMsg({ kind: "error", text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 grid lg:grid-cols-5 gap-6">
      <section className="lg:col-span-2">
        <div className="crs-card">
          <h2 className="text-xl font-bold">Submit a complaint</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Describe the issue. Our AI will route it to the right department.
          </p>
          <form onSubmit={submit} className="mt-5 space-y-4">
            <div>
              <label className="crs-label">Description</label>
              <textarea
                required
                rows={5}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="What's the issue?"
                className="crs-input resize-y"
              />
            </div>
            <div>
              <label className="crs-label">Location / Address</label>
              <input className="crs-input" required value={location}
                onChange={(e) => setLocation(e.target.value)} placeholder="e.g. 5th Ave, Block B" />
            </div>
            <div>
              <label className="crs-label">Image (optional)</label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
                className="crs-input file:mr-3 file:rounded-md file:border-0 file:bg-accent file:px-3 file:py-1 file:text-sm file:text-accent-foreground"
              />
            </div>
            <Alert kind={submitMsg.kind} message={submitMsg.text} />
            <button disabled={submitting} className="crs-btn w-full">
              {submitting ? "Submitting..." : "Submit Complaint"}
            </button>
          </form>
        </div>
      </section>

      <section className="lg:col-span-3">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-bold">Your complaints</h2>
          <button
            onClick={() => userId && fetchList(userId)}
            className="crs-btn crs-btn-ghost text-sm"
            disabled={loadingList}
          >
            {loadingList ? "Loading..." : "Refresh"}
          </button>
        </div>

        {listError && <Alert kind="error" message={listError} />}
        {!loadingList && complaints.length === 0 && !listError && (
          <div className="crs-card text-center text-muted-foreground">
            No complaints yet. Submit your first one!
          </div>
        )}
        <div className="space-y-3">
          {complaints.map((c, i) => (
            <article key={c.id ?? c._id ?? i} className="crs-card">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium leading-relaxed">{c.text}</p>
                <span className={statusClass(c.status)}>{c.status || "Pending"}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                {c.category && <span className="crs-badge">Category: {c.category}</span>}
                {c.department && <span className="crs-badge">Dept: {c.department}</span>}
                {c.priority && <span className="crs-badge">Priority: {c.priority}</span>}
              </div>
              {c.response && (
                <p className="mt-3 text-sm text-muted-foreground border-l-2 border-primary pl-3">
                  <span className="font-medium text-foreground">Response:</span> {c.response}
                </p>
              )}
            </article>
          ))}
        </div>

        <div className="mt-6">
          <LocationHeatmap title="Campus Complaint Heatmap" />
        </div>
      </section>
    </div>
  );
}

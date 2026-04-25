import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: Home,
});

function Home() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-12 sm:py-20">
      <section className="text-center">
        <span className="crs-badge mb-4">AI-Powered</span>
        <h1 className="text-3xl sm:text-5xl font-bold tracking-tight">
          Complaint Resolution System
        </h1>
        <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
          File a complaint in seconds. Our AI categorizes, prioritizes, and routes it
          to the right department — fire, water, electricity, roads, or garbage.
        </p>
      </section>

      <section className="mt-12 grid sm:grid-cols-2 gap-5">
        <div className="crs-card">
          <h2 className="text-lg font-semibold">For Citizens</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Register, submit complaints with location & photo, track status in real time.
          </p>
          <div className="mt-4 flex gap-2 flex-wrap">
            <Link to="/user/login" className="crs-btn">Login</Link>
            <Link to="/user/register" className="crs-btn crs-btn-ghost">Register</Link>
          </div>
        </div>
        <div className="crs-card">
          <h2 className="text-lg font-semibold">For Authorities</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Access the queue for your department and update statuses with one click.
          </p>
          <div className="mt-4 flex gap-2 flex-wrap">
            <Link to="/authority/login" className="crs-btn">Login</Link>
            <Link to="/authority/register" className="crs-btn crs-btn-ghost">Register</Link>
          </div>
        </div>
      </section>

      <section className="mt-12 grid sm:grid-cols-3 gap-5">
        {[
          { t: "Submit", d: "Describe the issue and add a location or image." },
          { t: "AI Routes", d: "Categorized and assigned to the right team." },
          { t: "Track", d: "Watch status move from pending to completed." },
        ].map((s, i) => (
          <div key={i} className="crs-card">
            <div className="text-primary font-semibold">Step {i + 1}</div>
            <div className="font-medium mt-1">{s.t}</div>
            <p className="text-sm text-muted-foreground mt-1">{s.d}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

import { Link, useNavigate, useRouterState } from "@tanstack/react-router";

export function Navbar() {
  const navigate = useNavigate();
  const { location } = useRouterState();
  const userId = typeof window !== "undefined" ? localStorage.getItem("user_id") : null;
  const department = typeof window !== "undefined" ? localStorage.getItem("department") : null;

  const logout = () => {
    localStorage.removeItem("user_id");
    localStorage.removeItem("department");
    navigate({ to: "/" });
  };

  const linkCls = (path: string) =>
    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      location.pathname === path
        ? "bg-accent text-accent-foreground"
        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
    }`;

  return (
    <header className="sticky top-0 z-30 bg-card/90 backdrop-blur border-b border-border">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between gap-3">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <span className="w-7 h-7 rounded-md bg-primary text-primary-foreground inline-flex items-center justify-center text-sm">
            CR
          </span>
          <span className="hidden sm:inline">Complaint Resolver</span>
        </Link>
        <nav className="flex items-center gap-1 flex-wrap">
          {!userId && !department && (
            <>
              <Link to="/user/login" className={linkCls("/user/login")}>User Login</Link>
              <Link to="/user/register" className={linkCls("/user/register")}>User Register</Link>
              <Link to="/authority/login" className={linkCls("/authority/login")}>Authority Login</Link>
              <Link to="/authority/register" className={linkCls("/authority/register")}>Authority Register</Link>
            </>
          )}
          {userId && (
            <>
              <Link to="/user/dashboard" className={linkCls("/user/dashboard")}>Dashboard</Link>
              <button onClick={logout} className="crs-btn crs-btn-ghost text-sm">Logout</button>
            </>
          )}
          {department && (
            <>
              <Link to="/authority/dashboard" className={linkCls("/authority/dashboard")}>Dashboard</Link>
              <button onClick={logout} className="crs-btn crs-btn-ghost text-sm">Logout</button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

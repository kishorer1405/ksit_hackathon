import { lazy, Suspense, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { HeatPoint } from "./BengaluruGeoMap";

type Summary = {
  total_complaints: number;
  top_areas: Array<{ area: string; count: number }>;
  status_breakdown: Array<{ status: string; count: number }>;
};

type Props = {
  title: string;
  department?: string;
  userId?: string | null;
};

const BengaluruGeoMap = lazy(() => import("./BengaluruGeoMap").then((module) => ({ default: module.BengaluruGeoMap })));

export function LocationHeatmap({ title, department, userId }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [points, setPoints] = useState<HeatPoint[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams();
        if (department) params.set("department", department);
        if (userId) params.set("user_id", userId);

        const query = params.toString() ? `?${params.toString()}` : "";
        const heatmapData = await api<{ points: HeatPoint[] }>(`/insights/heatmap${query}`);
        const summaryData = await api<Summary>(`/insights/summary${query}`);

        setPoints(heatmapData.points || []);
        setSummary(summaryData);
      } catch (err: any) {
        setError(err.message || "Failed to load heatmap insights");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [department, userId]);

  return (
    <Suspense fallback={<section className="crs-card"><p className="text-sm text-muted-foreground">Loading Bengaluru map...</p></section>}>
      <BengaluruGeoMap title={title} points={points} summary={summary} />
      {loading && <p className="mt-3 text-sm text-muted-foreground">Refreshing map data...</p>}
      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
    </Suspense>
  );
}

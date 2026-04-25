import { useEffect } from "react";
import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";

export type HeatPoint = {
  area: string;
  lat: number;
  lng: number;
  weight: number;
};

type Summary = {
  total_complaints: number;
  top_areas: Array<{ area: string; count: number }>;
  status_breakdown: Array<{ status: string; count: number }>;
};

type Props = {
  title: string;
  points: HeatPoint[];
  summary: Summary | null;
};

function pointColor(weight: number, maxWeight: number): string {
  if (maxWeight <= 0) return "#89bff8";
  const ratio = weight / maxWeight;
  if (ratio >= 0.85) return "#ff0000";
  if (ratio >= 0.65) return "#e1ff01";
  if (ratio >= 0.45) return "#00ff37";
  if (ratio >= 0.25) return "#81e1e1";
  return "#3b82f6";
}

function FitBounds({ points }: { points: HeatPoint[] }) {
  const map = useMap();

  useEffect(() => {
    if (!points.length) return;
    const bounds: LatLngBoundsExpression = points.map((point) => [point.lat, point.lng]);
    map.fitBounds(bounds, { padding: [30, 30] });
  }, [map, points]);

  return null;
}

export function BengaluruGeoMap({ title, points, summary }: Props) {
  const center: [number, number] = [12.9716, 77.5946];
  const maxWeight = points.reduce((max, point) => (point.weight > max ? point.weight : max), 0);

  return (
    <section className="crs-card">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-lg font-semibold">{title}</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Bengaluru locality heatmap from complaint density.
          </p>
        </div>
        {summary && <span className="crs-badge">Total: {summary.total_complaints}</span>}
      </div>

      {points.length === 0 ? (
        <div className="mt-4 rounded-md border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
          No Bengaluru complaint data available yet.
        </div>
      ) : (
        <div className="mt-4 overflow-hidden rounded-xl border border-border shadow-sm">
          <div style={{ height: 440, width: "100%" }}>
            <MapContainer center={center} zoom={11.5} scrollWheelZoom className="h-full w-full">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <FitBounds points={points} />
              {points.map((point) => {
                const radius = 14 + point.weight * 2.3;
                const fillColor = pointColor(point.weight, maxWeight);
                return (
                  <CircleMarker
                    key={`${point.area}-${point.lat}-${point.lng}`}
                    center={[point.lat, point.lng]}
                    radius={radius}
                    pathOptions={{
                      color: fillColor,
                      fillColor,
                      fillOpacity: 0.28,
                      weight: 2,
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
                      {point.area}: {point.weight} complaints
                    </Tooltip>
                    <Popup>
                      <div className="space-y-1">
                        <div className="font-semibold">{point.area}</div>
                        <div className="text-sm">Complaints: {point.weight}</div>
                        <div className="text-xs text-muted-foreground">
                          Lat: {point.lat.toFixed(4)}, Lng: {point.lng.toFixed(4)}
                        </div>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </MapContainer>
          </div>
        </div>
      )}

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div>
          <h4 className="text-sm font-semibold">Top Bengaluru Areas</h4>
          <div className="mt-2 space-y-2">
            {(summary?.top_areas || []).map((item) => (
              <div key={item.area} className="flex items-center justify-between text-sm rounded-md bg-muted/40 px-3 py-2">
                <span>{item.area}</span>
                <span className="font-semibold">{item.count}</span>
              </div>
            ))}
            {summary && summary.top_areas.length === 0 && (
              <p className="text-xs text-muted-foreground">No area statistics available.</p>
            )}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-semibold">Status Breakdown</h4>
          <div className="mt-2 space-y-2">
            {(summary?.status_breakdown || []).map((item) => (
              <div key={item.status} className="flex items-center justify-between text-sm rounded-md bg-muted/40 px-3 py-2">
                <span>{item.status}</span>
                <span className="font-semibold">{item.count}</span>
              </div>
            ))}
            {summary && summary.status_breakdown.length === 0 && (
              <p className="text-xs text-muted-foreground">No status statistics available.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

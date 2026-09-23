import { useMemo } from "react";
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, LinearScale, PointElement, LineElement, Tooltip, Legend } from "chart.js";

ChartJS.register(LinearScale, PointElement, LineElement, Tooltip, Legend);

const PALETTE = ["#4EE2C0", "#F2A65A", "#6FB1E0", "#C084FC", "#F87171", "#FBBF24"];

export default function DepthChart({ depthProfiles, selectedProfileId }) {
  const profilesToShow = useMemo(() => {
    if (!depthProfiles || depthProfiles.length === 0) return [];
    if (selectedProfileId) {
      const single = depthProfiles.find((p) => p.profile_id === selectedProfileId);
      return single ? [single] : depthProfiles.slice(0, 6);
    }
    return depthProfiles.slice(0, 6);
  }, [depthProfiles, selectedProfileId]);

  const hasData = profilesToShow.length > 0;

  const chartData = {
    datasets: profilesToShow.map((p, i) => ({
      label: `${p.platform_id} · ${p.date}`,
      data: p.levels.filter((l) => l.temperature != null).map((l) => ({ x: l.temperature, y: l.pressure })),
      borderColor: PALETTE[i % PALETTE.length],
      backgroundColor: PALETTE[i % PALETTE.length],
      tension: 0.25, pointRadius: 2, borderWidth: 2,
    })),
  };

  const options = {
    responsive: true, maintainAspectRatio: false, indexAxis: "y",
    scales: {
      y: { reverse: true, title: { display: true, text: "Pressure / depth (dbar)", color: "#7C97A8" }, ticks: { color: "#B9CBD6" }, grid: { color: "#1C3B52" } },
      x: { title: { display: true, text: "Temperature (°C)", color: "#7C97A8" }, ticks: { color: "#B9CBD6" }, grid: { color: "#1C3B52" } },
    },
    plugins: { legend: { labels: { color: "#E8F1F5", font: { family: "IBM Plex Mono", size: 10 } } } },
  };

  const hint = !hasData
    ? "Run a query to see temperature & salinity by depth."
    : selectedProfileId
    ? `Single profile — float ${profilesToShow[0].platform_id}, ${profilesToShow[0].date}`
    : `Showing ${profilesToShow.length} of ${depthProfiles.length} profile(s) — click a float on the map to inspect one.`;

  return (
    <div className="chart-wrap">
      <h2>Depth profile</h2>
      <div className="hint">{hint}</div>
      <div className="chart-canvas-wrap">
        {hasData ? <Line data={chartData} options={options} /> : <div className="empty-state">No profile data yet</div>}
      </div>
    </div>
  );
}

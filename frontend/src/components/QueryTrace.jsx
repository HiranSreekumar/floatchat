export default function QueryTrace({ intent, sql, rowCount }) {
  if (!intent) return null;
  return (
    <details className="trace">
      <summary>Query trace — parsed intent &amp; SQL</summary>
      <div className="trace-body">
        <div className="kv"><span className="k">location:</span> {intent.resolved_location_label}</div>
        <div className="kv"><span className="k">time window:</span> {intent.resolved_time_label}</div>
        <div className="kv"><span className="k">variable:</span> {intent.variable}</div>
        <div className="kv"><span className="k">metric:</span> {intent.metric}</div>
        <div className="kv"><span className="k">bounding box:</span> lon [{intent.lon_min}, {intent.lon_max}], lat [{intent.lat_min}, {intent.lat_max}]</div>
        <div className="kv"><span className="k">rows returned:</span> {rowCount}</div>
        {sql && <pre>{sql}</pre>}
      </div>
    </details>
  );
}

import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

function FitBounds({ locations }) {
  const map = useMap();
  useEffect(() => {
    if (!locations || locations.length === 0) return;
    const bounds = locations.map((l) => [l.lat, l.lon]);
    map.fitBounds(bounds, { padding: [30, 30], maxZoom: 9 });
  }, [locations, map]);
  return null;
}

export default function MapView({ locations, onSelectProfile }) {
  const hasLocations = locations && locations.length > 0;
  return (
    <div className="map-wrap">
      <MapContainer center={[15, 78]} zoom={5} style={{ width: "100%", height: "100%" }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap contributors'
          maxZoom={12}
        />
        {hasLocations && <FitBounds locations={locations} />}
        {locations.map((loc) => (
          <CircleMarker
            key={loc.profile_id}
            center={[loc.lat, loc.lon]}
            radius={6}
            pathOptions={{ color: "#4EE2C0", weight: 1.5, fillColor: "#4EE2C0", fillOpacity: 0.55 }}
            eventHandlers={{ click: () => onSelectProfile(loc.profile_id) }}
          >
            <Popup>
              <b>Float {loc.platform_id}</b><br />{loc.date}<br />{loc.lat.toFixed(2)}, {loc.lon.toFixed(2)}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}

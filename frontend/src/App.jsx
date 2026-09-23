import { useEffect, useState } from "react";
import ChatPanel from "./components/ChatPanel";
import MapView from "./components/MapView";
import DepthChart from "./components/DepthChart";
import { checkHealth, BACKEND_URL } from "./api";

export default function App() {
  const [locations, setLocations] = useState([]);
  const [depthProfiles, setDepthProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState(null);
  const [health, setHealth] = useState({ status: "connecting" });

  useEffect(() => {
    checkHealth().then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);

  function handleResult(data) {
    setLocations(data.profile_locations || []);
    setDepthProfiles(data.depth_profiles || []);
    setSelectedProfileId(null);
  }

  const isOnline = health.status === "ok";
  const label = isOnline
    ? `${BACKEND_URL.replace(/^https?:\/\//, "")} · ${health.profiles} profiles loaded`
    : `${BACKEND_URL.replace(/^https?:\/\//, "")} · unreachable`;

  return (
    <div className="app">
      <header>
        <div className="fathom-line"><div className="tick"></div><div className="tick"></div><div className="tick"></div><div className="tick"></div></div>
        <h1>FloatChat</h1>
        <div className="sub">
          <span className={`dot ${isOnline ? "" : "offline"}`}></span>
          ARGO ocean float network &middot; India<br />{label}
        </div>
      </header>
      <div className="layout">
        <ChatPanel onResult={handleResult} />
        <div className="right-pane">
          <MapView locations={locations} onSelectProfile={setSelectedProfileId} />
          <DepthChart depthProfiles={depthProfiles} selectedProfileId={selectedProfileId} />
        </div>
      </div>
    </div>
  );
}

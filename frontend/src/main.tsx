import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import AuthGate from "./components/AuthGate";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthGate>{(controls) => <App key={controls.session.mode + ":" + (controls.session.user?.user_id ?? "guest")} {...controls} />}</AuthGate>
  </React.StrictMode>
);

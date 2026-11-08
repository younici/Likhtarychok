import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home/Home.jsx";
import Graph from "./pages/Graph/Graph.jsx";
import Info from "./pages/Info/Info.jsx";
import Faq from "./pages/Faq/Faq.jsx";
import Privacy from "./pages/Privacy/Privacy.jsx";
import Donate from "./pages/Donate/Donate.jsx";
import AdmStats from "./pages/AdmStats/AdmStats.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/info" element={<Info />} />
          <Route path="/faq" element={<Faq />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/donate" element={<Donate />} />
          <Route path="/stats" element={<AdmStats />} />
          <Route path="/admstats" element={<AdmStats />} />
          <Route path="*" element={<Navigate to="/graph" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

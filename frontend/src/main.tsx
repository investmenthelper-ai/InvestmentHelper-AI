import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import TradingViewPage from "./pages/TradingViewPage/TradinViewPage";
import ChatbotPage from "./pages/ChatbotPage/Chatbot";
import ScreenerPage from "./pages/ScreenerPage/ScreenerPage"
import './global.css';
ReactDOM.createRoot(document.getElementById("app")!).render(
  <React.StrictMode>
    <Router>
      <Routes>
          <Route path="/" element={<ScreenerPage />} />
          <Route path="/chatbot" element={<ChatbotPage />} />
          <Route path="/screener" element={<ScreenerPage />} />
          <Route path="/tradingview/:stockId" element={<TradingViewPage />} />
      </Routes>
    </Router>
  </React.StrictMode>
);

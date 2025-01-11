import React, { useState } from "react";
import Navbar from "../../components/Navbar/Navbar";
import Sidebar from "../../components/Sidebar/Sidebar";
import ChartArea from "../../components/ChartArea/ChartArea";
import "./TradingViewPage.css";

const TradingViewPage: React.FC = () => {
    const [isSidebarOpen, setSidebarOpen] = useState<boolean>(false);
    const [selectedTool, setSelectedTool] = useState("");
    const handleToolSelect = (tool: string) => {
        setSelectedTool(tool);
    };
    return (
        <div className="trading-view-page">
        {/* Navbar */}
        <Navbar />



      {/* Chart Area */}
        <ChartArea />
     </div>
  );
};

export default TradingViewPage;

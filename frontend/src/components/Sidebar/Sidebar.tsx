import React from "react";
import { Menu } from "antd";
import { LineChartOutlined } from "@ant-design/icons";
import "./Sidebar.css";

type SidebarProps = {
  isOpen: boolean;
  setSidebarOpen: (isOpen: boolean) => void;
  isTrendLineActive: boolean; // Indicates if trendline is active
  onTrendLineToggle: () => void; // Callback for toggling trendline drawing
};

const Sidebar: React.FC<SidebarProps> = ({
                                           isOpen,
                                           setSidebarOpen,
                                           isTrendLineActive,
                                           onTrendLineToggle,
                                         }) => {
  return (
      <div
          className="sidebar-wrapper"
          onMouseEnter={() => setSidebarOpen(true)}
          onMouseLeave={() => setSidebarOpen(false)}
      >
        <div className={`sidebar ${isOpen ? "open" : "closed"}`}>
          <Menu
              mode="inline"
              className="menu"
              inlineCollapsed={!isOpen}
              selectedKeys={isTrendLineActive ? ["trendline"] : []} // Dynamically control active item
          >
            <Menu.Item
                key="trendline"
                icon={<LineChartOutlined />}
                onClick={onTrendLineToggle}
            >
              Trend Line
            </Menu.Item>
          </Menu>
        </div>
      </div>
  );
};

export default Sidebar;

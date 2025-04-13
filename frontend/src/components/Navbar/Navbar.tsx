import React from "react";
import { Menu } from "antd";
import { BarChartOutlined, MessageOutlined, SettingOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom"; // React Router for navigation
import "./Navbar.css";

const items = [
  {
    key: "1",
    icon: <SettingOutlined />,
    label: "News",
    path: "/news", // Placeholder path
  },
  {
    key: "2",
    icon: <BarChartOutlined />,
    label: "Markets",
    path: "/screener", // Add path for navigation
  },
  {
    key: "3",
    icon: <SettingOutlined />,
    label: "Settings",
    path: "/settings", // Placeholder path
  },

];

const Navbar: React.FC = () => {
  const navigate = useNavigate(); // React Router hook for navigation

  const handleMenuClick = ({ key }: { key: string }) => {
    const item = items.find((i) => i.key === key);
    if (item && item.path) {
      navigate(item.path); // Navigate to the specified path
    }
  };

  return (
      <div className="navbar">
        <div className="navbar-logo">
          Finance<span className="navbar-highlight">Helper AI</span>
        </div>
        <Menu
            mode="horizontal"
            defaultSelectedKeys={["1"]}
            className="navbar-menu"
            items={items}
            onClick={handleMenuClick} /* Handle clicks to navigate */
            overflowedIndicator={null}
        />
      </div>
  );
};

export default Navbar;

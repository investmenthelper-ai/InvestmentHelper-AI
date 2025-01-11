// ContextMenu.tsx
import React from "react";

interface ContextMenuProps {
    x: number;
    y: number;
    onDelete: () => void;
    onEdit: () => void;
    onClose: () => void;
}

const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, onDelete, onEdit, onClose }) => {
    return (
        <div
            style={{
                position: "absolute",
                top: y,
                left: x,
                backgroundColor: "#fff",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxShadow: "0 2px 6px rgba(0, 0, 0, 0.2)",
                zIndex: 1000,
            }}
        >
            <button onClick={onDelete} style={{ display: "block", width: "100%" }}>
                Delete
            </button>
            <button onClick={onEdit} style={{ display: "block", width: "100%" }}>
                Edit
            </button>
            <button onClick={onClose} style={{ display: "block", width: "100%" }}>
                Close
            </button>
        </div>
    );
};

export default ContextMenu;

import React, { useState } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  List,
  ListItem,
  IconButton,
  Paper,
  Divider,
  Avatar,
  ListItemText,
  Drawer,
  Toolbar,
  AppBar,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ChatIcon from "@mui/icons-material/Chat";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";

interface Chat {
  id: number;
  title: string;
  messages: { sender: string; text: string }[];
}

const ChatbotPage: React.FC = () => {
  const [chats, setChats] = useState<Chat[]>([
    {
      id: 1,
      title: "Chat 1",
      messages: [{ sender: "Chatbot", text: "Hello! How can I assist you?" }],
    },
  ]);
  const [activeChatId, setActiveChatId] = useState<number>(1);
  const [input, setInput] = useState("");

  const activeChat = chats.find((chat) => chat.id === activeChatId);

  const handleSendMessage = () => {
    if (!input.trim()) return;

    setChats((prevChats) =>
      prevChats.map((chat) =>
        chat.id === activeChatId
          ? {
              ...chat,
              messages: [
                ...chat.messages,
                { sender: "User", text: input },
                { sender: "Chatbot", text: "This is a placeholder response!" },
              ],
            }
          : chat
      )
    );
    setInput("");
  };

  const handleAddChat = () => {
    const newChatId = chats.length + 1;
    setChats([
      ...chats,
      {
        id: newChatId,
        title: `Chat ${newChatId}`,
        messages: [{ sender: "Chatbot", text: "Hello! New chat opened." }],
      },
    ]);
    setActiveChatId(newChatId);
  };

  const handleDeleteChat = (id: number) => {
    setChats((prevChats) => prevChats.filter((chat) => chat.id !== id));
    if (id === activeChatId && chats.length > 1) {
      setActiveChatId(chats[0]?.id ?? 1);
    }
  };

  return (
    <Box sx={{ display: "flex", height: "100vh" }}>
      {/* Sidebar */}
      <Drawer
        variant="permanent"
        sx={{
          width: 250,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: 250, boxSizing: "border-box" },
        }}
      >
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Chats
          </Typography>
          <IconButton onClick={handleAddChat} color="primary">
            <AddIcon />
          </IconButton>
        </Toolbar>
        <Divider />
        <List>
          {chats.map((chat) => (
            <ListItem
              key={chat.id}
              button
              selected={chat.id === activeChatId}
              onClick={() => setActiveChatId(chat.id)}
              sx={{
                bgcolor: chat.id === activeChatId ? "rgba(63, 81, 181, 0.1)" : "inherit",
              }}
            >
              <ChatIcon sx={{ marginRight: 1 }} />
              <ListItemText primary={chat.title} />
              <IconButton
                edge="end"
                color="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteChat(chat.id);
                }}
              >
                <DeleteIcon />
              </IconButton>
            </ListItem>
          ))}
        </List>
      </Drawer>

      {/* Main Chat Area */}
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Chat Header */}
        <AppBar
          position="static"
          sx={{
            bgcolor: "#f5f5f5",
            color: "black",
            padding: 2,
            boxShadow: "none",
            borderBottom: "1px solid #ddd",
          }}
        >
          <Typography variant="h6">{activeChat?.title || "Chat"}</Typography>
        </AppBar>

        {/* Chat Messages */}
        <Box
          sx={{
            flex: 1,
            overflowY: "auto",
            padding: 2,
            bgcolor: "#ffffff",
          }}
        >
          {activeChat?.messages.map((message, index) => (
            <Box
              key={index}
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: message.sender === "User" ? "flex-end" : "flex-start",
                marginBottom: 2,
              }}
            >
              <Paper
                elevation={2}
                sx={{
                  padding: 1.5,
                  maxWidth: "70%",
                  bgcolor: message.sender === "User" ? "#e3f2fd" : "#f1f8e9",
                }}
              >
                <Typography variant="body1">{message.text}</Typography>
              </Paper>
              <Typography
                variant="caption"
                sx={{ marginTop: 0.5, color: "gray" }}
              >
                {message.sender}
              </Typography>
            </Box>
          ))}
        </Box>

        {/* Message Input */}
        <Box
          sx={{
            display: "flex",
            padding: 2,
            borderTop: "1px solid #ddd",
            bgcolor: "#f9f9f9",
          }}
        >
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSendMessage();
            }}
            sx={{ marginRight: 1 }}
          />
          <IconButton
            color="primary"
            onClick={handleSendMessage}
            sx={{ bgcolor: "#3f51b5", color: "white" }}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Box>
    </Box>
  );
};

export default ChatbotPage;

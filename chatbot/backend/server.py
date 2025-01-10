from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from user_db_manager import (
    create_user, get_user_by_username, create_chat, delete_chat,
    save_message, get_chat_messages, get_user_chats,
    delete_all_messages_in_chat
)

app = FastAPI()

# Models
class UserModel(BaseModel):
    username: str

class ChatModel(BaseModel):
    user_id: str = Field(..., alias="userId")
    title: str

class MessageModel(BaseModel):
    chat_id: str = Field(..., alias="chatId")
    message: str

class MessageResponseModel(BaseModel):
    message_id: str = Field(..., alias="messageId")

class ChatResponseModel(BaseModel):
    chat_id: str = Field(..., alias="chatId")

class Message(BaseModel):
    sender: str
    message: str
    timestamp: datetime

# Routes
@app.post("/users/", response_model=dict)
def api_create_user(user: UserModel):
    return create_user(user.username)

@app.get("/users/username/{username}", response_model=dict)
def api_get_user_by_username(username: str):
    return get_user_by_username(username)

@app.post("/chats/", response_model=ChatResponseModel)
def api_create_chat(chat: ChatModel):
    result = create_chat(chat.user_id, chat.title)
    return {"chatId": result["chat_id"]}

@app.delete("/chats/{chat_id}/", response_model=dict)
def api_delete_chat(chat_id: str):
    return delete_chat(chat_id)

@app.post("/messages/", response_model=MessageResponseModel)
def api_save_message(message: MessageModel, sender: str = "user"):
    if sender not in ["user", "bot"]:
        raise HTTPException(status_code=400, detail="Invalid sender. Must be 'user' or 'bot'.")
    result = save_message(message.chat_id, sender=sender, message=message.message)
    return {"messageId": result["message_id"]}

@app.get("/chats/{chat_id}/messages/", response_model=List[Message])
def api_get_chat_messages(chat_id: str):
    messages = get_chat_messages(chat_id)
    return [
        Message(sender=msg["sender"], message=msg["message"], timestamp=msg["timestamp"])
        for msg in messages
    ]

@app.get("/users/{user_id}/chats/", response_model=List[dict])
def api_get_user_chats(user_id: str):
    return get_user_chats(user_id)

# NEW endpoint: only delete messages in the chat, but keep the chat record
@app.delete("/chats/{chat_id}/messages/", response_model=dict)
def api_delete_chat_messages(chat_id: str):
    """
    Delete all messages for a chat, but keep the chat record itself.
    Returns {"success": True} if successful.
    """
    success = delete_all_messages_in_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="No messages found or deletion failed.")
    return {"success": True}

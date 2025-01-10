from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException

def get_db():
    """Connect to the MongoDB and return the database."""
    link = "xxx"
    client = MongoClient(link)
    return client["chatbot_db"]

def setup_database():
    """Ensure necessary collections and indexes exist in the database."""
    db = get_db()

    # Create the 'users' collection and ensure unique index on 'username'
    if "users" not in db.list_collection_names():
        db.create_collection("users")
    db["users"].create_index("username", unique=True)

    # Create the 'chats' collection and ensure indexes on 'user_id' and 'title'
    if "chats" not in db.list_collection_names():
        db.create_collection("chats")
    db["chats"].create_index("user_id")
    db["chats"].create_index("title")  # Optional: if title-based lookups are needed

    # Create the 'messages' collection and ensure an index on 'chat_id'
    if "messages" not in db.list_collection_names():
        db.create_collection("messages")
    db["messages"].create_index("chat_id")


setup_database()
db = get_db()
users_collection = db["users"]
chats_collection = db["chats"]
messages_collection = db["messages"]

def create_user(username: str) -> dict:
    """Create a new user with the given username."""
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    user_doc = {
        "username": username,
        "created_at": datetime.utcnow()
    }
    result = users_collection.insert_one(user_doc)
    return {"user_id": str(result.inserted_id)}

def get_user_by_username(username: str) -> dict:
    """Retrieve a user by their username."""
    user = users_collection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": str(user["_id"]), "username": user["username"]}

def create_chat(user_id: str, title: str) -> dict:
    """Create a new chat for a given user ID with a title."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    chat_doc = {
        "user_id": ObjectId(user_id),
        "title": title,
        "created_at": datetime.utcnow()
    }
    result = chats_collection.insert_one(chat_doc)
    return {"chat_id": str(result.inserted_id)}

def delete_chat(chat_id: str) -> dict:
    """Delete a chat and its associated messages."""
    if not ObjectId.is_valid(chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages_collection.delete_many({"chat_id": ObjectId(chat_id)})
    result = chats_collection.delete_one({"_id": ObjectId(chat_id)})

    if result.deleted_count == 1:
        return {"detail": "Chat and associated messages deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete chat")

def delete_all_messages_in_chat(chat_id: str) -> bool:
    """
    Delete all messages in the given chat, but keep the chat record itself.
    Return True if successful (including deleting zero messages), False otherwise.
    """
    if not ObjectId.is_valid(chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    result = messages_collection.delete_many({"chat_id": ObjectId(chat_id)})
    # result.deleted_count returns the number of messages actually deleted
    if result.acknowledged:
        # If the operation was "acknowledged", we can consider it successful
        return True
    return False

def save_message(chat_id: str, sender: str, message: str) -> dict:
    """Save a message in a chat."""
    if not ObjectId.is_valid(chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    message_doc = {
        "chat_id": ObjectId(chat_id),
        "sender": sender,
        "message": message,
        "timestamp": datetime.utcnow()
    }
    result = messages_collection.insert_one(message_doc)
    return {"message_id": str(result.inserted_id)}

def get_chat_messages(chat_id: str) -> list:
    """Retrieve all messages in a chat."""
    if not ObjectId.is_valid(chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages_cursor = messages_collection.find({"chat_id": ObjectId(chat_id)}).sort("timestamp", 1)
    return [
        {
            "sender": doc["sender"],
            "message": doc["message"],
            "timestamp": doc["timestamp"]
        } for doc in messages_cursor
    ]

def get_user_chats(user_id: str) -> list:
    """Retrieve all chats for a user."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    chats_cursor = chats_collection.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
    return [
        {"chat_id": str(chat["_id"]), "title": chat["title"], "created_at": chat["created_at"]} 
        for chat in chats_cursor
    ]

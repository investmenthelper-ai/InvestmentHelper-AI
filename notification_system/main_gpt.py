from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Tuple
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
import requests
import json
import numpy as np  # for cosine similarity
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
from openai import OpenAI

app = FastAPI()

# ------------------------------------------------------------------
# OPENAI CLIENT
# ------------------------------------------------------------------

# Make sure you have an actual API key here.
client = OpenAI(api_key='')

link = ""
client_mongo = MongoClient(link)  # Note: Renamed to avoid confusion with OpenAI client
db = client_mongo["chatbot_db"]

users_collection = db["users"]
chats_collection = db["chats"]
messages_collection = db["messages"]
notifications_collection = db["notifications"]
clusters_collection = db["clusters"]  # NEW: clusters collection

def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc

class UserModel(BaseModel):
    username: str

class ChatModel(BaseModel):
    user_id: str = Field(..., alias="userId")

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

class RephraseRequestModel(BaseModel):
    chat_id: str = Field(..., alias="chatId")
    query: str

class RephraseResponseModel(BaseModel):
    rephrased_query: str

# ------------------------------------------------------------------
# USERS
# ------------------------------------------------------------------

@app.get("/users/username/{username}", response_model=dict)
def get_user_by_username(username: str):
    user = users_collection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": str(user["_id"]), "username": user["username"]}

@app.post("/users/", response_model=dict)
def create_user(user: UserModel):
    # Check if username already exists
    existing_user = users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    user_doc = {
        "username": user.username,
        "created_at": datetime.utcnow()
    }
    result = users_collection.insert_one(user_doc)
    return {"user_id": str(result.inserted_id)}

# ------------------------------------------------------------------
# CHATS
# ------------------------------------------------------------------

@app.post("/chats/", response_model=ChatResponseModel)
def create_chat(chat: ChatModel):
    if not ObjectId.is_valid(chat.user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    user = users_collection.find_one({"_id": ObjectId(chat.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_doc = {
        "user_id": ObjectId(chat.user_id),
        "created_at": datetime.utcnow()
    }
    result = chats_collection.insert_one(chat_doc)
    return ChatResponseModel(chatId=str(result.inserted_id))

@app.delete("/chats/{chat_id}/delete/", response_model=dict)
def delete_chat(chat_id: str):
    if not ObjectId.is_valid(chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages_collection.delete_many({"chat_id": ObjectId(chat_id)})
    chat_result = chats_collection.delete_one({"_id": ObjectId(chat_id)})

    if chat_result.deleted_count == 1:
        return {"detail": "Chat and associated messages deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete chat")

# ------------------------------------------------------------------
# MESSAGES
# ------------------------------------------------------------------

@app.post("/messages/user/", response_model=MessageResponseModel)
def save_user_message(message: MessageModel):
    """
    Classify the user's message. If it's a notification request,
    save it to 'notifications' collection; otherwise, save it to 'messages'.
    Then assign the notification to a cluster if it's a NOTIFICATION.
    """
    if not ObjectId.is_valid(message.chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")
    chat = chats_collection.find_one({"_id": ObjectId(message.chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    classification = classify_message_type(message.message)

    if classification == "NOTIFICATION":
        text = message.message
        text = translateEnglish(text)
        print(text)
        notification_doc = {
            "chat_id": ObjectId(message.chat_id),
            "sender": "user",
            "message": text,
            "timestamp": datetime.utcnow(),
            "cluster_id": None  # will be set once assigned
        }
        result = notifications_collection.insert_one(notification_doc)

        # Assign this new notification to a cluster
        new_notification_id = result.inserted_id
        assign_notification_to_cluster(new_notification_id)

        return {"messageId": str(new_notification_id)}
    else:
        return save_message(message, sender="user")

@app.post("/messages/llm/", response_model=MessageResponseModel)
def save_llm_message(message: MessageModel):
    return save_message(message, sender="llm")

def save_message(message: MessageModel, sender: str):
    if not ObjectId.is_valid(message.chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")
    chat = chats_collection.find_one({"_id": ObjectId(message.chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    message_doc = {
        "chat_id": ObjectId(message.chat_id),
        "sender": sender,
        "message": message.message,
        "timestamp": datetime.utcnow()
    }
    result = messages_collection.insert_one(message_doc)
    return {"messageId": str(result.inserted_id)}

@app.get("/chats/{chat_id}/messages/", response_model=List[Message])
def get_chat_messages(chat_id: str):
    if not ObjectId.is_valid(chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages_cursor = messages_collection.find({"chat_id": ObjectId(chat_id)}).sort("timestamp", 1)
    messages = [
        Message(
            sender=doc["sender"],
            message=doc["message"],
            timestamp=doc["timestamp"]
        )
        for doc in messages_cursor
    ]

    return messages

@app.get("/users/{user_id}/chats/", response_model=List[dict])
def get_user_chats(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chats_cursor = chats_collection.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
    chats = [{"chat_id": str(chat["_id"]), "created_at": chat["created_at"]} for chat in chats_cursor]
    return chats

# ------------------------------------------------------------------
# LLM + CLASSIFICATION ENDPOINTS
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# CHANGED: Replacing the local Llama call with gpt4o-mini
# ------------------------------------------------------------------
def query_gpt4o_mini(prompt: str) -> Tuple[str, str]:
    """
    Send a prompt to OpenAI's 'gpt4o-mini' model and return a tuple:
      (json_output, human_readable_response).

    In this simple example, we return the same string for both
    the 'json_output' and 'human_readable_response' for compatibility.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are ChatGPT, a large language model that follows instructions carefully."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.12
        )
        full_response = response.choices[0].message.content.strip()
        # We return the same content for both fields.
        return full_response, full_response

    except Exception as e:
        raise Exception(f"Error communicating with OpenAI gpt4o-mini: {e}")

# ------------------------------------------------------------------
# Rephrase route
# ------------------------------------------------------------------

@app.post("/rephrase/", response_model=RephraseResponseModel)
def rephrase_query(request: RephraseRequestModel):
    if not ObjectId.is_valid(request.chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    chat = chats_collection.find_one({"_id": ObjectId(request.chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages_cursor = messages_collection.find({"chat_id": ObjectId(request.chat_id)}).sort("timestamp", 1)
    messages = [
        {
            "sender": doc["sender"],
            "message": doc["message"],
            "timestamp": doc["timestamp"].isoformat()
        }
        for doc in messages_cursor
    ]

    prompt_parts = []
    for msg in messages:
        sender_label = "User" if msg["sender"] == "user" else "LLM"
        prompt_parts.append(f"{sender_label}: {msg['message']}")
    chat_history_text = "\n".join(prompt_parts)

    current_query = request.query

    prompt = f"""
    Given the following Turkish conversation between a user and an assistant:
    {chat_history_text}

    Current user query: {current_query}

    Please rephrase the current user query by incorporating any necessary information from the conversation above.
    Replace any references to previous messages with the actual information.
    The rephrased query should be clear and fully self-contained.
    Its type should not change, that is, keep it a statement, question, command, or exclamation as appropriate.
    Please output only the rephrased query (in Turkish) and nothing else!
    """

    try:
        json_output, rephrased_query = query_gpt4o_mini(prompt)  # CHANGED
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rephrased_query:
        raise HTTPException(status_code=500, detail="LLM did not return a rephrased query")

    return RephraseResponseModel(rephrased_query=rephrased_query)

# Re-declare this after because the initial version is above.
@app.delete("/chats/{chat_id}/delete/", response_model=dict)
def delete_chat_final(chat_id: str):
    # Step 1: Validate the chat ID
    if not ObjectId.is_valid(chat_id):
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    # Step 2: Check if the chat exists
    chat = chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Step 3: Delete messages associated with the chat
    messages_collection.delete_many({"chat_id": ObjectId(chat_id)})

    # Step 4: Delete the chat
    result = chats_collection.delete_one({"_id": ObjectId(chat_id)})

    if result.deleted_count == 1:
        return {"detail": "Chat and associated messages deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete chat")

# ------------------------------------------------------------------
# CHANGED: Use gpt4o-mini in classify_message_type
# ------------------------------------------------------------------
def classify_message_type(message_text: str) -> str:

    prompt = f"""
    You are a message classifier. 
    Classify the user's message as either NOTIFICATION or NORMAL based solely on the content. 
    - Respond with NOTIFICATION if the message requests a future notification (e.g., contains phrases like "Tell me", "Let me know", "Notify me", etc.).
    - Respond with NORMAL if it does not request a notification.
    The user's message is: "{message_text}"

    Your response must be a single word: NOTIFICATION or NORMAL.
    """
    try:
        _, classification = query_gpt4o_mini(prompt)  # CHANGED
        classification = classification.strip().upper()
        if "NOTIFICATION" in classification:
            return "NOTIFICATION"
        else:
            return "NORMAL"

    except Exception as e:
        # In case of failure, default to NORMAL
        return "NORMAL"

# ------------------------------------------------------------------
# EMBEDDINGS & CLUSTERING
# ------------------------------------------------------------------
def extract_triplet(text: str) -> str:

    prompt = f"""
    Extract the main (subject, relation, object) or (entity, action, entity)
    decomposition from the text. The decomposition should capture the core meaning of the user's request.
    Ignore phrases like 'notify me', 'tell me', 'let me know right away', 'let me know'. 
    Examples:
        - "Notify me when Koç Holding increases investment" -> "Koç Holding, increases, investment"
        - "Tell me when Turkcell increases number of base stations" -> "Turkcell, increases, number of base stations"
        - "Let me know if Koç Holding and Sabancı work together" -> "Koç Holding, Sabancı, work together"

    Filter the generic and irrelevant words from the notification request.
    Return ONLY the decomposed text, nothing else.
    Text: "{text}"
    """
    
    try:
        # Call the LLM with the preprocessed text
        _, output = query_gpt4o_mini(prompt)  # Replace with your LLM method
        return output.strip()
    except Exception as e:
        # Simple fallback using regex-based heuristic
        return ""

def get_text_and_triplet_embedding(input_text: str, alpha: float = 0.5) -> List[float]:
    """
    1) Extract the triplet from 'input_text'.
    2) Embed the full 'input_text' and the 'triplet'.
    3) Combine them (weighted average) into a final vector.
    """

    extract_meaning = extract_triplet(input_text)
    print(extract_meaning)
    text_emb = get_text_embedding(input_text) if input_text else [0]*1024
    triplet_emb = get_text_embedding(extract_meaning) if extract_meaning else [0]*1024

    v_text = np.array(text_emb)
    v_extract = np.array(triplet_emb)
    final_vec = alpha * v_text + (1 - alpha) * v_extract

    # 4) Normalize final vector for consistency
    norm = np.linalg.norm(final_vec)
    if norm == 0:
        return final_vec.tolist()
    return (final_vec / norm).tolist()

def average_pool(last_hidden_states, attention_mask):
    """
    Applies average pooling to the last hidden states, considering the attention mask.
    """
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

def get_text_embedding(input_text):
    """
    Embeds a single input text using the 'intfloat/e5-large-v2' model.
    """
    tokenizer = AutoTokenizer.from_pretrained('intfloat/e5-large-v2')
    model = AutoModel.from_pretrained('intfloat/e5-large-v2')

    batch_dict = tokenizer([input_text], max_length=512, padding=True, truncation=True, return_tensors='pt')
    outputs = model(**batch_dict)
    embeddings = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
    embeddings = F.normalize(embeddings, p=2, dim=1)  # Normalize the embeddings
    return embeddings[0].tolist()

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def create_new_cluster(message_text: str, message_embedding: List[float]) -> ObjectId:
    """
    Create a new cluster with the message text as the initial summary.
    """
    summary = message_text  # or generate short summary with an LLM
    summary_embedding = message_embedding

    cluster_doc = {
        "summary": summary,
        "summary_embedding": summary_embedding,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "requests": []
    }
    result = clusters_collection.insert_one(cluster_doc)
    return result.inserted_id

# ------------------------------------------------------------------
# CHANGED: Use gpt4o-mini for summary updates
# ------------------------------------------------------------------
def generate_updated_summary(old_summary: str, new_text: str) -> str:

    prompt = f"""
    You have an existing cluster summary:
    {old_summary}

    You have a new request to include:
    {new_text}

    Please produce a short, self-contained summary that incorporates both.
    The summary should be concise, capturing the key points from
    the old summary and the new request. Avoid extraneous details. The summary should only include the combined purpose of both.
    Output only the updated summary text and nothing else! I repeat, only output the updated summary!
    """

    try:
        _, updated_summary = query_gpt4o_mini(prompt)  # CHANGED
    except Exception as e:
        updated_summary = old_summary + " + " + new_text

    if not updated_summary or updated_summary.strip() == "":
        updated_summary = old_summary + " + " + new_text

    return updated_summary.strip()

def update_cluster(cluster_id: ObjectId, new_request_id: ObjectId, new_request_text: str):
    """
    Updates the cluster summary after adding a new request.
    """
    cluster = clusters_collection.find_one({"_id": cluster_id})
    if not cluster:
        return
    
    updated_summary = generate_updated_summary(cluster["summary"], new_request_text)
    new_summary_embedding = get_text_embedding(updated_summary)

    clusters_collection.update_one(
        {"_id": cluster_id},
        {
            "$push": {"requests": new_request_id},
            "$set": {
                "summary": updated_summary,
                "summary_embedding": new_summary_embedding,
                "updated_at": datetime.utcnow()
            }
        }
    )

def assign_notification_to_cluster(notification_id: ObjectId) -> None:
    """
    Assigns a notification to an existing cluster or creates a new one
    if it doesn't meet any existing cluster's similarity threshold.
    Allows max 5 clusters.
    """
    notification = notifications_collection.find_one({"_id": notification_id})
    if not notification:
        return

    message_text = notification["message"]

    embedding = get_text_and_triplet_embedding(message_text, alpha=0.7)

    # Store the embedding in the notification doc
    notifications_collection.update_one(
        {"_id": notification_id},
        {"$set": {"embedding": embedding}}
    )

    clusters = list(clusters_collection.find({}))
    num_clusters = len(clusters)

    best_cluster_id = None
    best_similarity = -1.0

    # Compare with each existing cluster's summary embedding
    for cluster in clusters:
        cluster_emb = cluster["summary_embedding"]
        sim = cosine_similarity(embedding, cluster_emb)
        print(sim)
        # (Optional) refine with one child's embedding, if you want 
        if cluster["requests"]:
            first_child_id = cluster["requests"][0]
            child_doc = notifications_collection.find_one({"_id": first_child_id})
            if child_doc and "embedding" in child_doc:
                child_sim = cosine_similarity(embedding, child_doc["embedding"])
                # Weighted average of summary sim and child sim
                sim = 0.5 * sim + 0.5 * child_sim
                print(sim)
        if sim > best_similarity:
            best_similarity = sim
            best_cluster_id = cluster["_id"]
    
    similarity_threshold = 0.87
    if best_similarity >= similarity_threshold:
        # Add to the best cluster
        update_cluster(best_cluster_id, notification_id, message_text)
        notifications_collection.update_one(
            {"_id": notification_id},
            {"$set": {"cluster_id": best_cluster_id}}
        )
    else:
        # No cluster is suitable
        if num_clusters < 5:
            # Create a new cluster
            new_cluster_id = create_new_cluster(message_text, embedding)
            update_cluster(new_cluster_id, notification_id, message_text)
            notifications_collection.update_one(
                {"_id": notification_id},
                {"$set": {"cluster_id": new_cluster_id}}
            )
        else:
            update_cluster(best_cluster_id, notification_id, message_text)
            notifications_collection.update_one(
                {"_id": notification_id},
                {"$set": {"cluster_id": best_cluster_id}}
            )

class NotificationRequestModel(BaseModel):
    filename: str = "document.txt"
    similarity_threshold: float = 0.80
    chunk_size: int = 300
@app.post("/notifications/send", response_model=dict)
def process_document_for_notifications(request: NotificationRequestModel):
    """
    Reads the given .txt file, chunks it, embeds each chunk,
    compares with cluster summaries, and returns the top two relevant matches.
    """
    # 1) Load file content
    try:
        with open(request.filename, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {request.filename} not found")

    chunks = chunk_text(text, request.chunk_size)
    clusters = list(clusters_collection.find({}))

    relevant_matches = []

    for chunk in chunks:
        chunk_embedding = get_text_embedding(chunk)

        best_cluster_id = None
        best_similarity = -1.0
        cluster_summary = ""

        for cluster in clusters:
            cluster_embedding = cluster["summary_embedding"]
            sim = cosine_similarity(chunk_embedding, cluster_embedding)

            # Optional refinement using one child's embedding
            if cluster["requests"]:
                first_child_id = cluster["requests"][0]
                child_doc = notifications_collection.find_one({"_id": first_child_id})
                if child_doc and "embedding" in child_doc:
                    child_sim = cosine_similarity(chunk_embedding, child_doc["embedding"])
                    sim = 0.5 * sim + 0.5 * child_sim

            if sim > best_similarity:
                best_similarity = sim
                best_cluster_id = cluster["_id"]
                cluster_summary = cluster["summary"]

        # Check threshold
        if best_similarity >= request.similarity_threshold:
            relevant_matches.append({
                "chunk": chunk,
                "cluster_id": str(best_cluster_id),
                "similarity": best_similarity,
                "cluster_summary": cluster_summary
            })

    # Sort relevant matches by similarity in descending order
    sorted_matches = sorted(relevant_matches, key=lambda x: x["similarity"], reverse=True)

    # Select the top two matches
    top_matches = sorted_matches[:2]

    # 5) Return the filename and top matches
    return {
        "filename": request.filename,
        "matches_found": len(top_matches),
        "top_matches": top_matches
    }


def chunk_text(text: str, chunk_size: int) -> List[str]:
    """
    Splits the text into chunks of 'chunk_size' words.
    Returns a list of chunk strings.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk_words = words[i : i + chunk_size]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)
    return chunks

@app.get("/clusters/", response_model=List[dict])
def get_all_clusters():

    """
    Returns all clusters with their summary, 
    the requests in each cluster, and the owner of each request.
    """

    clusters = clusters_collection.find({})
    results = []

    for cluster in clusters:
        cluster_id = str(cluster["_id"])
        summary = cluster.get("summary", "")
        request_ids = cluster.get("requests", [])  # List of notification IDs
        summary_embedding = cluster["summary_embedding"]
        request_details = []
        for req_id in request_ids:
            # Find the notification in the notifications_collection
            notification = notifications_collection.find_one({"_id": req_id})
            if not notification:
                continue

            # We assume "chat_id" can lead us to the user who made this request
            chat_id = notification["chat_id"]
            chat_doc = chats_collection.find_one({"_id": chat_id})
            if not chat_doc:
                continue

            user_id = chat_doc["user_id"]
            user_doc = users_collection.find_one({"_id": user_id})
            if not user_doc:
                continue

            owner_username = user_doc["username"]

            # Build request detail
            request_details.append({
                "notification_id": str(notification["_id"]),
                "message": notification["message"],
                "timestamp": notification["timestamp"],
                "owner": owner_username,
            })

        results.append({
            "cluster_id": cluster_id,
            "summary": summary,
            "requests": request_details,
            "cluster_embedding_chunk": summary_embedding[:50]  # partial embedding
        })

    return results

# ------------------------------------------------------------------
# Translator helper functions using gpt4o-mini
# ------------------------------------------------------------------

def translateEnglish(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert translator with fluency in English and Turkish languages."},
            {"role": "user", "content": f"Translate the given text from Turkish to English, output only the translated text, nothing else! Text: {text}"}
        ],
        temperature=0.12
    )
    return response.choices[0].message.content

def translateTurkish(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Sen, İngilizce ve Türkçe dillerine akıcı bir şekilde hakim olan uzman bir çevirmenisin."},
            {"role": "user", "content": f"Verilen metni İngilizceden Türkçeye çevir, yalnızca çevrilmiş metni yanıt olarak ver, başka hiçbir şey verme! Metin: {text}"}
        ],
        temperature=0.12
    )
    return response.choices[0].message.content

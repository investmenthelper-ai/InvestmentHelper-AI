import chainlit as cl
import requests
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.rag.single_hop import run_pipeline_step_by_step, GraphState

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "example_user"
CHAT_TITLE = "Test Chat Title"

def create_user_if_not_exists(username: str):
    get_user_resp = requests.get(f"{BASE_URL}/users/username/{username}")
    if get_user_resp.status_code == 200:
        return get_user_resp.json()
    create_user_resp = requests.post(
        f"{BASE_URL}/users/", json={"username": username}
    )
    create_user_resp.raise_for_status()
    return create_user_resp.json()

def get_or_create_chat(user_id: str, chat_title: str):
    chats_resp = requests.get(f"{BASE_URL}/users/{user_id}/chats/")
    chats_resp.raise_for_status()
    chats = chats_resp.json()

    chat = next((c for c in chats if c["title"] == chat_title), None)
    if chat:
        return chat["chat_id"]
    
    create_chat_resp = requests.post(
        f"{BASE_URL}/chats/", json={"userId": user_id, "title": chat_title}
    )
    create_chat_resp.raise_for_status()
    created_chat = create_chat_resp.json()
    return created_chat["chatId"]

def fetch_chat_messages(chat_id: str):
    resp = requests.get(f"{BASE_URL}/chats/{chat_id}/messages/")
    resp.raise_for_status()
    return resp.json()

def save_message(chat_id: str, message: str, sender: str):
    payload = {"chatId": chat_id, "message": message}
    resp = requests.post(f"{BASE_URL}/messages/?sender={sender}", json=payload)
    resp.raise_for_status()
    return resp.json()

def build_past_messages_str(messages: list[dict]) -> str:
    conversation_lines = []
    for msg in messages:
        author = "User" if msg["sender"] == "user" else "Bot"
        conversation_lines.append(f"{author}: {msg['message']}")
    return "\n".join(conversation_lines)

@cl.on_chat_start
async def main():
    try:
        # 1. Check or create user
        user = create_user_if_not_exists(USERNAME)
        user_id = user["user_id"]

        # 2. Get or create chat
        chat_id = get_or_create_chat(user_id, CHAT_TITLE)

        # 3. Fetch existing messages
        messages = fetch_chat_messages(chat_id)

        # 4. Display them in Chainlit
        for m in messages:
            author = USERNAME if m["sender"] == "user" else "Bot"
            await cl.Message(content=m["message"], author=author).send()

        # 5. Store chat_id
        cl.user_session.set("chat_id", chat_id)

    except Exception as e:
        await cl.Message(content=f"Error: {e}", author="System").send()

@cl.on_message
async def on_message(message: cl.Message):
    try:
        chat_id = cl.user_session.get("chat_id")
        if not chat_id:
            await cl.Message(
                content="Chat ID not found. Please restart the chat.",
                author="System"
            ).send()
            return

        user_input = message.content.strip().lower()
        if user_input == "delete all":
            # 1) Call your new endpoint that deletes only messages
            url = f"{BASE_URL}/chats/{chat_id}/messages/"
            del_resp = requests.delete(url)
            del_resp.raise_for_status()

            # 2) Confirm to the user
            await cl.Message(
                content="All messages in this chat have been **deleted** from the database. The chat itself still exists but is now empty.",
                author="System"
            ).send()
            return  # Skip the pipeline after deletion

        # Otherwise, we run the normal pipeline
        msgs = fetch_chat_messages(chat_id)
        past_convo = build_past_messages_str(msgs)

        # Build initial state
        state: GraphState = {
            "userQuery": message.content,
            "rephrasedUserQuery": "",
            "englishUserQuery": "",
            "retrievedDocs": [],
            "relevantDocs": [],
            "pastMessages": past_convo,
            "answerGenerated": "",
            "isAnswerSupported": False,
            "turkishAnswer": "",
            "isDecomposed": False,
            "decomposedQueries": [],
            "answerNotFound": False,
            "comeFrom": "",
            "finalAnswer": ""
        }

        # Save user message
        save_message(chat_id, message.content, "user")

        # Step-by-step run
        async for (node_name, updated_state) in run_pipeline_step_by_step(state):
            async with cl.Step(name=node_name) as step:
                """ step.input = f"User query: {updated_state['userQuery']}"
                if node_name == "end":
                    step.output = updated_state["finalAnswer"]
                else:
                    step.output = f"State updated. (Node = {node_name})" """
                if node_name == "rephraseForFollowup":
                    step.input = f"User query: {updated_state['userQuery']}"
                    step.output = f"Rephrased user query: {updated_state['rephrasedUserQuery']}"
                elif node_name == "translateToEnglish":
                    step.input = f"Before translation: {updated_state['rephrasedUserQuery']}"
                    step.output = f"After translation: {updated_state['englishUserQuery']}"
                elif node_name == "retrieval":
                    inp = "Retrieved Documents:\n\n"
                    index = 1
                    for doc in updated_state['retrievedDocs']:
                        inp += f"Document {index})\n{doc}\n\n"
                        index +=1
                    step.input = inp
                    step.output = "Retrieval is done."
                elif node_name == "relevancyCheck":
                    inp = "Relevant Documents:\n\n"
                    index = 1
                    for doc in updated_state['relevantDocs']:
                        inp += f"Document {index})\n{doc}\n\n"
                        index +=1
                    step.input = inp
                    step.output = "Relevancy check is done."
                elif node_name == "generateAnswer":
                    step.output = f"Generated answer: {updated_state['answerGenerated']}"
                elif node_name == "supportednessCheck":
                    step.output = f"Answer supported: {updated_state['isAnswerSupported']}"
                elif node_name == "translateToTurkish":
                    step.input = f"Answer before translation: {updated_state['answerGenerated']}"
                    step.output = f"Translated answer: {updated_state['turkishAnswer']}"
                elif node_name == "decompose":
                    inp = "Generated subqueries:\n\n"
                    index = 1
                    for doc in updated_state["decomposedQueries"]:
                        inp += f"Query {index})\n{doc}\n\n"
                        index +=1
                    step.input = inp
                    step.output = "Query is decomposed into subqueries"
                elif node_name == "end":
                    step.output = f"Final answer is: {updated_state['finalAnswer']}"
        # Show final answer
        bot_answer = updated_state["finalAnswer"]
        await cl.Message(content=bot_answer, author="Bot").send()
        save_message(chat_id, bot_answer, "bot")

    except Exception as e:
        await cl.Message(content=f"An error occurred: {e}", author="System").send()


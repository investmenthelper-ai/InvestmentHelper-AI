import chainlit as cl
import requests
from openai import OpenAI
from datetime import datetime

API_BASE_URL = "http://localhost:8000"
client = OpenAI(api_key='')

def query_gpt4o_mini(prompt: str) -> str:

    """Query OpenAI's GPT4o-mini model and return the response."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are ChatGPT, a large language model that follows instructions carefully."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.12
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"Error communicating with OpenAI gpt4o-mini: {e}")

def classify_message_type_locally(message_text: str) -> str:

    """Classify the message type locally as NOTIFICATION or NORMAL."""
    prompt = f"""
    You are a message type classifier. 
    You ONLY respond with exactly one word, either NOTIFICATION or NORMAL, 
    based on whether the user's message requests a future notification or not.

    The user's message is (in Turkish): \"{message_text}\"

    Please provide your single-word decision:
    """
    classification = query_gpt4o_mini(prompt)
    if "NOTIFICATION" in classification.upper():
        return "NOTIFICATION"
    return "NORMAL"

def translate_text(text: str, target_language: str) -> str:
    """Translate text using GPT4o-mini."""
    if target_language == "English":
        prompt = f"Translate the given text from Turkish to English, output only the translated text, nothing else! Text: {text}"
    else:
        prompt = f"Translate the given text from English to Turkish, output only the translated text, nothing else! Text: {text}"
    return query_gpt4o_mini(prompt)

@cl.on_chat_start
async def main():
    try:
        global user_id
        global chat_id
        global chat_empty
        chat_empty = False
        username = "onur"
        response = requests.get(f"{API_BASE_URL}/users/username/{username}")
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data["user_id"]
        elif response.status_code == 404:
            user_data = {"username": username}
            response = requests.post(f"{API_BASE_URL}/users/", json=user_data)


        # 2. Get or create chat
        response = requests.get(f"{API_BASE_URL}/users/{user_id}/chats/")
        chats = response.json()

        # 3. Fetch existing messages
        
        if not chats:
            chat_empty = True
            chat_data = {"userId": user_id}
            response = requests.post(f"{API_BASE_URL}/chats/", json=chat_data)
            chat_id = response.json()["chatId"]
        else:
            chat_id = chats[-1]["chat_id"]

        response = requests.get(f"{API_BASE_URL}/chats/{chat_id}/messages/")
        messages = response.json()
        print(messages)
        # 4. Display them in Chainlit
        for m in messages:
            author = "user" if m["sender"] == "user" else "Bot"
            await cl.Message(content=m["message"], author=author).send()

        # 5. Store chat_id
        cl.user_session.set("chat_id", chat_id)

    except Exception as e:
        await cl.Message(content=f"Error: {e}", author="System").send()


@cl.on_message
async def talk(message: cl.Message):

    user_message = message.content

    classification = classify_message_type_locally(user_message)

    message_data = {"chatId": chat_id, "message": user_message}
    response = requests.post(f"{API_BASE_URL}/messages/user/", json=message_data)
    if response.status_code != 200:
        await cl.Message(content=f"Failed to save your message: {response.text}").send()
        return
    user_message_id = response.json()["messageId"]

    if classification == "NOTIFICATION":
        await cl.Message(content="Bildirim isteğini aldım. Haber vereceğim.").send()
        return
    
    rephrased_query = user_message
        
    translated_query = translate_text(rephrased_query, "English")
    llm_response = query_gpt4o_mini(translated_query)
    translated_response = translate_text(llm_response, "Turkish")

    llm_message_data = {"chatId": chat_id, "message": translated_response}
    response = requests.post(f"{API_BASE_URL}/messages/llm/", json=llm_message_data)
    if response.status_code != 200:
        await cl.Message(content=f"Failed to save LLM's message: {response.text}").send()
        return

    # Display Llama's response
    await cl.Message(content=translated_response).send()


def build_past_messages_str(messages: list[dict]) -> str:
    conversation_lines = []
    for msg in messages:
        author = "User" if msg["sender"] == "user" else "Bot"
        conversation_lines.append(f"{author}: {msg['message']}")
    return "\n".join(conversation_lines)


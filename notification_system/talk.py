import requests
import json
from datetime import datetime
from openai import OpenAI
from typing import List, Tuple


API_BASE_URL = "http://localhost:8000"
client = OpenAI(api_key='')

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
    

def classify_message_type_locally(message_text: str) -> str:

    prompt = f"""
    You are a message type classifier. 
    You ONLY respond with exactly one word, either NOTIFICATION or NORMAL, 
    based on whether the user's message requests a future notification or not.

    The user's message is (in Turkish): \"{message_text}\"

    Please provide your single-word decision:
    """
    try:
        _, classification = query_gpt4o_mini(prompt)
        classification = classification.strip().upper()
        if "NOTIFICATION" in classification:
            return "NOTIFICATION"
        else:
            return "NORMAL"
    except:
        return "NORMAL"


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

def main():
    # Step 1: Get username
    username = "onur"
    # Step 2: Try to get or create the user
    response = requests.get(f"{API_BASE_URL}/users/username/{username}")
    if response.status_code == 200:
        # User exists
        user_data = response.json()
        user_id = user_data["user_id"]
        print(f"{username} exists. ID is {user_id}.")
    elif response.status_code == 404:
        # User does not exist, create new user
        user_data = {"username": username}
        response = requests.post(f"{API_BASE_URL}/users/", json=user_data)
        if response.status_code == 200:
            user_id = response.json()["user_id"]
            print(f"User '{username}' created with ID: {user_id}")
        else:
            print(f"Failed to create user: {response.text}")
            return
    else:
        print(f"Failed to get or create user: {response.text}")
        return

    # Step 3: Get chats for the user
    response = requests.get(f"{API_BASE_URL}/users/{user_id}/chats/")
    if response.status_code != 200:
        print(f"Failed to get chats: {response.text}")
        return
    chats = response.json()

    # Step 4: Either create a new chat or let user select existing chat
    if len(chats) == 0:
        # No existing chats, create a new one
        chat_data = {"userId": user_id}
        response = requests.post(f"{API_BASE_URL}/chats/", json=chat_data)
        if response.status_code != 200:
            print(f"Failed to create chat: {response.text}")
            return
        chat_id = response.json()["chatId"]
        print(f"New chat created with ID: {chat_id}")
    else:
        # List existing chats
        print("Chats:")
        for idx, chat in enumerate(chats):
            chat_id = chat["chat_id"]
            created_at = chat["created_at"]
            created_at_formatted = datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{idx + 1}. Chat ID: {chat_id}, Created At: {created_at_formatted}")

        while True:
            selection = 1
            if selection.lower() == 'n':
                # Create a new chat
                chat_data = {"userId": user_id}
                response = requests.post(f"{API_BASE_URL}/chats/", json=chat_data)
                if response.status_code != 200:
                    print(f"Failed to create chat: {response.text}")
                    return
                chat_id = response.json()["chatId"]
                print(f"New chat created with ID: {chat_id}")
                break
            else:
                try:
                    selection = int(selection)
                    if 1 <= selection <= len(chats):
                        chat_id = chats[selection - 1]["chat_id"]
                        print(f"Selected chat with ID: {chat_id}")
                        break
                    else:
                        print("Invalid selection. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'n'.")

    # Step 5: Retrieve the conversation history
    response = requests.get(f"{API_BASE_URL}/chats/{chat_id}/messages/")
    if response.status_code != 200:
        print(f"Failed to get chat messages: {response.text}")
        return
    messages = response.json()

    chat_empty = True if len(messages) == 0 else False
    if not chat_empty:
        print("\nConversation history:")
        for msg in messages:
            timestamp = datetime.fromisoformat(msg["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            sender = "You" if msg["sender"] == "user" else "Llama"
            print(f"[{timestamp}] {sender}: {msg['message']}")
    else:
        print("\nNo messages in this chat yet.")

    # Step 6: Conversation loop
    
    while True:
        user_message = input("You: ")
        if user_message.lower() == 'exit':
            print("Exiting chat.")
            break

        # --- A) CLASSIFY LOCALLY ---
        
        classification = classify_message_type_locally(user_message)

        # --- B) POST the user message to the server (server also classifies) ---
        message_data = {"chatId": chat_id, "message": user_message}
        response = requests.post(f"{API_BASE_URL}/messages/user/", json=message_data)
        if response.status_code != 200:
            print(f"Failed to save your message: {response.text}")
            continue
        user_message_id = response.json()["messageId"]

        # If recognized as NOTIFICATION, skip LLM response
        if classification == "NOTIFICATION":
            print("Your message was recognized as a NOTIFICATION request. It has been stored accordingly.")

            chat_empty = False
            continue

        # If NORMAL, proceed with rephrase -> Llama -> LLM response
        if chat_empty:
            # If chat was empty, do not rephrase (no history). 
            # But you can still do so if you want. We'll skip to keep it simple.
            rephrased_query = user_message
            chat_empty = False
        else:
            # Rephrase the user's query using /rephrase/
            rephrase_data = {"chatId": chat_id, "query": user_message}
            response = requests.post(f"{API_BASE_URL}/rephrase/", json=rephrase_data)
            if response.status_code != 200:
                print(f"Failed to rephrase your query: {response.text}")
                continue
            rephrased_query = response.json()["rephrased_query"]
            print(f"Rephrased Query: {rephrased_query}")

        # Send the (rephrased) query to Llama
        try:
            translateEnglish(rephrased_query)
            _, llm_response = query_gpt4o_mini(rephrased_query)
        except Exception as e:
            print(f"Error communicating with Llama: {str(e)}")
            continue

        
        llm_response = translateTurkish(llm_response)
        llm_message_data = {"chatId": chat_id, "message": llm_response}
        response = requests.post(f"{API_BASE_URL}/messages/llm/", json=llm_message_data)
        if response.status_code != 200:
            print(f"Failed to save Llama's message: {response.text}")
            continue

        # Display Llama's response
        print(f"Chatbot: {llm_response}\n")

if __name__ == "__main__":
    main()

from neo4j import GraphDatabase
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
from datetime import datetime
import re
import re
import ast
from langchain.text_splitter import RecursiveCharacterTextSplitter
from prompts import (process_chunk)




""" 
CREATE VECTOR INDEX documentTextEmbeddingIndex IF NOT EXISTS
FOR (doc:Document)
ON doc.textEmbedding
OPTIONS { indexConfig: {
  `vector.dimensions`: 1024,
  `vector.similarity_function`: 'cosine'
}};


CREATE VECTOR INDEX tripletEmbeddingIndex IF NOT EXISTS
FOR ()-[rel]->()
ON rel.tripletEmbedding
OPTIONS { indexConfig: {
  `vector.dimensions`: 1024,
  `vector.similarity_function`: 'cosine'
}};

CREATE VECTOR INDEX tripletEmbeddingIndex IF NOT EXISTS
FOR ()-[rel:RELATIONSHIP_TYPE]->()
ON rel.tripletEmbedding
OPTIONS { indexConfig: {
  `vector.dimensions`: 1024,
  `vector.similarity_function`: 'cosine'
}};



CALL db.indexes();


"""

# Embedding creation
def average_pool(last_hidden_states, attention_mask):
    """
    Applies average pooling to the last hidden states, considering the attention mask.
    """
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

def embed_text(input_text):
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

# Date conversion
def convert_to_date(date_str):
    """
    Converts a date string to a format suitable for Neo4j or returns None for "-".
    """
    if date_str == "-":
        return None
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        return None

# Sanitize relation names
def sanitize_relation(relation):
    """
    Sanitizes the relation string to be a valid Neo4j relationship type.
    """
    return re.sub(r'[^A-Za-z0-9_]', '_', relation)

# Storing documents and fivelets in Neo4j
def store_fivelets_in_neo4j(fivelets, document_text):
    """
    Stores a document with its text and fivelets in Neo4j.
    Connects entities using relationships, stores metadata directly in relationships, and uses
    the original relation for embedding generation, with vector indexing compatibility.

    Args:
    - fivelets (list of dict): List of dictionaries containing the fivelet fields (Entity1, Relation, Entity2, RelatedCompanies, DateInterval).
    - document_text (str): The full text of the document.
    """
    # Generate text embedding
    text_embedding = embed_text(document_text)

    # Connect to Neo4j
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "strongpassword"
    driver = GraphDatabase.driver(uri, auth=(username, password))

    with driver.session() as session:
        # Create or find the document node (only one per unique text)
        query_document = """
        MERGE (d:Document {text: $DocumentText})
        ON CREATE SET d.textEmbedding = $TextEmbedding
        RETURN id(d) AS document_id
        """
        result = session.run(query_document, DocumentText=document_text, TextEmbedding=text_embedding)
        document_id = result.single()["document_id"]

        # Store each triplet and link it to the document node
        for fivelet in fivelets:
            # Use the original relation for generating the embedding
            triplet_text = f"{fivelet['Entity1']} {fivelet['Relation']} {fivelet['Entity2']}"
            triplet_embedding = embed_text(triplet_text)
            
            # Convert date intervals
            start_date = convert_to_date(fivelet['DateInterval'][0])
            end_date = convert_to_date(fivelet['DateInterval'][1])
            
            # Ensure Entity1 and Entity2 nodes exist or are reused
            query_entity1 = """
            MERGE (e:Entity {name: $Entity1})
            RETURN id(e) AS entity1_id
            """
            result = session.run(query_entity1, Entity1=fivelet['Entity1'])
            entity1_id = result.single()["entity1_id"]

            query_entity2 = """
            MERGE (e:Entity {name: $Entity2})
            RETURN id(e) AS entity2_id
            """
            result = session.run(query_entity2, Entity2=fivelet['Entity2'])
            entity2_id = result.single()["entity2_id"]
            
            # Sanitize the relation type for Neo4j
            sanitized_relation_type = sanitize_relation(fivelet['Relation'])
            
            # Create a dynamic relationship between Entity1 and Entity2 using the sanitized Relation
            # and store the original relation text as metadata

            #MERGE (e1)-[r:{sanitized_relation_type}]->(e2)
            query_relationship = f"""
            MATCH (e1:Entity), (e2:Entity)
            WHERE id(e1) = $Entity1ID AND id(e2) = $Entity2ID
            MERGE (e1)-[r:RELATIONSHIP_TYPE]->(e2)
            ON CREATE SET
                r.originalRelation = $OriginalRelation,
                r.relatedCompanies = $RelatedCompanies,
                r.tripletEmbedding = $TripletEmbedding,
                r.startDate = CASE WHEN $StartDate IS NOT NULL THEN date($StartDate) ELSE NULL END,
                r.endDate = CASE WHEN $EndDate IS NOT NULL THEN date($EndDate) ELSE NULL END,
                r.documentID = $DocumentID
            """

            session.run(
                query_relationship,
                Entity1ID=entity1_id,
                Entity2ID=entity2_id,
                OriginalRelation=fivelet['Relation'],  # Store the original relation text
                RelatedCompanies=fivelet['RelatedCompanies'],
                TripletEmbedding=triplet_embedding,
                StartDate=start_date,
                EndDate=end_date,
                DocumentID=document_id
            ) 

    driver.close()

""" # Example usage
if __name__ == "__main__":
    # Example fivelets
    fivelets = [{'Entity1': 'Bank of Canada (BoC)', 'Relation': 'announced that consumer inflation', 'Entity2': 'fell from 2.7% in June to 1.6% in September', 'RelatedCompanies': ['Bank of Canada'], 'DateInterval': ['01.06.2024', '30.09.2024']}, {'Entity1': 'Bank of Canada (BoC)', 'Relation': 'noted that business and consumer inflation expectations', 'Entity2': 'have largely normalized', 'RelatedCompanies': ['Bank of Canada'], 'DateInterval': ['10.11.2024', '10.11.2024']}, {'Entity1': 'Bank of Canada (BoC)', 'Relation': 'mentioned that inflationary pressures', 'Entity2': 'are no longer broad-based', 'RelatedCompanies': ['Bank of Canada'], 'DateInterval': ['10.11.2024', '10.11.2024']}, {'Entity1': 'Bank of Canada (BoC)', 'Relation': 'expects inflation', 'Entity2': 'to remain close to the target', 'RelatedCompanies': ['Bank of Canada'], 'DateInterval': ['10.11.2024', '-']}, {'Entity1': 'Bank of Canada (BoC)', 'Relation': 'highlighted that inflation', 'Entity2': 'has returned to the 2% target', 'RelatedCompanies': ['Bank of Canada'], 'DateInterval': ['10.11.2024', '-']}, {'Entity1': 'Bank of Canada (BoC)', 'Relation': 'reduced the policy interest rate by', 'Entity2': '50 basis points to 3.75%', 'RelatedCompanies': ['Bank of Canada'], 'DateInterval': ['10.11.2024', '10.11.2024']}, {'Entity1': 'Policy interest rate reduction by BoC', 'Relation': 'aims to support', 'Entity2': 'growth and keep inflation near the midpoint of the 1% to 3% range', 'RelatedCompanies': ['Bank of Canada'], 'DateInterval': ['10.11.2024', '-']}]

    document_text = "Bank of Canada's notification on 10.11.2024: The Bank of Canada (BoC) announced that consumer inflation, which was 2.7% in June, had fallen to 1.6% in September. The statement noted that business and consumer inflation expectations have largely normalized because inflationary pressures are no longer broad-based. It also mentioned that inflation is expected to remain close to the target, with upward and downward pressures on inflation roughly balanced. The statement highlighted that inflation has returned to the 2% target and that the policy interest rate was reduced by 50 basis points, bringing it to 3.75%, to support growth and keep inflation near the midpoint of the 1% to 3% range."

    # Store the data in Neo4j
    store_fivelets_in_neo4j(fivelets, document_text) """

def extract_fivelets(text):
    pattern = r'\(\s*\".*?\"\s*,\s*\".*?\"\s*,\s*\".*?\"\s*,\s*\[.*?\]\s*,\s*\[.*?\]\s*\)'
    fivelets = re.findall(pattern, text, re.DOTALL)
    return fivelets

def parse_fivelet(fivelet_str):
    pattern = r'^\(\s*\"(?P<Entity1>.*?)\"\s*,\s*\"(?P<Relation>.*?)\"\s*,\s*\"(?P<Entity2>.*?)\"\s*,\s*(?P<RelatedCompanies>\[.*?\])\s*,\s*(?P<DateInterval>\[.*?\])\s*\)$'
    match = re.match(pattern, fivelet_str)
    if match:
        try:
            Entity1 = match.group('Entity1')
            Relation = match.group('Relation')
            Entity2 = match.group('Entity2')
            RelatedCompanies = ast.literal_eval(match.group('RelatedCompanies'))
            DateInterval = ast.literal_eval(match.group('DateInterval'))
            
            return {
                'Entity1': Entity1,
                'Relation': Relation,
                'Entity2': Entity2,
                'RelatedCompanies': RelatedCompanies,
                'DateInterval': DateInterval
            }
        except Exception as e:
            print(f"Error parsing lists: {e}")
            return None
    else:
        print(f"Could not parse fivelet: {fivelet_str}")
        return None



def process_md_file(file_path, companyName, notificationDate):
    """
    Processes an MD file to extract and parse fivelets.

    Args:
        file_path (str): Path to the markdown file.
        system_prompt (str): System prompt for the LLM.
        user_prompt (str): User prompt to use with the LLM for processing each chunk.
        api_key (str): API key for OpenAI.

    Returns:
        list: Parsed fivelets as dictionaries.
    """
    # Read the markdown file
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()

    # Split text into chunks using Recursive Text Splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
    chunks = text_splitter.split_text(text)

  
    today = datetime.today()
    date_string = today.strftime("%d-%m-%Y")

    result = []

    for chunk in chunks:
        # Generate response using the call_llm function
        response_content = process_chunk(chunk, date_string, companyName, notificationDate)
        chunk = f"{companyName}'s Notification on {notificationDate} \n" + chunk
        # Extract fivelets from the response
        fivelet_strings = extract_fivelets(response_content)

        # Parse valid fivelets
        parsed_fivelets = [parse_fivelet(fivelet_str) for fivelet_str in fivelet_strings if parse_fivelet(fivelet_str)]

        # Append the chunk and its fivelets to the result
        result.append({
            "chunk": chunk,
            "fivelets": parsed_fivelets
        })

    return result

def saveFileToKG(companyName, file_path, notificationDate):
    fiveletsAndChunks = process_md_file(file_path, companyName, notificationDate)
    for item in fiveletsAndChunks:
        store_fivelets_in_neo4j(item["fivelets"], item["chunk"])




file_path = "/Users/hakanmuluk/Desktop/bitirme demosu/backend/turkcell.md"

saveFileToKG("Turkcell", file_path, "30.09.2024")

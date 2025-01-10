from neo4j import GraphDatabase
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
from datetime import date
from datetime import datetime
import re
from .prompts import (process_single_hop_query)

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


def parseUserQueryForSingleHop(data):
    """
    Parses a structured string and extracts companies, start_date, end_date, and mode.
    Converts dates from dd.mm.yyyy to yyyy-mm-dd format, preserving "-" as is.

    Args:
        data (str): The input string to be parsed.

    Returns:
        dict: A dictionary containing the extracted fields.
    """
    # Extract components using regex
    company_match = re.search(r'\[(.*?)\]', data)
    date_match = re.findall(r'\[([^\]]*)\]', data)
    mode_match = re.search(r'"([^"]*)"$', data.strip())

    if not (company_match and len(date_match) > 1 and mode_match):
        raise ValueError("Input string format is invalid or missing components.")

    # Parse the companies
    companies = [c.strip().strip('"') for c in company_match.group(1).split(",")]

    # Parse the dates
    raw_dates = [d.strip().strip('"') for d in date_match[1].split(",")]
    raw_start_date, raw_end_date = raw_dates

    # Format dates
    def format_date(date):
        if date == "-":  # Preserve "-" as is
            return date
        return datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")  # Convert format

    start_date = format_date(raw_start_date)
    end_date = format_date(raw_end_date)

    # Parse the mode
    mode = mode_match.group(1)

    # Construct the result
    return {
        "companies": companies,
        "start_date": start_date,
        "end_date": end_date,
        "mode": mode,
    }

def retrieve_and_rerank_with_temporal_in_neo4j(
    company_filter, date_interval, user_query_embedding, driver, alpha_scale=1.0, mode="none"
):
    """
    Retrieves, reranks, and applies temporal scoring within Neo4j for "early" or "late" mode.

    Args:
    - company_filter (list): List of companies to filter on (e.g., ["YEOTK"]).
    - date_interval (list): Start and end date as strings in the format ["YYYY-MM-DD", "YYYY-MM-DD"].
    - user_query_embedding (list): Embedding of the user query.
    - driver (GraphDatabase.driver): Neo4j driver instance.
    - alpha_scale (float): Scaling factor for temporal score importance.
    - mode (str): Temporal scoring mode ("early", "late", or "none").

    Returns:
    - list: Top 100 fivelets ranked by the combined retrieval and temporal scores.
    """
    

    # Convert date strings to date objects, handling "-"
    start_date = None if date_interval[0] == "-" else datetime.strptime(date_interval[0], "%Y-%m-%d").date()
    end_date = None if date_interval[1] == "-" else datetime.strptime(date_interval[1], "%Y-%m-%d").date()




    # Handle cases where the provided date interval contains "-"
    start_date_condition = "TRUE" if start_date == None else f"(f.startDate IS NULL OR date(f.startDate) >= date($StartDate))"

    end_date_condition = "TRUE" if end_date == None else f"(f.endDate IS NULL OR date(f.endDate) <= date($EndDate))"
    
    query_embedding = list(user_query_embedding)

    if len(company_filter) == 0:
        company_filter = None
    company_condition  = "TRUE" if company_filter == None else f"ANY(company IN $CompanyFilter WHERE company IN f.relatedCompanies)"

    query = f"""
    MATCH (e1:Entity)-[f]->(e2:Entity)
    WHERE {company_condition}
      AND {start_date_condition}
      AND {end_date_condition}
    WITH f, e1, e2
    MATCH (d:Document) WHERE id(d) = f.documentID
    WITH f, e1, e2, d
    CALL db.index.vector.queryRelationships(
        'tripletEmbeddingIndex',
        1000,
        $QueryEmbedding
    )  
    YIELD relationship AS similar_f, score AS triplet_cosine_sim
    WHERE id(f) = id(similar_f)
    CALL db.index.vector.queryNodes(
        'documentTextEmbeddingIndex',
        100,
        $QueryEmbedding
    )
    YIELD node AS similar_d, score AS document_cosine_sim
    WHERE id(d) = id(similar_d)
    WITH f, e1, e2, d, triplet_cosine_sim, document_cosine_sim,
         (triplet_cosine_sim + 0.5 * document_cosine_sim) AS retrieval_score
    RETURN f, e1, e2, d, retrieval_score
    ORDER BY retrieval_score DESC
    LIMIT 100
    """

    with driver.session() as session:
        result = session.run(query, 
                             CompanyFilter=company_filter, 
                             StartDate=start_date if start_date != "-" else None, 
                             EndDate=end_date if end_date != "-" else None, 
                             QueryEmbedding=query_embedding)

        ranked_results = [
            {
                "fiveletId": record["f"].id,
                "retrieval_score": record["retrieval_score"],
                "fivelet_start_date": record["f"]["startDate"],
                "fivelet_end_date": record["f"]["endDate"],
                "document_id": record["d"].id,
                "doc_text": record["d"]["text"]
            }
            for record in result
        ]


    if mode == "none" or not ranked_results:
       
        sorted_results = sorted(ranked_results, key=lambda x: x['retrieval_score'], reverse=True)
        top_doc_texts = []
        seen_docs = set()
        for record in sorted_results:
            doc_id = record['document_id']
            if doc_id not in seen_docs:
                top_doc_texts.append(record['doc_text'])
                seen_docs.add(doc_id)
            if len(top_doc_texts) == 5:
                break
        return top_doc_texts
    
    query_date = (
        min((r["fivelet_start_date"] for r in ranked_results if r["fivelet_start_date"] not in [None, "-"]), default=date.today().strftime("%Y-%m-%d"))
        if mode == "early" and start_date is None
        else date.today().strftime("%Y-%m-%d")
        if mode == "late" and end_date is None
        else start_date if mode == "early" else end_date
    )
  

    temporal_query = """
    WITH $RankedResults AS RankedResults
    UNWIND RankedResults AS result
    WITH result,
        CASE 
            WHEN $Mode = "early" AND (result.fivelet_start_date IS NOT NULL)
            THEN toFloat($AlphaScale) / 
                CASE 
                    WHEN abs(duration.inDays(date(result.fivelet_start_date), date($QueryDate)).days) = 0 
                    THEN 1 
                    ELSE abs(duration.inDays(date(result.fivelet_start_date), date($QueryDate)).days) 
                END
            WHEN $Mode = "late" AND (result.fivelet_end_date IS NOT NULL)
            THEN toFloat($AlphaScale) / 
                CASE 
                    WHEN abs(duration.inDays(date(result.fivelet_end_date), date($QueryDate)).days) = 0 
                    THEN 1 
                    ELSE abs(duration.inDays(date(result.fivelet_end_date), date($QueryDate)).days) 
                END
            ELSE NULL

        END AS temporal_score,
        result.retrieval_score AS retrieval_score
    WITH collect({result: result, temporal_score: temporal_score, retrieval_score: retrieval_score}) AS results_with_scores

    CALL {
        WITH results_with_scores
        UNWIND results_with_scores AS res
        RETURN
            avg(res.temporal_score) AS mean_t,
            stdev(res.temporal_score) AS sigma_t,
            avg(res.retrieval_score) AS mean_s,
            stdev(res.retrieval_score) AS sigma_s
    }

    UNWIND results_with_scores AS res
    WITH res.result AS result, res.temporal_score AS temporal_score, res.retrieval_score AS retrieval_score,
        mean_t, sigma_t, mean_s, sigma_s

    MATCH (e1:Entity)-[f]->(e2:Entity)
    WHERE id(f) = result.fiveletId
    MATCH (d:Document)
    WHERE id(d) = result.document_id

    WITH result, f, e1, e2, d, temporal_score, retrieval_score, mean_t, sigma_t, mean_s, sigma_s,
        CASE WHEN sigma_t = 0 THEN 1 ELSE sigma_t END AS adjusted_sigma_t,
        CASE WHEN sigma_s = 0 THEN 1 ELSE sigma_s END AS adjusted_sigma_s

    WITH result, f, e1, e2, d,
        CASE
            WHEN temporal_score IS NULL THEN mean_t
            ELSE temporal_score
        END AS temporal_score,
        retrieval_score, mean_t, adjusted_sigma_t, mean_s, adjusted_sigma_s

    WITH result, f, e1, e2, d, temporal_score, retrieval_score, mean_t, adjusted_sigma_t, mean_s, adjusted_sigma_s,
        ((temporal_score - mean_t) / adjusted_sigma_t * adjusted_sigma_s + mean_s) AS normalized_temporal_score

    WITH f, e1, e2, d, result, temporal_score, normalized_temporal_score, retrieval_score,
        retrieval_score + (0.7 * normalized_temporal_score) AS final_score

    RETURN f, e1, e2, d, final_score, result, normalized_temporal_score, temporal_score, retrieval_score
    ORDER BY final_score DESC
    LIMIT 100

    """

    with driver.session() as session:
        reranked_result = session.run(
            temporal_query, 
            RankedResults=ranked_results, 
            QueryDate=query_date, 
            Mode=mode,
            AlphaScale=alpha_scale  # Pass the AlphaScale parameter
            )
        
        document_texts = []
        seen_document_ids = set()
       
        """ for record in reranked_result:
            document_id = record["result"]["document_id"]  # Extract the document ID
            if document_id not in seen_document_ids:
                seen_document_ids.add(document_id)  # Track the document ID
                document_texts.append({
                    "document_id": document_id,
                    "text": record["d"]["text"],  # Ensure the Document node has 'text' property
                    "final_score": record["final_score"],  # Include final score for sorting
                })
                if len(document_texts) == 5:  # Stop once we have 5 distinct documents
                    break

        # Return only the top 5 document texts
        sorted_docs = sorted(document_texts, key=lambda x: x["final_score"], reverse=True)  """
        for record in reranked_result:
         
            document_id = record["result"]["document_id"]  # Extract the document ID
            if document_id not in seen_document_ids:
                seen_document_ids.add(document_id)  # Track the document ID
                document_texts.append({
                    "document_id": document_id,
                    "text": record["d"]["text"],  # Ensure the Document node has 'text' property
                    "final_score": record["final_score"],  # Use None if final_score is missing
                    "retrieval_score": record["retrieval_score"],  # Default to 0 for retrieval_score
                })
                if len(document_texts) == 5:  # Stop once we have 5 distinct documents
                    break

        # Sort the documents, falling back to retrieval_score if final_score is None
        sorted_docs = sorted(
            document_texts,
            key=lambda x: x["final_score"] if x["final_score"] is not None else x["retrieval_score"],
            reverse=True
        )

     
        return [doc["text"] for doc in sorted_docs]  


"""         return [
                    {
                        "fivelet": record["f"].id,  # Extract the ID of the relationship 'f'
                        "entity1": record["e1"]["name"],  # Access the 'name' property of the 'e1' node
                        "entity2": record["e2"]["name"],  # Access the 'name' property of the 'e2' node
                        "originalRelation": record["f"]["originalRelation"],
                        "final_score": record["final_score"],  # Combined final score
                        "retrieval_score": record["result"]["retrieval_score"],
                        "normalized_temporal_score": record["normalized_temporal_score"], 
                        "temporal_score": record["temporal_score"]
                    }
                    for record in reranked_result
                ]  """  


def retrieveForSingleHop(userQuery, driver):
    today = datetime.today()
    date_string = today.strftime("%d-%m-%Y")
    userQueryFields = process_single_hop_query(userQuery, date_string)
    parsedFields = parseUserQueryForSingleHop(userQueryFields)
    queryEmbedding = embed_text(userQuery)
    print("*******************************************")
    print("*******************************************")
    print(userQuery)
    print(parsedFields["companies"])
    print(parsedFields["start_date"])
    print(parsedFields["end_date"])
    print(parsedFields["mode"])
    print("*******************************************")
    print("*******************************************")
    results = retrieve_and_rerank_with_temporal_in_neo4j(parsedFields["companies"], [parsedFields["start_date"], parsedFields["end_date"]], queryEmbedding, driver, 1.0, parsedFields["mode"]) 
    return results

def retrieveForSingleHopWithoutFilter(userQuery, driver):
    today = datetime.today()
    date_string = today.strftime("%d-%m-%Y")
    userQueryFields = process_single_hop_query(userQuery, date_string)
    #parsedFields = parseUserQueryForSingleHop(userQueryFields)
    queryEmbedding = embed_text(userQuery)
    results = retrieve_and_rerank_with_temporal_in_neo4j([], ["-", "-"], queryEmbedding, driver, 1.0, "none") 
    return results





""" uri = "bolt://localhost:7687"
username = "neo4j"
password = "strongpassword"
driver = GraphDatabase.driver(uri, auth=(username, password))

q = embed_text("What is the relationship between YEOTK and SEP?")

results = retrieve_and_rerank_with_temporal_in_neo4j(["YEOTK"], ["-", "-"], q, driver, 1, "late")

for res in results:
    print()
    print(res)
    print()  """





""" uri = "bolt://localhost:7687"
username = "neo4j"
password = "strongpassword"
driver = GraphDatabase.driver(uri, auth=(username, password))
print(retrieveForSingleHop("What is the relationship between YEOTK and SEP?", driver)) """



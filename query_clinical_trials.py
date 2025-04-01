import os
import json
import chromadb
import openai
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from utils import get_embedding

_ = load_dotenv(find_dotenv())
openai.api_key = os.getenv('OPENAI_API_KEY')

client = chromadb.PersistentClient(path = "./chroma_db")
collection = client.get_or_create_collection(name = "clinical_trials")

system_prompt = """
You are an assistant that parses clinical trial search queries into structured filters and semantic search phrases.

Given a natural language query, output:
1. key: "status". values can be: [ALL, RECRUITING, COMPLETED]
2. key: "type". values can be: [ALL, INTERVENTIONAL]
3. key: "semantic_phrases". value: a cleaned-up set of terms on conditions and treatments for semantic embedding search

Only include values that are explicitly mentioned in the query.
"""

class RESPONSE_FORMAT(BaseModel):
    status: str
    type: str
    semantic_phrases: str

def get_clinical_trials(
    user_message,  
    system_prompt = system_prompt, 
    n_results = 10,
    model = "gpt-4o-mini", 
    temperature = 0, 
    max_tokens = 500, 
    response_format = RESPONSE_FORMAT):

    llm_response = openai.beta.chat.completions.parse(
        messages = [
            {"role": "system","content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        model = model,
        temperature = temperature,
        max_tokens = max_tokens,
        response_format = response_format
    )
    structured_query = json.loads(llm_response.choices[0].message.content)
    semantic = structured_query["semantic_phrases"]
    filters = [{k: v} for k, v in structured_query.items() if k != "semantic_phrases" and v != 'ALL']
    print(f"parsed structured filters: {filters}\nparsed semantic search phrases: {semantic}")
    
    where_clause = {"$and": filters} if len(filters) > 1 else (filters[0] if filters else {})
    print(f"where_clause: {where_clause}")

    result = collection.query(
        query_embeddings = get_embedding(semantic),
        n_results = n_results,
        where = {"$and": filters} if len(filters) > 1 else (filters[0] if filters else {}),
        include = ["metadatas", "distances"]
    )

    print(f"result: {result}")

    result_formatted = []
    for id, distance, metadata in zip(result["ids"][0], result["distances"][0], result["metadatas"][0]):
        result_formatted.append({
            "id": id,
            "rank": distance,
            "title": metadata["brief_title"],
            "status": metadata["status"],
            "type": metadata["type"],
            "purpose": metadata["purpose"],
            "sponsor": metadata["sponsor"]
        })

    print(f"result_formatted: {result_formatted}")

    return result_formatted

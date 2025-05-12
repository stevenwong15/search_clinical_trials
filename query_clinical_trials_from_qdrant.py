import os
import json
from qdrant_client import QdrantClient, models
import openai
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from utils import get_embedding

_ = load_dotenv(find_dotenv())
openai.api_key = os.getenv("OPENAI_API_KEY")

client = QdrantClient(path="./qdrant_db")
print(f"number of trials in database: {client.get_collection('clinical_trials').points_count}")

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
    filters = [{k: v} for k, v in structured_query.items() if k != "semantic_phrases" and v != "ALL"]
    print(f"parsed structured filters: {filters}\nparsed semantic search phrases: {semantic}")
    
    qdrant_filters = []
    for filter_dict in filters:
        for key, value in filter_dict.items():
            qdrant_filters.append(
                models.FieldCondition(
                    key = key,
                    match = models.MatchValue(value = value)
                )
            )
    
    results = client.search(
        collection_name = "clinical_trials",
        query_vector = get_embedding(semantic),
        limit = n_results,
        query_filter = models.Filter(must = qdrant_filters) if qdrant_filters else None
    )

    results_formatted = []
    for result in results:
        results_formatted.append({
            "id": f"NCT{result.id}",
            "rank": result.score,
            "title": result.payload["brief_title"],
            "status": result.payload["status"],
            "type": result.payload["type"],
            "purpose": result.payload["purpose"],
            "sponsor": result.payload["sponsor"]
        })

    return results_formatted

import os
import json
import ast
from qdrant_client import QdrantClient, models
import openai
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from utils import get_embedding

_ = load_dotenv(find_dotenv())
openai.api_key = os.getenv("OPENAI_API_KEY")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# client = QdrantClient("localhost", port = 6333)
client = QdrantClient(
    url = "https://09ded390-e5ee-4905-80a4-0de54ed1ddd3.us-east4-0.gcp.cloud.qdrant.io:6333", 
    api_key = QDRANT_API_KEY
)
print(f"number of trials in database: {client.get_collection('clinical_trials').points_count}")

SEARCH_INTENT_SYSTEM_PROMPT = """
You are a doctor, and your task is to parse clinical trial search queries into:
- structured filters
- semantic search phrases

Given a user's natural language input, output:
1. key: "type". values can be: ['', 'OBSERVATIONAL', 'INTERVENTIONAL']
2. key: "criteria_sex". values can be: ['', 'FEMALE', 'MALE']
3. key: "criteria_age". values can be: ['', 'CHILD', 'ADULT', 'OLDER_ADULT']
4. key: "location". value: specific location mentioned (city, state, zip code, etc.) or '' if none specified
5. key: "distance_miles". value: numeric distance in miles or 50 if location specified but no distance
6. key: "semantic_phrases". value: a cleaned-up set of terms on conditions and treatments for semantic embedding search

Only include values that are explicitly mentioned in the query.
If a location is mentioned but no distance, use 50 miles as the default.
"""

class RESPONSE_FORMAT(BaseModel):
    type: str
    criteria_sex: str
    criteria_age: str
    location: str
    distance_miles: int
    semantic_phrases: str

def clean_value(value):
    if value is None or value == "['NA']":
        return ""
    try:
        parsed_value = ast.literal_eval(value)
        if isinstance(parsed_value, list):
            return ", ".join([str(v) for v in parsed_value])
        return str(parsed_value)
    except (ValueError, SyntaxError):
        return value

def get_clinical_trials(
    user_message,  
    search_intent_system_prompt = SEARCH_INTENT_SYSTEM_PROMPT, 
    n_results = 10,
    model = "gpt-4.1-nano", 
    temperature = 0, 
    max_tokens = 500, 
    response_format = RESPONSE_FORMAT):

    llm_response = openai.beta.chat.completions.parse(
        messages = [
            {"role": "system","content": search_intent_system_prompt},
            {"role": "user", "content": user_message}
        ],
        model = model,
        temperature = temperature,
        max_tokens = max_tokens,
        response_format = response_format
    )

    structured_query = json.loads(llm_response.choices[0].message.content)
    semantic = structured_query["semantic_phrases"]
    
    search_params = {
        "type": structured_query["type"],
        "criteria_sex": structured_query["criteria_sex"],
        "criteria_age": structured_query["criteria_age"],
        "location": structured_query["location"],
        "distance_miles": structured_query["distance_miles"] if structured_query["location"] else 0,
        "semantic_phrases": semantic
    }
    
    filters = {k: v for k, v in structured_query.items() if k in ["type", "criteria_sex", "criteria_age"]}
    print(f"parsed structured filters: {filters}\nparsed semantic search phrases: {semantic}")
    print(f"location: {structured_query['location']}, distance: {structured_query['distance_miles']} miles")
    
    TYPE_MAP = {
        "": ["INTERVENTIONAL", "OBSERVATIONAL"],
        "INTERVENTIONAL": ["INTERVENTIONAL"],
        "OBSERVATIONAL": ["OBSERVATIONAL"],
    }

    SEX_MAP = {
        "": ["ALL", "FEMALE", "MALE"],
        "FEMALE":["ALL", "FEMALE"],
        "MALE": ["ALL", "MALE"],
    }

    AGE_VARIANTS = [
        "['CHILD']",
        "['ADULT']",
        "['OLDER_ADULT']",
        "['CHILD, ADULT']",
        "['ADULT, OLDER_ADULT']",
        "['CHILD', 'ADULT', 'OLDER_ADULT']",
    ]
    AGE_MAP = {
        "": AGE_VARIANTS,
        "CHILD": [v for v in AGE_VARIANTS if "CHILD" in v],
        "ADULT": [v for v in AGE_VARIANTS if "ADULT" in v],
        "OLDER_ADULT": [v for v in AGE_VARIANTS if "OLDER_ADULT" in v],
    }

    qdrant_filters = []
    for key, value in filters.items():
        qdrant_filters.append(
            models.FieldCondition(
                key = key,
                match = models.models.MatchAny(any = (
                    TYPE_MAP.get(value) if key == "type"
                    else SEX_MAP.get(value) if key == "criteria_sex"
                    else AGE_MAP.get(value) if key == "criteria_age"
                    else ValueError("error")
                    )
                )
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
            "id": result.payload["nct_id"],
            "rank": result.score,
            "brief_title": result.payload["brief_title"],
            "conditions_treated": clean_value(result.payload["conditions_treated"]),
            "start_date": result.payload["start_date"],
            "status": result.payload["status"],
            "type": result.payload["type"],
            "phase": clean_value(result.payload["phase"]),
            "sponsor": result.payload["sponsor"],
            "criteria_age": clean_value(result.payload["criteria_age"]),
            "criteria_sex": result.payload["criteria_sex"],
            "lat_lon": str(result.payload["lat_lon"]),
            "search_params": search_params
        })

    return results_formatted
import os
import json
import ast
import math
import requests
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

# UPDATED SYSTEM PROMPT - More explicit about extracting age/sex from query
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

IMPORTANT INSTRUCTIONS:
- ONLY extract demographic criteria that are EXPLICITLY mentioned in the query
- DO NOT infer or assume demographics based on the medical condition
- For criteria_age: 
  - "children", "pediatric", "kids" → 'CHILD'
  - "adults" → 'ADULT'
  - "older adults", "elderly", "seniors", "geriatric" → 'OLDER_ADULT'
  - If no age is mentioned → ''
- Remove demographic terms from semantic_phrases after extracting them as filters
- semantic_phrases should focus on medical conditions, treatments, and symptoms

Examples:
- Input: "alzheimer's" 
  → criteria_age: '', semantic_phrases: "alzheimer's"
- Input: "alzheimer's for older adults" 
  → criteria_age: 'OLDER_ADULT', semantic_phrases: "alzheimer's"
- Input: "breast cancer trials for women"
  → criteria_sex: 'FEMALE', semantic_phrases: "breast cancer"
- Input: "pediatric asthma studies"
  → criteria_age: 'CHILD', semantic_phrases: "asthma"

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

def haversine(coord1, coord2):
    """
    Calculate the great-circle distance between two coordinates
    in miles using the Haversine formula
    
    Parameters:
    coord1, coord2: [lat, lon] coordinates
    
    Returns:
    Distance in miles
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 3956  # Radius of earth in miles
    
    return c * r

def get_coordinates_from_location(location_query):
    """
    Get [lat, lon] for a location string using OpenStreetMap Nominatim API
    
    Parameters:
    location_query: String representing location (e.g., "Boston, MA")
    
    Returns:
    [lat, lon] or None if location not found
    """
    try:
        # Use Nominatim API for geocoding (add a user-agent to comply with usage policy)
        url = f"https://nominatim.openstreetmap.org/search?q={location_query}&format=json&limit=1"
        headers = {"User-Agent": "ClinicalTrialsSearchApp/1.0"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            results = response.json()
            if results:
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                return [lat, lon]
        
        print(f"Could not geocode location: {location_query}")
        return None
    except Exception as e:
        print(f"Error geocoding location: {str(e)}")
        return None

def get_clinical_trials(
    user_message,  
    search_intent_system_prompt = SEARCH_INTENT_SYSTEM_PROMPT, 
    n_results = 10,
    model = "gpt-4.1-nano", 
    temperature = 0, 
    max_tokens = 500, 
    response_format = RESPONSE_FORMAT,
    geo_buffer_factor = 10  # Factor to increase initial results for geo filtering
):
    # Parse the user query to extract search parameters
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
    
    # DEBUG: Print parsed query to see what's happening
    print(f"\n=== DEBUG: Query Parsing ===")
    print(f"Original query: {user_message}")
    print(f"Parsed structured filters: {filters}")
    print(f"Parsed semantic search phrases: {semantic}")
    print(f"Location: {structured_query['location']}, distance: {structured_query['distance_miles']} miles")
    
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
        # Only add filter if value is not empty
        if value:
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
    
    # DEBUG: Print Qdrant filters
    print(f"Qdrant filters being applied: {qdrant_filters}")
        
    # Determine if we need to do geo-filtering
    do_geo_filtering = search_params["location"] and search_params["distance_miles"] > 0
    
    # Get more initial results if we need to do geo-filtering
    initial_limit = n_results * geo_buffer_factor if do_geo_filtering else n_results
    
    # Get semantic search results
    results = client.search(
        collection_name = "clinical_trials",
        query_vector = get_embedding(semantic),
        limit = initial_limit,
        query_filter = models.Filter(must = qdrant_filters) if qdrant_filters else None
    )
    
    # DEBUG: Print number of results before filtering
    print(f"Number of results from Qdrant: {len(results)}")

    # Apply geo-filtering if location and distance are specified
    if do_geo_filtering:
        user_location = get_coordinates_from_location(search_params["location"])
        if user_location:
            filtered_results = []
            max_distance = search_params["distance_miles"]
            
            for result in results:
                # Parse the lat_lon field which contains arrays of [lat, lon]
                try:
                    # Handle string representation of array of coordinates
                    locations_str = result.payload["lat_lon"]
                    locations = json.loads(locations_str.replace("'", "\""))
                    
                    # Check if the locations is itself an array of arrays
                    if locations and isinstance(locations, list):
                        if isinstance(locations[0], list):
                            # It's already an array of [lat, lon] pairs
                            pass
                        elif isinstance(locations[0], (int, float)):
                            # It's a single [lat, lon] pair
                            locations = [locations]
                        else:
                            # Invalid format
                            continue
                    
                    # Check if any location is within the specified distance
                    within_distance = False
                    for location in locations:
                        if len(location) == 2:  # Make sure it's a valid [lat, lon] pair
                            distance = haversine(user_location, location)
                            if distance <= max_distance:
                                within_distance = True
                                break
                    
                    if within_distance:
                        filtered_results.append(result)
                except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
                    print(f"Error parsing locations for trial {result.payload.get('nct_id')}: {str(e)}")
                    continue
            
            # Replace results with geo-filtered results
            results = filtered_results[:n_results]
            print(f"Found {len(results)} trials within {max_distance} miles of {search_params['location']}")
        else:
            print(f"Warning: Could not geocode location '{search_params['location']}', skipping geo-filtering")
            results = results[:n_results]
    else:
        # If no geo-filtering, just take the top n results
        results = results[:n_results]

    # Format the results for the frontend
    results_formatted = []
    for result in results:
        # Handle missing lat_lon gracefully
        lat_lon_value = result.payload.get("lat_lon", "[]")
        
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
            "lat_lon": str(lat_lon_value),
            "search_params": search_params
        })

    return results_formatted
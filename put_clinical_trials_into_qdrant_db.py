import os
import pandas as pd
from tqdm.autonotebook import tqdm
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv, find_dotenv
from utils import get_token, get_embedding

_ = load_dotenv(find_dotenv())
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

df = pd.read_csv("studies_looking_for_participants_20250518.csv")

# to update:
# - improve embedding model
tqdm.pandas(desc = "counting tokens")
df["keywords_tokens"] = df["keywords"].progress_apply(lambda x: len(get_token(x)))
tqdm.pandas(desc = "generating embeddings")
df["keywords_embeddings"] = df["keywords"].progress_apply(lambda x: get_embedding(x))

df.to_csv('studies_looking_for_participants_20250518_with_embedding.csv', index=False)

client = QdrantClient("localhost", port = 6333)
# client = QdrantClient(
#     url = "https://09ded390-e5ee-4905-80a4-0de54ed1ddd3.us-east4-0.gcp.cloud.qdrant.io:6333", 
#     api_key = QDRANT_API_KEY
# )
if not client.collection_exists(collection_name = "clinical_trials"):
    client.create_collection(
        collection_name = "clinical_trials",
        vectors_config = models.VectorParams(
            size = 1536,
            distance = models.Distance.COSINE
        )
    )

# Process records in batches
BATCH_SIZE = 100
total_records = len(df)

for start_idx in tqdm(range(0, total_records, BATCH_SIZE), desc="Upserting records"):
    end_idx = min(start_idx + BATCH_SIZE, total_records)
    batch_df = df.iloc[start_idx:end_idx]
    
    client.upsert(
        collection_name = "clinical_trials",
        points = [
            models.PointStruct(
                id = int(row["nct_id"].replace("NCT", "")),
                vector = row["keywords_embeddings"],
                payload = {
                "nct_id": row["nct_id"],
                "status": row["status"],
                "start_date": row["start_date"],
                "completion_date": row["completion_date"],
                "first_post_date": row["first_post_date"],
                "last_update_date": row["last_update_date"],
                "contact": row["contact"],
                "sponsor": row["sponsor"],
                "collaborators": row["collaborators"],
                "lat_lon": row["lat_lon"],
                "brief_title": row["brief_title"],
                "official_title": row["official_title"],
                "purpose": row["purpose"],
                "description": row["description"],
                "conditions_treated": row["conditions_treated"],
                "type": row["type"],
                "phase": row["phase"],
                "criteria_overall": row["criteria_overall"],
                "criteria_sex": row["criteria_sex"],
                "criteria_age": row["criteria_age"],
                "keywords_tokens": row["keywords_tokens"],
                }
            )
            for _, row in batch_df.iterrows()
        ]
    )

print(f"end: collection size of {client.get_collection("clinical_trials").points_count}")

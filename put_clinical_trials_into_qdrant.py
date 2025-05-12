import pandas as pd
from tqdm.autonotebook import tqdm
from qdrant_client import QdrantClient, models
from utils import get_token, get_embedding

df = pd.read_csv("studies_20240101_20250228.csv")[1:10]

# import chromadb
# chroma_client = chromadb.PersistentClient(path = "./chroma_db")
# chroma_collection = chroma_client.get_or_create_collection(name = "clinical_trials")

# [item for item in chroma_collection.get()][0][1]

# len(chroma_collection.get()["documents"])
# chroma_collection.get()["metadatas"][1]

# to update:
# - improve embedding model
tqdm.pandas(desc = "counting tokens")
df["keywords_tokens"] = df["keywords"].progress_apply(lambda x: len(get_token(x)))
tqdm.pandas(desc = "generating embeddings")
df["keywords_embeddings"] = df["keywords"].progress_apply(lambda x: get_embedding(x))

client = QdrantClient(path = "./qdrant_db")
if not client.collection_exists(collection_name = "clinical_trials"):
    client.create_collection(
        collection_name = "clinical_trials",
        vectors_config = models.VectorParams(
            size = 1536,
            distance = models.Distance.COSINE
        )
    )

client.upsert(
    collection_name = "clinical_trials",
    points = [
        models.PointStruct(
            id = int(row["nct_id"].replace("NCT", "")),
            vector = row["keywords_embeddings"],
            payload = {
            "status": row["status"],
            "start_date": row["start_date"],
            "completion_date": row["completion_date"],
            "first_post_date": row["first_post_date"],
            "last_update_date": row["last_update_date"],
            "contact": row["contact"],
            "sponsor": row["sponsor"],
            "collaborators": row["collaborators"],
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
        for _, row in df.iterrows()
    ]
)

print(f"end: collection size of {client.get_collection("clinical_trials").points_count}")

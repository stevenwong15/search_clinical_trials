import pandas as pd
from tqdm.autonotebook import tqdm
import chromadb
from utils import get_token, get_embedding

df = pd.read_csv("studies.csv")

# to update:
# - improve embedding model
tqdm.pandas(desc = "counting tokens")
df["keywords_tokens"] = df["keywords"].progress_apply(lambda x: len(get_token(x)))
tqdm.pandas(desc = "generating embeddings")
df["keywords_embeddings"] = df["keywords"].progress_apply(lambda x: get_embedding(x))

client = chromadb.PersistentClient(path = "./chroma_db")
collection = client.get_or_create_collection(name = "clinical_trials")
for _, row in df.iterrows():
    collection.add(
        documents = row["keywords"],
        embeddings = row["keywords_embeddings"],
        ids = [row["nct_id"]],
        metadatas = [{
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
        }])

print(f"end: collection size of {collection.count()}")

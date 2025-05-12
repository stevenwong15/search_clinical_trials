import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

cloud_client = QdrantClient(
    url = "https://09ded390-e5ee-4905-80a4-0de54ed1ddd3.us-east4-0.gcp.cloud.qdrant.io:6333", 
    api_key = QDRANT_API_KEY
)
local_client = QdrantClient("localhost", port = 6333)

local_client.migrate(
    dest_client = cloud_client, 
    collection_names = ["clinical_trials"],
    batch_size = 100,
    recreate_on_collision = True)

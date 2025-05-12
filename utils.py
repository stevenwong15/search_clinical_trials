import os
import tiktoken
import openai
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_token(text, model = "cl100k_base"):
    return tiktoken.get_encoding(model).encode(text)

def get_embedding(text, model = "text-embedding-3-small"):
    max_tokens = 8191
    tokens = get_token(text)
    if len(tokens) > max_tokens:
        text = tiktoken.get_encoding("cl100k_base").decode(tokens[:max_tokens])
    return openai.embeddings.create(input = [text], model = model).data[0].embedding

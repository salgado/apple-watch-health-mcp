# ingest_data.py
# This Python script reads data from a JSON file and ingests it into an Elasticsearch index.

import json
from elasticsearch import Elasticsearch, helpers
import os


# --- Configuration ---
ES_HOST = "http://localhost:9200"
ES_INDEX = "apple-health-steps"
DATA_FILE_PATH = "sample_data.json"

# API key from environment variable or fallback for development
ES_API_KEY = os.getenv('ES_API_KEY')


# --- Index Mapping ---
# This mapping is taken directly from the article to ensure consistency.
INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "type": {"type": "keyword"},
            "sourceName": {"type": "keyword"},
            "deviceInfo": {
                "properties": {
                    "name": {"type": "keyword"},
                    "manufacturer": {"type": "keyword"},
                    "model": {"type": "keyword"},
                    "hardware": {"type": "keyword"},
                    "software": {"type": "keyword"}
                }
            },
            "unit": {"type": "keyword"},
            "creationDate": {
                "type": "date",
                "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"
            },
            "startDate": {
                "type": "date",
                "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"
            },
            "endDate": {
                "type": "date",
                "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"
            },
            "value": {"type": "float"},
            "day": {
                "type": "date",
                "format": "yyyy-MM-dd"
            },
            "dayOfWeek": {"type": "keyword"},
            "hour": {"type": "integer"},
            "duration": {"type": "float"}
        }
    },
    "settings": {
        "number_of_shards": 1,  # WARNING: For production, consider using more shards based on your data volume
        "number_of_replicas": 0  # WARNING: This is set to 0 for development. For production, use at least 1 replica for fault tolerance
        
    }
}


def create_es_client():
    """Creates and returns an Elasticsearch client."""
    print(f"Connecting to Elasticsearch at {ES_HOST}...")
    try:
        client = Elasticsearch(
            hosts=[ES_HOST],
            api_key=ES_API_KEY
        )
        if not client.ping():
            raise ConnectionError("Could not connect to Elasticsearch.")
        print("Connection successful!")
        return client
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def generate_actions(filepath, index_name):
    """
    Reads a JSON array from a file and yields a generator of actions for the bulk API.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)  # Load the entire JSON array
    for doc in data:
        yield {
            "_index": index_name,
            "_source": doc
        }

def ingest_data(client: Elasticsearch):
    """
    Coordinates the ingestion process: deletes the old index, creates a new one, and ingests the data.
    """
    # 1. Delete the index if it already exists for a clean start.
    if client.indices.exists(index=ES_INDEX):
        print(f"Index '{ES_INDEX}' found. Deleting...")
        client.indices.delete(index=ES_INDEX)
        print("Index deleted.")

    # 2. Create the index with the correct mapping.
    print(f"Creating index '{ES_INDEX}' with the specified mapping...")
    client.indices.create(index=ES_INDEX, body=INDEX_MAPPING)
    print("Index created successfully.")

    # 3. Read data from the file and ingest using the Bulk API.
    print(f"Reading data from '{DATA_FILE_PATH}' for ingestion...")
    try:
        # Use the generator to prepare actions for the bulk helper
        actions = generate_actions(DATA_FILE_PATH, ES_INDEX)
        
        # Ingest the data using the bulk helper
        success, failed = helpers.bulk(client, actions)
        print(f"Ingestion complete. Documents successfully ingested: {success}")
        if failed:
            print(f"Failed to ingest documents: {len(failed)}")

    except FileNotFoundError:
        print(f"ERROR: The data file '{DATA_FILE_PATH}' was not found.")
        return
    except Exception as e:
        print(f"An error occurred during file reading or ingestion: {e}")
        return
    
    # 4. Refresh and print the final document count.
    client.indices.refresh(index=ES_INDEX)
    count = client.count(index=ES_INDEX)['count']
    print(f"Final check: The index '{ES_INDEX}' now contains {count} documents.")


if __name__ == "__main__":
    es_client = create_es_client()
    if es_client:
        ingest_data(es_client)
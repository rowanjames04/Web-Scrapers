import json
import csv
import os
from datetime import datetime

PRODUCTS_FILE = "products.json"
HISTORY_FILE = "price_history.csv"

def load_products():
    """Reads the product list from the JSON file."""
    with open(PRODUCTS_FILE, "r") as f:
        return json.load(f)

def save_price_record(record):
    """
    Appends a single price observation to the history CSV.
    record format: {"timestamp": ..., "stockcode": ..., "name": ..., "price": ..., "special_price": ...}
    """
    file_exists = os.path.exists(HISTORY_FILE)

    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "stockcode", "name", "price", "special_price"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)

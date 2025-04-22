from fastapi import FastAPI, Query
from typing import List
import logging
from pymongo import MongoClient
import os
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64

# Initialize FastAPI app
app = FastAPI()

# Configure logging
LOG_FILE = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# MongoDB setup
MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)
db = client["measurement_conversion"]
collection = db["history"]

# Key file path
KEY_FILE = "encryption_key.key"

# Generate and replace the encryption key
def generate_new_key():
    with open(KEY_FILE, "wb") as key_file:
        new_key = os.urandom(32)  # AES-256 key
        key_file.write(new_key)
        logger.info("New encryption key generated and saved.")

generate_new_key()

# Load encryption key
with open(KEY_FILE, "rb") as key_file:
    ENCRYPTION_KEY = key_file.read()
logger.info("Encryption key successfully loaded.")

# Mapping of letters to values
alpha = {
    "_": 0, "a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8, "i": 9, "j": 10,
    "k": 11, "l": 12, "m": 13, "n": 14, "o": 15, "p": 16, "q": 17, "r": 18, "s": 19,
    "t": 20, "u": 21, "v": 22, "w": 23, "x": 24, "y": 25, "z": 26
}

# AES Encryption/Decryption
def encrypt_data(data: str) -> str:
    iv = os.urandom(16)
    backend = default_backend()
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=backend)
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(data.encode()) + padder.finalize()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + encrypted).decode()

def decrypt_data(encrypted_data: str) -> str:
    raw = base64.b64decode(encrypted_data.encode())  # Ensure input is encoded to bytes
    iv = raw[:16]
    encrypted = raw[16:]
    backend = default_backend()
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=backend)
    decryptor = cipher.decryptor()
    padded = decryptor.update(encrypted) + decryptor.finalize()
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    data = unpadder.update(padded) + unpadder.finalize()
    return data.decode()

# Parse measurements
def parse_measurements(input_str: str) -> List[int]:
    """
    Parse measurement string into a list of total values for each package.
    """
    logger.info(f"Processing input string: {input_str}")
    if not input_str:
        return []

    results = []
    i = 0

    while i < len(input_str):
        # Check if enough characters remain for a new package
        if input_str[i] not in alpha:
            raise ValueError(f"Invalid package size character: {input_str[i]}")
        package_size = alpha[input_str[i]]
        i += 1
        package_total = 0
        values_read = 0

        while values_read < package_size and i < len(input_str):
            current_value = 0
            # Chain all consecutive z's and sum their value, then add the next non-z character
            while i < len(input_str) and input_str[i] == 'z':
                current_value += alpha['z']
                i += 1
            if i < len(input_str):
                current_value += alpha[input_str[i]]
                i += 1
            values_read += 1
            package_total += current_value

        # Handle missing values
        while values_read < package_size:
            package_total += alpha['a']
            values_read += 1

        results.append(package_total)
        logger.debug(f"Package total: {package_total}")

        # If not enough characters for a new package, break
        if i >= len(input_str):
            break

    return results

# File path to store the history
LOCAL_FILE = "history.json"

# Route to convert measurements
@app.get("/convert-measurements")
def convert_measurements(input_string: str = Query(..., alias="input")):
    logger.info(f"Received input: {input_string}")
    try:
        # Parse and encrypt the input/output
        converted = parse_measurements(input_string)
        encrypted_input = encrypt_data(input_string)
        encrypted_output = encrypt_data(json.dumps(converted))

        # Save to MongoDB
        collection.insert_one({
            "input": encrypted_input,
            "output": encrypted_output
        })

        # Save to local file
        history_entry = {
            "input": encrypted_input,
            "output": encrypted_output
        }
        if not os.path.exists(LOCAL_FILE):
            with open(LOCAL_FILE, "w") as file:
                json.dump([history_entry], file, indent=4)
        else:
            with open(LOCAL_FILE, "r+") as file:
                data = json.load(file)
                data.append(history_entry)
                file.seek(0)
                json.dump(data, file, indent=4)

        return {"converted": converted}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}

# Route to retrieve history
@app.get("/history")
def get_history():
    history = [
        {
            "input": "encrypted_input_string",
            "output": "encrypted_output_string"
        },
        {
            "input": "another_encrypted_input_string",
            "output": "another_encrypted_output_string"
        }
    ]
    for record in collection.find():
        try:
            decrypted_input = decrypt_data(record["input"])
            decrypted_output = json.loads(decrypt_data(record["output"]))
            history.append({
                "input": decrypted_input,
                "output": decrypted_output
            })
        except Exception as e:
            logger.warning(f"Failed to decrypt record: {e}")
            continue
    return {"history": history}

# Run with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="192.168.100.6", port=8080)


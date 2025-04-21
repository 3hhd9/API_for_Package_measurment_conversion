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

# Configure logging to include a log file
LOG_FILE = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Log to a file
        logging.StreamHandler()        # Log to the console
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
        new_key = os.urandom(32)  # Generate a new 32-byte key for AES-256
        key_file.write(new_key)
        logging.info("A new encryption key has been generated and replaced.")

# Replace the existing key
generate_new_key()

# Load the encryption key from the file
with open(KEY_FILE, "rb") as key_file:
    ENCRYPTION_KEY = key_file.read()

# Log the key loading process
logging.info("Encryption key successfully loaded from the file.")

# Mapping of letters to numbers
alpha = { "_":0,"a":1, "b":2, "c":3, "d":4, "e":5, "f":6, "g":7, "h":8, "i":9, "j":10,
          "k":11, "l":12, "m":13, "n":14, "o":15, "p":16, "q":17, "r":18, "s":19,
          "t":20, "u":21, "v":22, "w":23, "x":24, "y":25, "z":26 }

# Encryption and decryption functions
def encrypt_data(data: str) -> bytes:
    backend = default_backend()
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(b"16bytesivvector"), backend=backend)
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(encrypted_data)

def decrypt_data(encrypted_data: bytes) -> str:
    backend = default_backend()
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(b"16bytesivvector"), backend=backend)
    decryptor = cipher.decryptor()
    encrypted_data = base64.b64decode(encrypted_data)
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()
    return decrypted_data.decode()

def parse_measurements(input_string: str) -> List[int]:
    """
    Parses the input string and converts it into a list of total measured inflows for each package.
    """
    result = []
    packages = input_string.split("_")  # Split the input string by '_'
    
    for package in packages:
        i = 0
        total = 0
        while i < len(package):
            count = alpha.get(package[i], 0)  # Get the count of values in the package
            i += 1
            for _ in range(count):
                if i < len(package):
                    total += alpha.get(package[i], 0)  # Sum the values
                    i += 1
        result.append(total)
    
    return result

@app.get("/convert-measurements")
def convert_measurements(input_string: str = Query(..., alias="input")):
    logger.info(f"Received input string: {input_string}")
    converted = parse_measurements(input_string)
    logger.info(f"Converted result: {converted}")

    # Encrypt and store in MongoDB
    encrypted_input = encrypt_data(input_string).decode()
    encrypted_output = encrypt_data(json.dumps(converted)).decode()
    collection.insert_one({"input": encrypted_input, "output": encrypted_output})

    return {"converted": converted}

@app.get("/history")
def get_history():
    history = []
    for record in collection.find():
        decrypted_input = decrypt_data(record["input"].encode())
        decrypted_output = json.loads(decrypt_data(record["output"].encode()))
        history.append({"input": decrypted_input, "output": decrypted_output})
    return {"history": history}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
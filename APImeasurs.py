from fastapi import FastAPI, Query
from typing import List
import logging
from pymongo import MongoClient
import os
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
import base64

# Initialize FastAPI app
app = FastAPI()

# Logging
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

# MongoDB
MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)
db = client["measurement_conversion"]
collection = db["history"]

# File paths for RSA keys
PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

# Generate RSA key pair if not already present
def generate_key_pair():
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    # Save private key to file
    with open(PRIVATE_KEY_FILE, "wb") as private_file:
        private_file.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        )
    # Generate public key
    public_key = private_key.public_key()
    # Save public key to file
    with open(PUBLIC_KEY_FILE, "wb") as public_file:
        public_file.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )
    logger.info("RSA key pair generated and saved.")

if not os.path.exists(PRIVATE_KEY_FILE) or not os.path.exists(PUBLIC_KEY_FILE):
    generate_key_pair()

# Encrypt data using the public key
def encrypt_data(data: str) -> str:
    with open(PUBLIC_KEY_FILE, "rb") as public_file:
        public_key = serialization.load_pem_public_key(public_file.read())
    encrypted = public_key.encrypt(
        data.encode(),
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted).decode()

# Decrypt data using the private key
def decrypt_data(encrypted_data: str) -> str:
    with open(PRIVATE_KEY_FILE, "rb") as private_file:
        private_key = serialization.load_pem_private_key(private_file.read(), password=None)
    decrypted = private_key.decrypt(
        base64.b64decode(encrypted_data),
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted.decode()

# New string-to-values logic
def string_to_values(s: str) -> List[int]:
    def char_val(c: str) -> int:
        c = c.lower()
        return ord(c) - 96 if 'a' <= c <= 'z' else 0

    slots = []
    i = 0
    while i < len(s):
        if s[i].lower() == 'z':
            slot = s[i]
            i += 1
            while slot and slot[-1].lower() == 'z' and i < len(s):
                slot += s[i]
                i += 1
            slots.append(slot)
        else:
            slots.append(s[i])
            i += 1

    slot_vals = [sum(char_val(c) for c in slot) for slot in slots]

    result = []
    idx = 0
    while idx < len(slot_vals):
        count = slot_vals[idx]
        portion = sum(slot_vals[idx + 1: idx + 1 + count])
        result.append(portion)
        idx += 1 + count

    return result

# Local file
LOCAL_FILE = "history.json"

# Route to convert measurements
@app.get("/convert-measurements")
def convert_measurements(input_string: str = Query(..., alias="input")):
    logger.info(f"Received input: {input_string}")
    try:
        converted = string_to_values(input_string)
        encrypted_input = encrypt_data(input_string)
        encrypted_output = encrypt_data(json.dumps(converted))

        # MongoDB
        collection.insert_one({
            "input": encrypted_input,
            "output": encrypted_output
        })

        # Local file
        history_entry = {"input": encrypted_input, "output": encrypted_output}
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
    history = []
    for record in collection.find():
        try:
            decrypted_input = decrypt_data(record.get("input", ""))
            decrypted_output = json.loads(decrypt_data(record.get("output", "{}")))
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


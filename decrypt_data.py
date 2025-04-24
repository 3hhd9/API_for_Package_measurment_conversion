import json
import os
from pymongo import MongoClient
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
import base64

# File paths for RSA keys
PRIVATE_KEY_FILE = "private_key.pem"

# MongoDB setup
MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)
db = client["measurement_conversion"]
collection = db["history"]

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

# Decrypt data in MongoDB
def decrypt_mongo_data():
    print("Decrypting data in MongoDB...")
    for record in collection.find():
        try:
            decrypted_input = decrypt_data(record["input"])
            decrypted_output = json.loads(decrypt_data(record["output"]))
            print(f"Decrypted Record: Input: {decrypted_input}, Output: {decrypted_output}")
        except Exception as e:
            print(f"Failed to decrypt record: {e}")

# Decrypt data in local storage
def decrypt_local_data():
    LOCAL_FILE = "history.json"
    if not os.path.exists(LOCAL_FILE):
        print("Local history file not found.")
        return

    print("Decrypting data in local storage...")
    with open(LOCAL_FILE, "r") as file:
        data = json.load(file)

    decrypted_data = []
    for entry in data:
        try:
            decrypted_input = decrypt_data(entry["input"])
            decrypted_output = json.loads(decrypt_data(entry["output"]))
            decrypted_data.append({
                "input": decrypted_input,
                "output": decrypted_output
            })
        except Exception as e:
            print(f"Failed to decrypt entry: {e}")

    # Save decrypted data back to the file
    with open(LOCAL_FILE, "w") as file:
        json.dump(decrypted_data, file, indent=4)
    print("Decrypted data saved to local storage.")

if __name__ == "__main__":
    decrypt_mongo_data()
    decrypt_local_data()
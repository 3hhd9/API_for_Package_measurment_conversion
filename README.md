# API for Package Measurement Conversion

This project is a FastAPI-based application designed to process custom-encoded measurement strings, convert them into numerical values, and securely store the results using encryption. The application supports both MongoDB and a local JSON file for storing the conversion history.

## Features
- Converts measurement strings into numerical values based on a predefined mapping.
- Supports chained `z` values and handles missing values by padding with `a` (value = 1).
- Encrypts input and output using AES encryption.
- Stores encrypted data in MongoDB and a local JSON file (`history.json`).
- Logs all activity in `app.log`.

## Endpoints
1. **Convert Measurements**: `/convert-measurements?input=...`
   - Converts the input string into numerical values and stores the results.
   - **Method**: `GET`
   - **Query Parameter**:
     - `input` (string): The input string to be processed.
   - **Example**:
     ```bash
     curl "http://192.168.100.6:8080/convert-measurements?input=dz_a_aazzaaa"
     ```
   - **Response**:
     ```json
     {
         "converted": [28, 53, 1]
     }
     ```

2. **Retrieve History**: `/history`
   - Retrieves the encrypted conversion history from MongoDB and decrypts it.
   - **Method**: `GET`
   - **Example**:
     ```bash
     curl "http://192.168.100.6:8080/history"
     ```
   - **Response**:
     ```json
     {
         "history": [
             {
                 "input": "dz_a_aazzaaa",
                 "output": [28, 53, 1]
             }
         ]
     }

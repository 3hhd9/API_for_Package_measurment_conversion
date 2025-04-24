# Measurement Converter

The **Measurement Converter** is a web application that allows users to convert measurement strings into numerical values, view conversion history, and clear results. It integrates a FastAPI backend with a responsive HTML frontend.

---

## Features

### Frontend
- **Convert Measurements**:
  - Enter a measurement string in the input field and click the "Convert" button to get the converted values.
- **View Conversion History**:
  - Click the "Show History" button to fetch and display previous conversions.
- **Clear Input and Results**:
  - Click the "Clear" button to reset the input field and result area.
- **Error Handling**:
  - Displays user-friendly error messages if the input is invalid or the server is unavailable.
- **Responsive Design**:
  - Light colors, rounded elements, and a clean layout ensure a user-friendly experience on all devices.

### Backend
- **Endpoints**:
  - `/convert-measurements`: Converts the input string into numerical values.
  - `/history`: Retrieves the history of previous conversions.
- **Data Storage**:
  - Stores encrypted input and output in MongoDB and a local JSON file (`history.json`).
- **Encryption**:
  - Uses RSA encryption for secure data storage.

---

## How to Use

### Frontend
1. Open the `UI.html` file in your browser.
2. Enter a measurement string in the input field (e.g., `dz_a_aazzaaa`).
3. Click the **Convert** button to see the converted values.
4. Click the **Show History** button to view previous conversions.
5. Click the **Clear** button to reset the input field and result area.

### Backend
1. Start the FastAPI server:
   ```bash
   python APImeasurs.py

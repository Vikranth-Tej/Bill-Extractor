import pytesseract
from pytesseract import Output
import cv2
import numpy as np
from typing import Dict, List
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\SAI VIKRANTH TEJ\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"


def ocr_page(image: Image.Image):
    # 1. Preprocessing
    # Convert to OpenCV format (RGB -> BGR)
    img = np.array(image)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    # Resize x2 (improves OCR accuracy on small text)
    img = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    
    # Grayscale & Adaptive Thresholding
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        31, 15
    )

    # 2. Tesseract OCR
    # --psm 6: Assume a single uniform block of text
    custom_config = r'--oem 3 --psm 6'
    
    try:
        data = pytesseract.image_to_data(thresh, output_type=Output.DICT, config=custom_config)
        full_text = pytesseract.image_to_string(thresh, config=custom_config)
    except Exception as e:
        print(f"OCR Engine Error: {e}")
        return {"text": "", "rows": []}

    rows = {}
    n = len(data["text"])
    
    for i in range(n):
        txt = data["text"][i].strip()
        if not txt: 
            continue
        
        # --- SAFETY FIX: Handle float confidence scores ---
        try:
            conf_val = data["conf"][i]
            # Convert to float first, then check. Handles '76.5104' and '-1'
            conf = float(conf_val)
        except (ValueError, TypeError):
            conf = -1.0

        if conf < 30: 
            continue # Skip low confidence/garbage text

        # Group words by line number
        line_num = data["line_num"][i]
        
        # Safety for coordinates
        try:
            x = int(data["left"][i])
            y = int(data["top"][i])
            w = int(data["width"][i])
            h = int(data["height"][i])
        except:
            x, y, w, h = 0, 0, 0, 0

        rows.setdefault(line_num, []).append({
            "text": txt,
            "x": x, "y": y, "w": w, "h": h
        })

    # 3. Structure Rows
    structured_rows = []
    for ln in sorted(rows.keys()):
        # Sort words left-to-right based on 'x' coordinate
        words = sorted(rows[ln], key=lambda w: w["x"])
        line_text = " ".join([w["text"] for w in words])
        structured_rows.append({"words": words, "text": line_text})

    return {"text": full_text, "rows": structured_rows}
import re
import itertools
from typing import List, Dict, Optional

# Regex to find financial numbers (matches "1,000.00", "50", "10.5")
NUMBER_PATTERN = re.compile(r'^-?[\d,]+(\.\d+)?$')

def to_float(s: str) -> float:
    return float(s.replace(",", ""))

def solve_math_relation(numbers: List[float]) -> Dict:
    """
    Determines which number is Qty, Rate, and Amount based on math.
    """
    candidates = [n for n in numbers if n > 0.001] # Ignore zeros
    
    # 1. If only 1 number found, assume it is the Amount (Standard for 'Consultation', etc.)
    if len(candidates) == 1:
        return {"qty": 1.0, "rate": candidates[0], "amount": candidates[0]}
    
    # 2. If 3 numbers, check if A * B = C (Permutations)
    if len(candidates) >= 3:
        for p in itertools.permutations(candidates, 3):
            # Allow small float error (e.g. 1.0)
            if abs((p[0] * p[1]) - p[2]) < 1.0:
                return {"qty": p[0], "rate": p[1], "amount": p[2]}

    # 3. Fallback: Largest number is likely the Amount
    if candidates:
        amount = max(candidates)
        return {"qty": 1.0, "rate": amount, "amount": amount}
    
    return None

def extract_items_from_lines_enhanced(rows: List[Dict]) -> List[Dict]:
    """
    Expects 'rows' to be the list of dicts from the OCR step:
    [{'text': '...', 'words': [...]}, ...]
    """
    items = []
    
    # Keywords to skip (Headers/Footers)
    SKIP_KEYWORDS = {"total", "subtotal", "gst", "discount", "net", "amount", "page"}

    for row in rows:
        words = row["words"] # List of word dicts with positions
        text_tokens = [w["text"] for w in words]
        
        # 1. Quick Filter
        full_line = " ".join(text_tokens).lower()
        if any(k in full_line for k in SKIP_KEYWORDS):
            continue

        # 2. Right-to-Left Scan
        financial_numbers = []
        split_index = len(text_tokens)

        # Iterate backwards
        for i in range(len(text_tokens) - 1, -1, -1):
            token = text_tokens[i].replace("Rs.", "").replace("$", "")
            
            # If it's a valid number, add to our list
            if NUMBER_PATTERN.match(token):
                try:
                    val = to_float(token)
                    financial_numbers.append(val)
                    split_index = i # Mark this as the start of the numbers
                except:
                    break # Stop if conversion fails
            else:
                # If we hit text (like "mg" or "Tablet"), stop scanning
                # UNLESS we haven't found any numbers yet.
                if len(financial_numbers) > 0:
                    break
        
        # Restore order (we scanned backwards)
        financial_numbers.reverse()

        # 3. Validation & Extraction
        if not financial_numbers:
            continue

        # Solve the math (Qty * Rate = Amount)
        result = solve_math_relation(financial_numbers)
        if not result:
            continue

        # 4. Get the Name
        name_part = text_tokens[:split_index]
        
        # Clean up name (remove '1.' serial numbers, dates)
        clean_name_tokens = []
        for t in name_part:
            if not re.match(r'^\d+(\.)?$', t) and not re.match(r'\d{2}/\d{2}', t):
                clean_name_tokens.append(t)
        
        item_name = " ".join(clean_name_tokens).strip()

        # Final check: Name must be valid text
        if len(item_name) < 2 or not re.search(r'[a-zA-Z]', item_name):
            continue

        items.append({
            "item_name": item_name,
            "item_quantity": result["qty"],
            "item_rate": result["rate"],
            "item_amount": result["amount"]
        })

    return items
import re
import itertools
from typing import List, Dict, Optional

# Matches currency-like numbers: 1,200.50 | 50.00 | 100
NUMBER_PATTERN = re.compile(r'^-?[\d,]+(\.\d+)?$')

# Skip lines containing these keywords (Headers, Footers, Noise)
SKIP_KEYWORDS = {
    "total", "subtotal", "gross", "net", "balance", "payable",
    "tax", "gst", "discount", "page", "date", "printed", 
    "description", "particulars", "rate", "qty", "amount", "sl no"
}

def to_float(s: str) -> float:
    """Safely converts string to float. Returns 0.0 on failure."""
    try:
        if not s: return 0.0
        clean_s = s.replace(",", "").replace("Rs.", "").replace("$", "")
        return float(clean_s)
    except ValueError:
        return 0.0

def detect_page_type(text: str) -> str:
    low = text.lower()
    if "final bill" in low or "summary" in low or "net payable" in low:
        return "Final Bill"
    if "batch" in low or "expiry" in low or "pharmacy" in low:
        return "Pharmacy"
    return "Bill Detail"

def solve_math_relation(numbers: List[float]) -> Optional[Dict]:
    """
    Identifies Qty, Rate, Amount from a list of numbers using logic:
    Qty * Rate ~= Amount
    """
    # Filter out zeros to avoid division by zero or trivial 0*0=0
    candidates = [n for n in numbers if abs(n) > 0.001]

    if not candidates:
        return None

    # Case 1: Only 1 number -> It's the Amount (Qty=1)
    if len(candidates) == 1:
        val = candidates[0]
        return {"qty": 1.0, "rate": val, "amount": val}

    # Case 2: 3+ numbers -> Check A * B = C
    if len(candidates) >= 3:
        for p in itertools.permutations(candidates, 3):
            qty, rate, amt = p
            # Check math with small tolerance for float rounding
            if abs((qty * rate) - amt) < 1.0:
                return {"qty": qty, "rate": rate, "amount": amt}

    # Case 3: 2 numbers -> Usually (Rate, Amount) or (Qty, Amount)
    # The largest number is usually the Amount.
    candidates.sort()
    amount = candidates[-1]
    other = candidates[-2]

    # Heuristic: If we have 2 numbers, assume Qty=1 unless proven otherwise
    return {"qty": 1.0, "rate": amount, "amount": amount}

def parse_row_right_to_left(words: List[Dict]) -> Optional[Dict]:
    """
    Scans row backwards (Right -> Left) to find financials, then the Name.
    """
    text_tokens = [w["text"] for w in words]
    full_line = " ".join(text_tokens).lower()

    # Skip invalid lines
    if any(k in full_line for k in SKIP_KEYWORDS):
        return None

    financial_numbers = []
    split_index = len(text_tokens)

    # 1. Backward Scan for Numbers
    for i in range(len(text_tokens) - 1, -1, -1):
        token = text_tokens[i].replace(",", "")
        # Remove currency symbols for regex check
        clean_token = token.replace("Rs.", "").replace("$", "")
        
        if NUMBER_PATTERN.match(clean_token):
            val = to_float(clean_token)
            financial_numbers.append(val)
            split_index = i
        else:
            # If we hit text and already have numbers, stop scanning
            if len(financial_numbers) > 0:
                break
    
    # 2. Logic Check
    financial_numbers.reverse() # Restore natural order
    
    if not financial_numbers:
        return None

    math_res = solve_math_relation(financial_numbers)
    if not math_res:
        return None

    # 3. Extract Name
    name_tokens = text_tokens[:split_index]
    
    # Clean leading "1.", "2." or Dates
    cleaned_name_parts = []
    for t in name_tokens:
        # Skip purely numeric indexes or dates
        if not re.match(r'^[\d\W]+$', t) and not re.match(r'\d{2}/\d{2}', t):
            cleaned_name_parts.append(t)

    item_name = " ".join(cleaned_name_parts).strip()

    # Name validation
    if len(item_name) < 2 or not re.search(r'[a-zA-Z]', item_name):
        return None

    return {
        "item_name": item_name,
        "item_quantity": math_res["qty"],
        "item_rate": math_res["rate"],
        "item_amount": math_res["amount"]
    }

def extract_items_from_rows(rows: List[Dict]) -> List[Dict]:
    items = []
    for row in rows:
        result = parse_row_right_to_left(row["words"])
        if result:
            items.append(result)
    return items

def deduplicate_items(items: List[Dict]) -> List[Dict]:
    """
    Removes exact duplicates (same Name + same Amount).
    """
    seen = set()
    cleaned = []
    for it in items:
        # --- SAFETY FIX: Ensure float conversion before int casting ---
        try:
            name_key = it["item_name"].lower().replace(" ", "")
            amt_key = int(float(it["item_amount"])) # Handles '76.51' string safely
            qty_key = int(float(it["item_quantity"]))
            
            sig = (name_key, amt_key, qty_key)
            
            if sig not in seen:
                seen.add(sig)
                cleaned.append(it)
        except Exception:
            # If something is totally broken, just add it to avoid data loss
            cleaned.append(it)
            
    return cleaned

def compute_reconciled_amount(items: List[Dict]) -> float:
    total = sum(float(i["item_amount"]) for i in items)
    return round(total, 2)
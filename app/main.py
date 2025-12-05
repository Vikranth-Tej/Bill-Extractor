from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import traceback

# Import custom modules
from .utils import download_document, is_pdf
from .ocr import ocr_page
from .postprocessing import (
    detect_page_type,
    extract_items_from_rows,
    deduplicate_items,
    compute_reconciled_amount
)

app = FastAPI(title="Bill Extraction API", version="2.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class BillItem(BaseModel):
    item_name: str
    item_amount: float
    item_rate: float
    item_quantity: float

class PageLineItems(BaseModel):
    page_no: str
    page_type: Optional[str] = "Bill Detail"
    bill_items: List[BillItem]

class ExtractData(BaseModel):
    pagewise_line_items: List[PageLineItems]
    total_item_count: int
    reconciled_amount: float

class ExtractResponse(BaseModel):
    is_success: bool
    data: ExtractData

class ExtractRequest(BaseModel):
    document: HttpUrl

@app.post("/extract-bill-data", response_model=ExtractResponse)
def extract_bill_data(req: ExtractRequest):
    try:
        # 1. Download
        file_bytes = download_document(str(req.document))

        # 2. Convert to Images
        images = []
        try:
            # Try as image first
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            images = [image]
        except Exception:
            # Try as PDF
            if is_pdf(file_bytes):
                from pdf2image import convert_from_bytes
                # 300 DPI for high quality
                images = convert_from_bytes(file_bytes, dpi=300)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format")

        all_raw_items = []
        page_outputs = []

        # 3. Process Pages
        for i, img in enumerate(images):
            # OCR
            ocr_result = ocr_page(img)
            
            # Extract
            parsed_items = extract_items_from_rows(ocr_result["rows"])
            
            # Convert to Pydantic models
            bill_items = [BillItem(**item) for item in parsed_items]

            page_outputs.append(PageLineItems(
                page_no=str(i + 1),
                page_type=detect_page_type(ocr_result["text"]),
                bill_items=bill_items
            ))

            all_raw_items.extend(parsed_items)

        # 4. Global Reconciliation
        final_items = deduplicate_items(all_raw_items)
        total_val = compute_reconciled_amount(final_items)

        return ExtractResponse(
            is_success=True,
            data=ExtractData(
                pagewise_line_items=page_outputs,
                total_item_count=len(final_items),
                reconciled_amount=total_val
            )
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        # Print actual error to console for debugging
        print("CRITICAL SERVER ERROR:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
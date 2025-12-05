# OCR-Based Bill Line Item Extraction  

---

##  Project Overview

Hospital bills are chaotic, multiple pages, inconsistent layouts, tabular + free text mashups, and crucial totals hidden between noisy disclaimers.

This API extracts **only what matters**:

-  Individual bill line items  
-  Item names exactly as printed  
-  Quantities & per-unit rates  
-  Net amount per item *(validated mathematically)*  
-  Page classification *(Bill Detail / Pharmacy / Final Bill)*  
-  Accurate total **without double counting**  
-  Zero hallucinations, zero missing rows  

Everything is computed **locally using OCR**, requiring **no external LLM tokens**. 

---

## System Design

| Stage | Action |
|------:|--------|
| **Document Acquisition** | Fetch image/PDF from provided URL |
| **OCR & Preprocessing** | OpenCV enhancement + Tesseract bounding-box extraction |
| **Row Detection** | Line-wise structured grouping |
| **Bill Item Parsing** | Regex-based numeric column identification |
| **Sanity Validation** | `qty × rate ≈ net amount` check & auto-correction |
| **Reconciliation** | Final computed total returned in strict schema |

> Zero pandas dependency.  
> Zero LLM calls.  
> Pure optimized OCR. Fast and reliable.

```

{
  "document": "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&st=2025-11-24T14%3A13%3A22Z&se=2026-11-25T14%3A13%3A00Z&sr=b&sp=r&sig=WFJYfNw0PJdZOpOYlsoAW0XujYGG1x2HSbcDREiFXSU%3D"
}

```

uvicorn app.main:app --reload

http://localhost:8000/docs

---

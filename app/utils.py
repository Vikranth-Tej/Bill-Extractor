import requests

PDF_MAGIC = b"%PDF"

def download_document(url: str) -> bytes:
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")

def is_pdf(data: bytes) -> bool:
    return data.startswith(PDF_MAGIC)
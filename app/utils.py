import unicodedata
import re
import string

def clean_text(text: str):
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\s+', ' ', text)
    text = ''.join(c for c in text if c in string.printable)
    return text.strip()

def is_valid_url(url: str) -> bool:
    url = url.lower()
    return any(domain in url for domain in [
        'instagram.com', 'youtube.com', 'youtu.be', 'tiktok.com'
    ])

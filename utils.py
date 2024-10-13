import re
import pandas as pd 
from urllib.parse import urlparse

from typing import Optional 


def clean_text(text: str) -> str:
    # Remove leading/trailing whitespace and convert to title case, if not NaN
    return None if pd.isna(text) else ' '.join(text.strip().split()).title()


def validate_url(url: str) -> Optional[str]:
    if pd.isna(url):
        return None
    try:
        result = urlparse(url)
        return url if all([result.scheme, result.netloc]) else None
    except Exception:
        return None

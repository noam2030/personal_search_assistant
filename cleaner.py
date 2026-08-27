import re
from bs4 import BeautifulSoup


def clean_html(html: str) -> str:
    """
    Sanitizes raw HTML content into clean, readable text.
    Strips script, style, nav, header, and footer elements to reduce LLM prompt noise.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove irrelevant or noisy HTML tags
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form", "iframe"]):
        tag.decompose()
        
    # Extract visible text with line breaks
    text = soup.get_text(separator="\n")
    
    # Collapse multiple consecutive blank lines and whitespace
    cleaned_lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_text = "\n".join(cleaned_lines)
    
    return cleaned_text

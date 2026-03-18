from .parse_pdf_tool import parse_pdf
from .search_reference_tool import extract_references
from .rag_search_tool import rag_search
from .verify_citation_tool import verify_citation

TOOLS = {
    "parse_pdf": parse_pdf,
    "extract_references": extract_references,
    "rag_search": rag_search,
    "verify_citation": verify_citation
}
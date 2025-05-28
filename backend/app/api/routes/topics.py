from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

# List of common legal topics/areas of law
LEGAL_TOPICS = [
    "Administrative Law",
    "Bankruptcy Law",
    "Civil Rights",
    "Commercial Tenancy",
    "Constitutional Law",
    "Contract Law",
    "Corporate Law",
    "Criminal Law",
    "Employment Law",
    "Environmental Law",
    "Family Law",
    "Immigration Law",
    "Intellectual Property",
    "International Law",
    "Maritime Law",
    "Personal Injury",
    "Property Law",
    "Tax Law",
    "Tort Law",
    "Trusts and Estates"
]

@router.get("/topics", response_model=Dict[str, List[str]])
async def get_topics():
    """
    Get a list of available legal topics for filtering cases and building arguments.
    """
    return {"topics": LEGAL_TOPICS} 
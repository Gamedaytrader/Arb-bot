import re
from dataclasses import dataclass
from rapidfuzz import fuzz

@dataclass(frozen=True)
class MatchScore:
    left: str
    right: str
    score: float

def normalize_event_name(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"\b(vs\.?|@|at|-)\b", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def similarity(left: str, right: str) -> MatchScore:
    return MatchScore(left, right, fuzz.token_set_ratio(normalize_event_name(left), normalize_event_name(right)))

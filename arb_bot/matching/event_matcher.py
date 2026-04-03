import re
from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz

from arb_bot.models import RawMarket


@dataclass(frozen=True)
class MatchScore:
    left: str
    right: str
    score: float


@dataclass
class MarketPair:
    """A matched pair of markets across two platforms."""
    market_a: RawMarket
    market_b: RawMarket
    match_score: float


def normalize_event_name(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"\b(vs\.?|versus|@|at|-)\b", " ", s)
    s = re.sub(r"\b(fc|cf|sc|ac|afc|fk|sk|bk|if|is)\b", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def similarity(left: str, right: str) -> MatchScore:
    score = fuzz.token_set_ratio(normalize_event_name(left), normalize_event_name(right))
    return MatchScore(left, right, score)


def find_matches(
    markets_a: list[RawMarket],
    markets_b: list[RawMarket],
    threshold: float = 85.0,
) -> list[MarketPair]:
    """
    Cross-match markets from two platforms by fuzzy title similarity.

    Returns pairs where similarity score >= threshold.
    Each market from markets_a is matched to its single best counterpart in
    markets_b (greedy, one-to-one).
    """
    pairs: list[MarketPair] = []
    used_b: set[str] = set()

    for a in markets_a:
        best_score = 0.0
        best_b: Optional[RawMarket] = None

        for b in markets_b:
            if b.market_id in used_b:
                continue
            ms = similarity(a.title, b.title)
            if ms.score > best_score:
                best_score = ms.score
                best_b = b

        if best_b is not None and best_score >= threshold:
            pairs.append(MarketPair(market_a=a, market_b=best_b, match_score=best_score))
            used_b.add(best_b.market_id)

    return pairs

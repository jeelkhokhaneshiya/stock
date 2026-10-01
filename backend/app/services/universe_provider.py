from abc import ABC, abstractmethod
from typing import List, Dict

class InvestmentUniverseProvider(ABC):
    @abstractmethod
    def get_candidates(self) -> List[Dict]:
        """Returns a list of candidate dictionaries containing at least 'symbol' and 'type'."""
        pass

class MockInvestmentUniverseProvider(InvestmentUniverseProvider):
    def __init__(self, candidates: List[Dict] = None):
        if candidates is None:
            candidates = [
                {"symbol": "RELIANCE", "type": "STOCK"},
                {"symbol": "TCS", "type": "STOCK"},
                {"symbol": "NIFTYBEES", "type": "ETF"}
            ]
        self._candidates = candidates

    def get_candidates(self) -> List[Dict]:
        return self._candidates

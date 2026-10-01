from abc import ABC, abstractmethod
from typing import Dict, Any

class AIProvider(ABC):
    @abstractmethod
    def generate_decision(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Takes a prompt and a structured context, calls the AI, and returns the raw response string.
        The caller is responsible for parsing it to JSON.
        """
        pass

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate_json(self, prompt: str) -> str:
        raise NotImplementedError
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from llmlib.models import Session

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> List[Session]:
        """Parse the export file and return a list of Sessions."""
        pass

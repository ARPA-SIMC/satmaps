from pathlib import Path
from typing import Self

import pydantic
import yaml


class Flavour(pydantic.BaseModel):
    """Flavour definition data."""

    area: str
    skip: list[str] = []

    @classmethod
    def load(cls, path: Path) -> Self:
        """Load a flavour from a file."""
        with path.open("rt") as fd:
            data = yaml.safe_load(fd)
        return cls.model_validate(data)

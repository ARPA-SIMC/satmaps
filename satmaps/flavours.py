from pathlib import Path
from typing import Self, TypedDict, NotRequired

import pydantic
import yaml


class Overlay(TypedDict):
    """Typing for the overlay dict."""

    coast_dir: str
    color: NotRequired[tuple[int, int, int]]
    width: NotRequired[float]


class Flavour(pydantic.BaseModel):
    """Flavour definition data."""

    area: str
    skip: list[str] = []
    overlay: Overlay | None = None

    @classmethod
    def load(cls, path: Path) -> Self:
        """Load a flavour from a file."""
        with path.open("rt") as fd:
            data = yaml.safe_load(fd)
        return cls.model_validate(data)

from abc import ABC, abstractmethod

from app.schemas.evidence import EvidenceRecord


class MarineDataProvider(ABC):
    """Common interface for ORCA marine-data providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the stable provider identifier."""
        ...

    @abstractmethod
    async def fetch(
        self,
        *,
        latitude: float,
        longitude: float,
        observed_at: str | None = None,
    ) -> list[EvidenceRecord]:
        """Retrieve normalized observations for a location and time."""
        ...
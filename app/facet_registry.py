"""
Facet Registry — loads, indexes, and batches facets from the cleaned CSV.
Scalable: supports 5000+ facets by simply adding rows to the CSV.
"""

import csv
from typing import Dict, List, Optional, Iterator
from collections import defaultdict

from app.models import FacetDefinition
from app.config import settings


class FacetRegistry:
    """
    Central registry of all evaluation facets.
    Loads from CSV and provides batching/filtering APIs.
    """

    def __init__(self, csv_path: Optional[str] = None):
        self._facets: Dict[int, FacetDefinition] = {}
        self._by_category: Dict[str, List[FacetDefinition]] = defaultdict(list)
        self._csv_path = csv_path or settings.FACETS_CSV
        self.load()

    def load(self) -> None:
        """Load facets from CSV file."""
        self._facets.clear()
        self._by_category.clear()

        with open(self._csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                facet = FacetDefinition(
                    facet_id=int(row["facet_id"]),
                    raw_name=row["raw_name"],
                    clean_name=row["clean_name"],
                    category=row["category"],
                    description=row["description"],
                    score_1_anchor=row["score_1_anchor"],
                    score_5_anchor=row["score_5_anchor"],
                )
                self._facets[facet.facet_id] = facet
                self._by_category[facet.category].append(facet)

    @property
    def total(self) -> int:
        return len(self._facets)

    @property
    def categories(self) -> Dict[str, int]:
        return {cat: len(facets) for cat, facets in sorted(self._by_category.items())}

    def get_all(self) -> List[FacetDefinition]:
        return list(self._facets.values())

    def get_by_id(self, facet_id: int) -> Optional[FacetDefinition]:
        return self._facets.get(facet_id)

    def get_by_ids(self, facet_ids: List[int]) -> List[FacetDefinition]:
        return [self._facets[fid] for fid in facet_ids if fid in self._facets]

    def get_by_category(self, category: str) -> List[FacetDefinition]:
        return self._by_category.get(category, [])

    def get_batches(
        self,
        batch_size: Optional[int] = None,
        facet_ids: Optional[List[int]] = None,
    ) -> Iterator[List[FacetDefinition]]:
        """
        Yield batches of facets for LLM evaluation.
        If facet_ids is provided, only those facets are batched.
        """
        bs = batch_size or settings.FACET_BATCH_SIZE
        facets = self.get_by_ids(facet_ids) if facet_ids else self.get_all()

        for i in range(0, len(facets), bs):
            yield facets[i : i + bs]

    def reload(self) -> None:
        """Hot-reload facets from CSV (e.g., after adding new facets)."""
        self.load()


# Global singleton
registry = FacetRegistry()

import re
from dataclasses import dataclass, fields
from functools import cached_property

from .names import DatasetName

# The attributes of a Record by category.
CATEGORIES = {
    "names": ["title", "title_ipa", "name_variants", "wiki_title"],
    "physical_geography": ["lat", "lon"],
    "human_geography": ["country", "capital", "neighbours", "population"],
    "temporal": ["begin_date", "end_date", "inception", "dissolved"],
    "classification": ["types", "instance_of_label"],
    "description": ["details", "described_by", "description", "text_snippets"],
}


@dataclass
class Record:
    """One place, from any dataset, with the attributes we use. Cells are strings as in the
    file, "" when empty or when the dataset has no such column."""

    dataset: DatasetName
    id: str
    # name and name variants
    title: str = ""
    title_ipa: str = ""
    name_variants: str = ""
    wiki_title: str = ""            # Wikidata
    # absolute / physical geography
    lat: str = ""
    lon: str = ""
    # relational / human geography
    country: str = ""
    capital: str = ""               # Wikidata
    neighbours: str = ""            # Wikidata
    population: str = ""            # Wikidata
    # temporal
    begin_date: str = ""            # not Wikidata
    end_date: str = ""              # not Wikidata
    inception: str = ""             # Wikidata
    dissolved: str = ""             # Wikidata
    # classification
    types: str = ""                 # not Wikidata
    instance_of_label: str = ""     # Wikidata
    # description
    details: str = ""               # Pleiades
    described_by: str = ""          # Wikidata
    description: str = ""           # not Trismegistos
    text_snippets: str = ""         # Trismegistos

    @classmethod
    def from_row(cls, dataset: DatasetName, row: dict[str, str]) -> "Record":
        """A record from one row of its dataset's file; columns that are not attributes are left out."""
        return cls(dataset, **{f.name: row[f.name] for f in fields(cls) if f.name in row})

    @cached_property
    def names(self) -> list[str]:
        """Main name first, then the variants and the Wikipedia title (if any), without duplicates,
        language tags ("Ἄλπεις@grc") or trailing qualifiers ("Aethusa (island)")."""
        cells = [self.title, self.name_variants, self.wiki_title]
        return _distinct(_clean(name) for cell in cells for name in re.split(r"\s*[|;،]\s*", cell))

    @cached_property
    def phonetic(self) -> list[str]:
        """The IPA encodings of the title (several for Trismegistos)."""
        return _distinct(ipa.strip() for ipa in self.title_ipa.split("|"))

    @cached_property
    def coordinates(self) -> list[tuple[float, float]]:
        """The (lat, lon) points: none, one or several."""
        return [(float(a), float(b)) for a, b in zip(re.split(r"[;|]", self.lat), re.split(r"[;|]", self.lon))
                if a.strip() and b.strip()]


def _clean(name: str) -> str:
    name = re.sub(r"@[A-Za-z-]+$", "", name.strip())      # language tag
    return re.sub(r"\s+\([^)]*\)$", "", name).strip()     # trailing qualifier


def _distinct(values) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))

from dataclasses import dataclass
from urllib.parse import quote
import json
import requests

ENDPOINT = "https://idos.cz/vlakyautobusymhdvse/Ajax/SearchTimetableObjects/" \
    + "?callback=jQuery35101258140532885048_1788615118771&count=10" \
    + "&searchByPosition=false&onlyStation=false&line=&format=json" \
    + "&bindTtIndex=&date=&_=&prefixText="


@dataclass(slots=True)
class Place:
    """A fully resolved place returned from the IDOS API"""
    title: str
    idents: tuple[str, str]
    description: str
    lines: str


def print_places(places: list[Place]):
    """Print out a list of places prettily."""
    if len(places) == 0:
        return

    def print_place(place: Place):
        lines = place.lines if place.lines else "(no lines)"
        print(f"┌ {place.title}, {place.description}")
        print(f"├ \033[32m@{place.idents[0]}|{place.idents[1]} " +
              f"{place.title}\033[0m")
        print(f"└ {lines}")

    print_place(places[0])
    for place in places[1:]:
        print()
        print_place(place)


def resolve(place: str) -> list[Place]:
    """Use the IDOS place resolution API to attempt to resolve `place`."""
    url = f"{ENDPOINT}{quote(place)}"
    res = requests.get(url)
    res.raise_for_status()

    payload = res.text.split("(", 1)[1].rsplit(")", 1)[0]
    return [
        Place(
            title=place['text'],
            idents=(place['value'], place['value2']),
            description=place['description'],
            lines=place['lines'],
        )
        for place in json.loads(payload)
    ]


def resolve_place_arg(place: str) -> Place | None:
    """
    Attempt to resolve a place argument passed at the command line.

    Place args can either start with an '@" symbol, meaning the ID is provided
    with the place title, e.g. `@302003|654 Hlavní nádraží`, or they can be a
    simple place title which we will attempt to resolve.
    """
    if place.startswith("@"):
        (ident, title) = place[1:].split(" ", maxsplit=1)
        idents = tuple(ident.split("|"))

        try:
            return next(filter(lambda x: x.idents == idents, resolve(title)))
        except:
            return None

    res = resolve(place)

    if len(res) == 0:
        return None
    return res[0]

from dataclasses import dataclass, field
from bs4 import BeautifulSoup, Tag


@dataclass(slots=True)
class Stop:
    """A boarding or alighting stop within a journey leg."""
    time: str
    name: str
    on_request: bool = False
    platform: str | None = None


@dataclass(slots=True)
class Leg:
    """A single vehicle journey between two stops."""
    service: str
    stops: list[Stop] = field(default_factory=list)
    disruption: bool = False


@dataclass(slots=True)
class Transfer:
    """A walking transfer between two journey legs."""
    text: str


JourneyStep = Leg | Transfer


@dataclass(slots=True)
class Connection:
    """One complete connection returned by IDOS."""
    departure: str
    duration: str
    steps: list[JourneyStep] = field(default_factory=list)


def parse_connections(html: str) -> list[Connection]:
    """Parse all connection results from an IDOS HTML response."""
    soup = BeautifulSoup(html, "html.parser")

    # Ignore malformed/incomplete connection boxes rather than failing the
    # whole response when one result cannot be parsed.
    return [
        connection
        for box in soup.select("div.connection.detail-box")
        if (connection := _parse_connection(box)) is not None
    ]


def _parse_connection(box: Tag) -> Connection | None:
    """Parse one `.connection` element."""
    head = box.select_one(".connection-head")
    details = box.select_one(".connection-details")

    # Both sections are required to construct a useful connection.
    if head is None or details is None:
        return None

    date = head.select_one("h2.date")
    duration = head.select_one(".date-total .total strong")

    if date is None or duration is None:
        return None

    # Each top-level line item may contain a transfer, a vehicle leg, or both.
    steps = [
        step
        for line_item in details.find_all(
            "div",
            class_="line-item",
            recursive=False,
        )
        for element in line_item.find_all(
            "div",
            class_=lambda classes: (
                classes is not None and "outside-of-popup" in classes
            ),
            recursive=False,
        )
        for step in _parse_steps(element)
    ]

    return Connection(
        departure=_extract_time(date),
        duration=duration.get_text(" ", strip=True),
        steps=steps,
    )


def _parse_steps(element: Tag) -> list[JourneyStep]:
    """Parse the transfer and/or vehicle leg represented by an element."""
    steps: list[JourneyStep] = []

    # IDOS can put a walking transfer immediately before a vehicle leg.
    if walk := element.find("div", class_="walk", recursive=False):
        steps.append(Transfer(walk.get_text(" ", strip=True)))

    if leg := _parse_leg(element):
        steps.append(leg)

    return steps


def _parse_leg(element: Tag) -> Leg | None:
    """Parse a vehicle leg from an `.outside-of-popup` element."""
    service = element.select_one(".line-title h3")
    stations = element.select_one("ul.stations")

    # Without the service or station list this is not a vehicle leg.
    if service is None or stations is None:
        return None

    return Leg(
        service=service.get_text(" ", strip=True),
        stops=[
            _parse_stop(station)
            for station in stations.find_all("li", recursive=False)
            # Only station entries with the expected time and name are useful.
            if station.select_one(":scope > p.time") is not None
            and station.select_one(":scope > p.station > strong.name")
            is not None
        ],
        disruption=element.select_one(".info-warning") is not None,
    )


def _parse_stop(station: Tag) -> Stop:
    """Parse a single station entry."""
    time = station.select_one(":scope > p.time")
    name = station.select_one(":scope > p.station > strong.name")

    # This function is only called for entries we've already identified as
    # stations, so missing required fields indicate malformed HTML.
    if time is None or name is None:
        raise ValueError("Invalid IDOS station element")

    on_request, platform = _parse_station_metadata(station)

    return Stop(
        time=time.get_text(" ", strip=True),
        name=name.get_text(" ", strip=True),
        on_request=on_request,
        platform=platform,
    )


def _parse_station_metadata(station: Tag) -> tuple[bool, str | None]:
    """Extract platform and on-request information from a station."""
    on_request = False
    platform = None

    # IDOS stores these details in titled spans rather than dedicated fields.
    for element in station.select(".station span[title]"):
        title = element.get("title", "")
        text = element.get_text(" ", strip=True)

        if "nástupiště" in title:
            platform = text
        elif "na znamení" in title:
            on_request = True

    return on_request, platform


def _extract_time(element: Tag) -> str:
    """Extract the departure time, excluding IDOS's displayed date."""
    date_after = element.select_one(".date-after")
    text = element.get_text(" ", strip=True)

    if date_after is None:
        return text

    # The date is rendered inside the same element as the time, so remove it
    # rather than relying on the exact surrounding markup.
    date_text = date_after.get_text(" ", strip=True)
    return text.removesuffix(date_text).strip()

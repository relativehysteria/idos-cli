#!/usr/bin/env python
from datetime import datetime
import requests
import argparse
import parser
import resolver
import formatting

# TODO:
# * Parse and print out warnings (--expand)
# * Print out more connections (--count)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="idos",
        description=(
            "Find public transport connections using IDOS.\n\n"
            "SRC and DEST are either IDOS place queries or exact place IDs "
            "prefixed with '@'. For example, 'Brno', 'hradek;znojmo', or "
            "'@302003|654 Hlavní nádraží'. When a place query is used, "
            "IDOS is queried for matching places and the first result is "
            "selected."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-t", "--time",
        metavar="TIME",
        help=(
            "time of the journey (departure time by default, "
            "or arrival time if --arrive is set). "
            "If omitted, connections departing now are searched. "
            "Can be the hour (\"13:42\"), the date (\"2026-09-14\", "
            "or just \"09-14\"), or both (\"2026-09-14 13:42\")."
        ),
    )

    parser.add_argument(
        "-a", "--arrive",
        action="store_true",
        help=(
            "treat --time as the arrival time rather than the departure time."
        ),
    )

    parser.add_argument(
        "-n", "--num",
        metavar="NAME",
        help=(
            "resolve NAME using IDOS and print the matching places. "
            "When used, all other arguments are ignored."
        ),
    )

    parser.add_argument(
        "-d", "--direct",
        action="store_true",
        help="only return direct connections (no transfers)",
    )

    parser.add_argument(
        "-r", "--resolve",
        metavar="NAME",
        help=(
            "resolve NAME using IDOS and print the matching places and their "
            "fully qualified IDs. When used, all other arguments are ignored."
        ),
    )

    parser.add_argument(
        "src",
        nargs="?",
        metavar="SRC",
        help=(
            "origin, either an IDOS place query or an exact ID prefixed "
            "with '@'"
        ),
    )

    parser.add_argument(
        "dest",
        nargs="?",
        metavar="DEST",
        help=(
            "destination, either an IDOS place query or an exact ID "
            "prefixed with '@'"
        ),
    )

    return parser


def split_datetime(value: str | None) -> tuple[str, str]:
    """Split a --time value into a date and time."""
    if not value or not (value := value.strip()):
        return "", ""

    if " " in value:
        date_part, time_part = value.split(maxsplit=1)
    elif ":" in value:
        date_part, time_part = "", value
    else:
        date_part, time_part = value, ""

    if date_part:
        if len(date_part.split("-")) == 2:
            date_part = f"{datetime.now().year}-{date_part}"

        parsed_date = datetime.strptime(date_part, "%Y-%m-%d")
        weekday = parsed_date.strftime("%a").lower()
        date = f"{parsed_date.day}.{parsed_date.month}" \
               f".{parsed_date.year} {weekday}"
    else:
        date = ""

    time = (
        datetime.strptime(time_part, "%H:%M").strftime("%H:%M")
        if time_part
        else ""
    )

    return date, time


def search_connections(
    src: Place,
    dest: Place,
    time: str | None = None,
    is_arr: bool = False,
    direct: bool = False,
) -> List[parser.Connection]:
    """Search IDOS for connections."""
    def title_ident(place: Place) -> str:
        return f"{place.title}%{place.idents[0]}%{place.idents[1]}"

    # Parse the date
    date, time = split_datetime(time)
    date = f"{date} fri"

    # Build the request and send it!
    data = {
        "From": src.title,
        "FromHidden": title_ident(src),
        "PositionFromHidden": "",
        "To": dest.title,
        "ToHidden": title_ident(dest),
        "PositionToHidden": "",
        "OnlyDirect": str(direct),
        "IsArr": str(is_arr),
        "AdvancedFormTxt": "",
        "ViaReverse": str(False),
        "Date": date,
        "Time": time,
    }

    url = "https://idos.cz/vlakyautobusymhdvse/spojeni/"
    res = requests.post(url, data=data)
    res.raise_for_status()

    # Return the connections we have parsed!

    return parser.parse_connections(res.text)


def main() -> None:
    # Build the parser and parse the args.
    parser = build_parser()
    args = parser.parse_args()

    if args.resolve is not None:
        resolver.print_places(resolver.resolve(args.resolve))
        return

    if args.src is None or args.dest is None:
        parser.error("SRC and DEST are required unless --resolve is used")

    if args.arrive and args.time is None:
        parser.error("--arrive was used but --time was not specififed")

    # Resolve the destinations.
    if not (src := resolver.resolve_place_arg(args.src)):
        print(f'Couldn\'t resolve "{args.src}".')
        return

    if not (dest := resolver.resolve_place_arg(args.dest)):
        print(f'Couldn\'t resolve "{args.dest}".')
        return

    # Query the API for connections.
    connections = search_connections(
        src=src,
        dest=dest,
        time=args.time,
        is_arr=args.arrive,
        direct=args.direct,
    )

    formatting.pretty_print(src, dest, connections)

if __name__ == "__main__":
    main()

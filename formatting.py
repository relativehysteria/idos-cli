import resolver
import parser

class Ansi:
    RESET = "\033[0m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BOLD = "\033[1m"
    DIM = "\033[2m"

    @classmethod
    def wrap(cls, text: str, *styles: str) -> str:
        return f"{''.join(styles)}{text}{cls.RESET}"


def pretty_print(
    src: resolver.Place,
    dest: resolver.Place,
    cons: list[parser.Connection],
) -> None:
    """Print everything to the terminal in a very pretty way!"""
    print("╌" * 46)
    print()
    print(Ansi.wrap(src.title, Ansi.BOLD, Ansi.YELLOW), end=", ")
    print(Ansi.wrap(src.description, Ansi.YELLOW), end=" -> ")
    print(Ansi.wrap(dest.title, Ansi.BOLD, Ansi.YELLOW), end=", ")
    print(Ansi.wrap(dest.description, Ansi.YELLOW))

    for connection in cons:
        print()
        print("╌" * 46)

        departure = Ansi.wrap(connection.departure, Ansi.MAGENTA)
        arrival = Ansi.wrap(connection.steps[-1].stops[-1].time, Ansi.MAGENTA)
        duration = Ansi.wrap(connection.duration, Ansi.BLUE)
        print(f"{duration} | {departure} -> {arrival}\n")

        for idx, step in enumerate(connection.steps):
            is_first = idx == 0
            is_last = idx == len(connection.steps) - 1
            prefix = connection_prefix(is_first, is_last)

            print(prefix, end="")

            if isinstance(step, parser.Transfer):
                print(f"{Ansi.wrap(step.text, Ansi.YELLOW)}\n│")
                continue

            disruption = f" ({Ansi.wrap('!', Ansi.RED, Ansi.BOLD)})" \
                if step.disruption else ""
            print(f"{Ansi.wrap(step.service, Ansi.YELLOW)}{disruption}")

            stop_prefix = " " if is_last else "│"
            print(f"{stop_prefix}   ├ {pretty_stop(step.stops[0])}")
            print(f"{stop_prefix}   └ {pretty_stop(step.stops[-1])}")

            if not is_last:
                print("│")


def connection_prefix(is_first: bool, is_last: bool) -> str:
    if is_first and is_last:
        return ""
    if is_first:
        return "┌ "
    if is_last:
        return "└ "
    return "├ "


def pretty_stop(stop: parser.Stop) -> str:
    request = Ansi.wrap("X", Ansi.CYAN)
    platform = Ansi.wrap(stop.platform, Ansi.GREEN) if stop.platform else ""

    details = ", ".join(
        value
        for value in ((request if stop.on_request else ""), platform or "")
        if value
    )
    details = f" ({details})" if details else ""

    time = Ansi.wrap(f"{stop.time:>5}", Ansi.MAGENTA)

    return f"{time} | {stop.name}{details}"

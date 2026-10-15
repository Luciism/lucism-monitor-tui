from enum import Enum
from typing import final


VALUE_OFFSET = 40

@final
class Color(Enum):
    """Named colors for the dashboard."""
    Running = "green"
    Degraded = "yellow"
    Offline = "red"
    Loading = "#444444"
    Background = "#0a0a0a"
    CardTitle = "white"
    Accent = "#3e6ce0"

    @staticmethod
    def border_classes() -> str:
        return "\n".join([f"""
            .border-{color.name.lower()} {{
                border: round {color.value};
            }}
        """ for color in Color])


from enum import Enum
from typing import final


VALUE_OFFSET = 40

@final
class Color(Enum):
    """Named colors for the dashboard."""
    Running = "#4ADE80"
    Degraded = "#FACC15"
    Offline = "#F87171"
    Loading = "#94A3B8"
    Background = "#0F172A"
    Surface = "#1E293B"
    CardTitle = "white"
    Accent = "#818CF8"
    Primary = "#38BDF8"

    @staticmethod
    def border_classes() -> str:
        return "\n".join([f"""
            .border-{color.name.lower()} {{
                border: round {color.value};
            }}
        """ for color in Color])


    @staticmethod
    def bg_classes() -> str:
        return "\n".join([f"""
            .bg-{color.name.lower()} {{
                background: {color.value};
            }}
        """ for color in Color])


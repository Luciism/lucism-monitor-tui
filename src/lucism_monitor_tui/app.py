import os
import logging
import argparse
from pathlib import Path
from typing import final, override

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Static, ProgressBar, Label
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
_ = parser.add_argument("--env-file", type=Path, help="Path to a .env file")
args = parser.parse_args()

if args.env_file:
    if not args.env_file.is_file():
        parser.error(f"env file not found: {args.env_file}")
    _ = load_dotenv(args.env_file, override=False)

from .projects import dark_smp, statalytics, enotify, islestats
from .projects.style import Color


logging.basicConfig(
    level=logging.INFO,
    # handlers=[],
    handlers=[logging.FileHandler("tui.log")],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

_is_exit_allowed = os.getenv("ALLOW_EXIT", "1")
IS_EXIT_ALLOWED = int(_is_exit_allowed) if _is_exit_allowed.isnumeric() else 1
logging.info(f"IS_EXIT_ALLOWED: {type(IS_EXIT_ALLOWED)}({IS_EXIT_ALLOWED})")

@final
class PlaceholderServiceCard(Static):
    """One bordered panel representing a single service's status."""

    def __init__(self, name: str, status: str, cpu: int, mem: int) -> None:
        super().__init__()
        self.service_name = name
        self.status = status
        self.cpu = cpu
        self.mem = mem

    @override
    def compose(self) -> ComposeResult:
        yield Label(f"[b]{self.service_name}[/b]  [{self.status}]", classes="card-title")
        yield Label("CPU")
        yield ProgressBar(total=100, show_eta=False)
        yield Label("Memory")
        yield ProgressBar(total=100, show_eta=False)

    def on_mount(self) -> None:
        bars = self.query(ProgressBar)
        bars[0].update(progress=self.cpu)
        bars[1].update(progress=self.mem)


@final
class ServiceDashboard(App[None]):
    """A grid of service status panels, similar in spirit to the screenshot."""

    def __init__(self):
        super().__init__()
    _inherit_bindings = False

    @override
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if not IS_EXIT_ALLOWED and action in ("quit", "help_quit"):
            return False

        return super().check_action(action, parameters)
    
    CSS: str = f"""
        Screen {{
            background: {Color.Background.value};
        }}
        ProjectCard, PlaceholderServiceCard, ProjectCardBase {{
            border: round {Color.Loading.value};
            padding: 1 2;
            height: auto;
            margin: 1;
        }}
        .card-title {{
            color: {Color.CardTitle.value};
        }}
        #grid {{
            layout: grid;
            grid-size: 4;
            grid-gutter: 1;
        }}

        .detail-label-horizontal {{
            width: 100%;
            height: auto;
        }}

        Rule {{
            margin: 0 0;
            height: 2;
            color: {Color.Primary.value};
        }}

        .rule-label {{
            color: {Color.Primary.value};
            text-style: italic;
        }}

        .rule-labels-horizontal {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: auto;
        }}

        .horizontal-spacer {{
            width: 1fr;
        }}

        .vertical-spacer {{
            height: 1fr;
        }}

        .vertical-spacer-small {{
            height: 3;
        }}

        Vertical, Horizontal {{
            height: auto;
        }}

        .pre-selected-button {{
            border: none;
            height: 0;
            width: 0;
        }}

        Button {{
            width: 1fr;
            height: 3;
            background: transparent;
            border: round {Color.Accent.value};
        }}

        .project-card-logs {{
            height: 1fr;
            min-height: 6;
            margin: 1 0;
            padding: 0 1;
            color: {Color.Loading.value};
            background: {Color.Surface.value};
            border: round {Color.Loading.value};
            scrollbar-size: 0 0;
        }}

        .section-a {{
            height: 10;
        }}
        .section-b {{
            # position: relative;
            # offset: 0 14;
            # background: red;
        }}
        
        {Color.border_classes()}
        {Color.bg_classes()}
    """

    @override
    def compose(self) -> ComposeResult:
        yield Button("", classes="pre-selected-button")
        with Container(id="grid"):
            yield statalytics.ProjectCard()
            yield islestats.ProjectCard()
            yield enotify.ProjectCard()
            yield dark_smp.ProjectCard()



app = ServiceDashboard()

def main() -> None:
    app.run()


if __name__ == "__main__":
    main()

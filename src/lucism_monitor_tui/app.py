import logging
from typing import final, override

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static, ProgressBar, Label


from .projects import dark_smp, statalytics
from .projects.style import Color


logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.FileHandler("tui.log")],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

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

    CSS: str = f"""
        Screen {{
            background: {Color.Background.value};
        }}
        ProjectCard, PlaceholderServiceCard {{
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
            grid-size: 2;
            grid-gutter: 1;
        }}

        {Color.border_classes()}
    """

    BINDINGS = [("^q", "quit", "Quit")]

    @override
    def compose(self) -> ComposeResult:
        # yield Header(show_clock=True)
        with Container(id="grid"):
            yield statalytics.ProjectCard()
            yield dark_smp.ProjectCard()

        # yield Footer()


app = ServiceDashboard()

def main() -> None:
    app.run()


if __name__ == "__main__":
    main()

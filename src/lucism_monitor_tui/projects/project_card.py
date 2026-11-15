import os
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, final, override

from textual.containers import Horizontal, Vertical
from textual.widgets import Rule, Static, Label

from .style import Color, VALUE_OFFSET


class ProjectCardBase(Static):
    def __init__(self, project_name: str, last_updated_at: str="") -> None:
        super().__init__()
        self.border_title: str = project_name 

        if last_updated_at:
            self.set_last_updated_at(last_updated_at) 

    def set_last_updated_at(self, last_updated_at: str) -> None:
        self.border_subtitle: str = f"Updated at {last_updated_at}"

    def set_border_color(self, color: Color) -> None:
        _ = self.remove_class(*["border-" + color.name.lower() for color in Color])
        _ = self.add_class(f"border-{color.name.lower()}")

@dataclass
class DetailLabelEntry:
    id: str
    name: str
    icon: str


def build_detail_label(
    service: DetailLabelEntry,
    status: str,
    color: str
) -> str:
    if int(os.environ["USE_NERD_ICONS"]):
        service_name = f"{service.icon}  {service.name}"
    else:
        service_name = f"◆  {service.name}"

    extra_space = VALUE_OFFSET - len(service_name)
    return f"[b]{service_name}[/b][#222222] {'.' * (extra_space - 2)} [/][{color}]{status}[/]"

class LabelWrapper:
    def __init__(
        self,
        label_entry: DetailLabelEntry,
        text: str="",
        color: Color | None=None
    ) -> None:
        self._label_entry: DetailLabelEntry = label_entry
        self._text: str = text
        self._color: Color = color or Color.Loading

        self._value_label: Label = Label(f"[{self._color.value}]{self._text}[/]")

        if int(os.environ["USE_NERD_ICONS"]):
            service_name = f"{label_entry.icon}  {label_entry.name}"
        else:
            service_name = f"◆  {label_entry.name}"

        self._label: Horizontal = Horizontal(
            Label(f"[b]{service_name}[/]"),
            Static("", classes="horizontal-spacer"),
            self._value_label,
            classes="detail-label-horizontal"
        )

    def update_detail(
        self,
        text: str | None=None,
        color: Color | None=None
    ) -> None:
        if text:
            self._text = text
        if color:
            self._color = color

        self._value_label.update(f"[{self._color.value}]{self._text}[/]")

    def set_loading(self) -> Horizontal:
        self.update_detail(text="Loading", color=Color.Loading)
        return self.label

    @property
    def label(self) -> Horizontal:
        return self._label

@dataclass
class ServiceStatus:
    healthy: bool
    status: str
    color: str

    @staticmethod
    def as_healthy() -> 'ServiceStatus':
        return ServiceStatus(healthy=True, status="Running", color=Color.Running.value)

    @staticmethod
    def as_unhealthy() -> 'ServiceStatus':
        return ServiceStatus(healthy=False, status="Offline", color=Color.Offline.value)

    @staticmethod
    def as_loading() -> 'ServiceStatus':
        return ServiceStatus(healthy=False, status="Fetching...", color=Color.Loading.value)

def strf_seconds(seconds: int) -> str:
    if seconds < 60:
        return f"{round(seconds)}s"
    
    if seconds < 60 * 60:
        return f"{round(seconds / 60)}m"
    
    if seconds < 24 * 60 * 60:
        return f"{round(seconds / 60 / 60)}h"
    
    return f"{round(seconds / 60 / 60 / 24)}d"

@final
class Ticker(Label):
    def __init__(
        self,
        ticker_type: Literal["past", "future"],
        ticker_timestamp: float | None,
        ticker_interval: int=1
    ) -> None:
        super().__init__("")

        self.ticker_type = ticker_type
        self._ticker_timestamp = ticker_timestamp
        self.ticker_interval = ticker_interval

    def format_time(self, formatted_time_delta: str) -> str:
        if self.ticker_type == "past":
            return f"{formatted_time_delta} ago"

        return f"in {formatted_time_delta}"

    def _tick(self) -> None:
        if self._ticker_timestamp is None:
            self.update("")
            return

        now = datetime.now().timestamp()
        formatted_delta = strf_seconds(int(now - self._ticker_timestamp))

        self.update(self.format_time(formatted_delta))

    def on_mount(self) -> None:
        self._tick()
        _ = self.set_interval(self.ticker_interval, self._tick)

    def set_timestamp(self, timestamp: float) -> None:
        self._ticker_timestamp = timestamp


@final
class SectionHeading(Vertical):
    def __init__(self, title: str, updated_at: datetime | None=None) -> None:
        super().__init__(classes="section-heading")
        self.title = title
        self._updated_at = updated_at

        self._updated_label = Label("", classes="rule-label")

        self._ticker = Ticker(
            "past",
            updated_at.timestamp() if updated_at else None,
        )
        self._ticker.classes = "rule-label"

        def format_time(formatted_time_delta: str) -> str:
            return f"Updated {formatted_time_delta} ago"
        self._ticker.format_time = format_time

    @override
    def compose(self):
        with Horizontal(classes="rule-labels-horizontal"):
            yield Label(self.title, classes="rule-label")
            yield Static("", classes="horizontal-spacer")
            # yield self._updated_label
            yield self._ticker
        yield Rule()

    # def _updated_at_str(self) -> str:
    #     if self._updated_at is None:
    #         return ""
    #
    #     timestamp = self._updated_at.strftime("%H:%M")
    #     return f"Updated at {timestamp}"

    # def _tick(self) -> None:
    #     if self._updated_at is None:
    #         self._updated_label.update("")
    #         return
    #
    #     now = datetime.now().timestamp()
    #     updated_at = self._updated_at.timestamp()
    #     self._updated_label.update(f"Updated {strf_seconds(int(now - updated_at))} ago")

    def set_updated_at(self, updated_at: datetime) -> None:
        self._updated_at = updated_at
        self._ticker.set_timestamp(updated_at.timestamp())
        # self._updated_label.update(self._updated_at_str())

    # def on_mount(self) -> None:
    #     _ = self.set_interval(self.ticker_interval, self._tick)

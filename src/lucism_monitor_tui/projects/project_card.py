from dataclasses import dataclass

from textual.widgets import Static, Label

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
    service_name = f"{service.icon}  {service.name}"
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
        self._label: Label = Label(build_detail_label(
            self._label_entry,
            self._text,
            self._color.value
        ))

    def update_detail(
        self,
        text: str | None=None,
        color: Color | None=None
    ) -> None:
        if text:
            self._text = text
        if color:
            self._color = color

        self._label.update(build_detail_label(self._label_entry, self._text, self._color.value))

    def set_loading(self) -> Label:
        self.update_detail(text="Loading", color=Color.Loading)
        return self.label

    @property
    def label(self) -> Label:
        return self._label

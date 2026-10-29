"""Dropdown family: one base skeleton + two concrete variants.

    BaseDropdownFrame      skeleton, model, single event outlet (never instantiated)
      ├── DropdownFrame       multi-select, removable labels
      └── SimpleDropdownFrame single-select, nothing extra

Hooks: _apply_select / _render_content. Do not override _notify_change.
"""
import logging
from typing import Callable

import customtkinter as tk


class BaseDropdownFrame(tk.CTkFrame):
    def __init__(
        self,
        master_,
        filter_name: str,
        display: str,
        values: list[str],
        on_change: Callable[[str], None] | None = None,
    ):
        _tag = f"[{type(self).__name__}.__init__]"
        super().__init__(master=master_, corner_radius=8)

        self.filter_name: str = filter_name   # data key, never shown
        self.display: str = display           # customer facing label
        self.filter_content: list[str] = []   # current selection
        self.on_change: Callable[[str], None] | None = on_change

        self.title = tk.CTkLabel(master=self, text=display, width=70, anchor='w')
        self.title.pack(side='left', padx=(10, 6), pady=6)

        # one handle only: self.menu
        self.menu = tk.CTkOptionMenu(
            master=self,
            values=values,
            command=self._emit,
            width=110,
        )
        self.menu.pack(side='right', padx=(6, 10), pady=6)
        logging.debug(f"{_tag} {filter_name} values={values} callback={on_change is not None}")

    def _emit(self, selected_value: str) -> None:
        # step 1: mutate the model, step 2: tell the world
        self._apply_select(selected_value)
        self._notify_change('select', selected_value)

    def _notify_change(self, reason: str, selected_value: str = '') -> None:
        """Pass the value that was just picked, NOT the filter_name.

        Passing filter_name here used to break coupon lookups. Subscribers that need
        the full selection should call selected_values() themselves.
        """
        if self.on_change is None:
            logging.debug(f"{self.filter_name} changed to {self.filter_content}, no subscriber")
            return
        logging.debug(f"{self.filter_name} -> {selected_value!r} ({reason})")
        self.on_change(selected_value)

    def selected_values(self) -> list[str]:
        """Copy of the selection, so callers cannot mutate our state."""
        return list(self.filter_content)

    def select(self, value: str = '') -> None:
        """Programmatic selection, same path as a user click."""
        target = value or self.menu.get()
        if value:
            self.menu.set(target)
        self._apply_select(target)
        self._notify_change('select', target)

    def _apply_select(self, selected_value: str) -> None:
        """Default semantics: single select, overwrite."""
        self._update_filter_content([selected_value], 'select-replace')

    def _update_filter_content(self, new_content: list[str], reason: str) -> None:
        """Only way to write filter_content. Writes, logs, re-renders."""
        old_content = list(self.filter_content)
        if old_content == new_content:
            return
        self.filter_content = list(new_content)
        logging.debug(f"{self.filter_name} {reason}: {old_content} -> {self.filter_content}")
        self._render_content(reason)

    def _render_content(self, reason: str) -> None:
        """Projection hook. No-op for single select."""
        logging.debug(f"{type(self).__name__} no projection ({reason})")


class DropdownFrame(BaseDropdownFrame):
    """Multi-select: each pick appends a removable label."""

    def __init__(self, master_, filter_name: str, display: str, values: list[str], on_change: Callable[..., None]):
        super().__init__(master_=master_, filter_name=filter_name, display=display, values=values, on_change=on_change)
        self.filters: list[tk.CTkLabel] = []
        self.delete_btn = tk.CTkButton(
            master=self,
            text='delete',
            width=64,
            command=self._on_user_delete
        )
        # menu is already packed right, so delete lands to its left
        self.delete_btn.pack(side='right', padx=(0, 0), pady=6)

    def _apply_select(self, selected_value: str) -> None:
        # accumulate, dedupe at model level so the UI never flickers
        if selected_value in self.filter_content:
            logging.debug(f"{self.filter_name} already has {selected_value!r}")
            return
        self._update_filter_content([*self.filter_content, selected_value], 'select-append')

    def _render_content(self, reason: str) -> None:
        wanted = list(self.filter_content)

        # drop labels that left the model
        for label in tuple(self.filters):
            label_text = label.cget('text')
            if label_text in wanted:
                continue
            logging.debug(f"{self.filter_name} drop label {label_text!r}")
            label.destroy()
            self.filters.remove(label)

        # add missing ones, ordered by filter_content
        existing_texts = {label.cget('text') for label in self.filters}
        for label_text in wanted:
            if label_text in existing_texts:
                continue
            label = tk.CTkLabel(master=self, text=label_text, corner_radius=6, padx=8)
            # before=self.menu puts it left of menu + delete
            label.pack(side='left', before=self.menu, padx=(0, 4), pady=6)
            self.filters.append(label)
            existing_texts.add(label_text)
        logging.debug(f"{self.filter_name} rendered {wanted} ({reason})")

    def _on_user_delete(self) -> None:
        if not self.filter_content:
            logging.warning(f"{self.filter_name} delete on empty selection")
            return
        new_content = self.filter_content[:-1]
        self._update_filter_content(new_content, 'delete-last')
        # deletes are state changes too; subscribers reread selected_values()
        self._notify_change('delete', '')


class SimpleDropdownFrame(BaseDropdownFrame):
    """Single select straight through. Exists so add_filter(simple=True) gets
    the same data shape without the delete button.
    """

    def __init__(self, master_, filter_name: str, display: str, values: list[str], on_change: Callable[..., None]):
        super().__init__(master_=master_, filter_name=filter_name, display=display, values=values, on_change=on_change)
        # CTkOptionMenu already displays values[0] while filter_content is empty.
        # Sync them or filtering silently disagrees with what the user sees.
        self.select('')
        logging.debug(f"{filter_name} initialised to {self.filter_content}")

    def set_displayed(self, value: str) -> None:
        """Push a value into the menu without firing the callback."""
        self.menu.set(value)
        self._update_filter_content([value], 'set-displayed')

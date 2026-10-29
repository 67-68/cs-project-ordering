"""Back / quit button pair for the page header."""
import logging
from typing import Callable

import customtkinter as tk


class BackFrame(tk.CTkFrame):
    """Both callbacks are optional; without one the button is display only."""

    def __init__(
        self,
        master_,
        on_back: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ):
        super().__init__(master=master_, fg_color="transparent")
        self.backbtn = tk.CTkButton(master=self, text='back', width=64, command=self._on_back_click)
        self.quitbtn = tk.CTkButton(master=self, text='quit', width=64, command=self._on_quit_click)
        self.backbtn.pack(side='left', padx=(0, 6))
        self.quitbtn.pack(side='left', padx=(0, 0))
        self.on_back = on_back
        self.on_quit = on_quit
        logging.debug(f"header built: back={on_back is not None} quit={on_quit is not None}")

    def _on_back_click(self) -> None:
        # None guard stays: unbound button must not raise
        if self.on_back is None:
            logging.warning("back clicked but unbound")
            return
        self.on_back()

    def _on_quit_click(self) -> None:
        if self.on_quit is None:
            logging.warning("quit clicked but unbound")
            return
        self.on_quit()

"""页面顶栏的 back / quit 按钮组。"""
import logging
from typing import Callable

import customtkinter as tk


class BackFrame(tk.CTkFrame):
    """两个按钮的回调都可选: 不传时降级为纯展示, 不会因为 None 在点击时炸。"""

    def __init__(
        self,
        master_,
        on_back: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ):
        logging.debug(f"[BackFrame.__init__] entry on_back={on_back!r} on_quit={on_quit!r}")
        super().__init__(master=master_, fg_color="transparent")
        # 没给 text 的按钮是空白的, 先在视觉上补个占位文案
        self.backbtn = tk.CTkButton(master=self, text='back', width=64, command=self._on_back_click)
        self.quitbtn = tk.CTkButton(master=self, text='quit', width=64, command=self._on_quit_click)
        self.backbtn.pack(side='left', padx=(0, 6))
        self.quitbtn.pack(side='left', padx=(0, 0))
        self.on_back = on_back
        self.on_quit = on_quit
        logging.debug(f"[BackFrame.__init__] exit back_bound={on_back is not None} quit_bound={on_quit is not None}")

    def _on_back_click(self) -> None:
        logging.info(f"[BackFrame._on_back_click] entry bound={self.on_back is not None}")
        if self.on_back is None:
            logging.warning("[BackFrame._on_back_click] branch=no-callback, back 未接")
            return
        self.on_back()

    def _on_quit_click(self) -> None:
        logging.info(f"[BackFrame._on_quit_click] entry bound={self.on_quit is not None}")
        if self.on_quit is None:
            logging.warning("[BackFrame._on_quit_click] branch=no-callback, quit 未接")
            return
        self.on_quit()

"""Order detail page: title bar, actions, info card, dine-in card."""
import logging
from typing import Callable

import customtkinter as tk

from ui.theme import (
    CARD_BORDER,
    CARD_DINE_BG,
    CARD_INFO_BG,
    PAGE_BG,
    SHADOW,
    TEXT_HEADING,
    TEXT_PRIMARY,
    TITLE_BAR_BG,
)


class OrderDetailView(tk.CTkFrame):
    """Displays one FoodInfo; data arrives through load().

    customtkinter has no shadow API, so a dark outer frame with the card sunk 2px
    gives us the hard shadow.
    """

    SHADOW_OFFSET = 2  # px the inner card is inset

    def __init__(self, master, on_pay: Callable[[], None]):
        _tag = "[order]"
        super().__init__(master=master, fg_color=PAGE_BG, corner_radius=12)

        self.on_pay: Callable[[], None] | None = on_pay

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # row0: title bar
        self.title_row = tk.CTkFrame(
            master=self, fg_color=TITLE_BAR_BG, corner_radius=12,
            border_width=1, border_color=CARD_BORDER,
        )
        self.title_row.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 6))
        self.title_row.grid_columnconfigure(0, weight=1)

        self.big_title = tk.CTkLabel(
            master=self.title_row,
            text='(no dish)',
            font=tk.CTkFont(size=36, weight='bold'),
            text_color=TEXT_PRIMARY,
            anchor='w',
            justify='left',
        )
        self.big_title.grid(row=0, column=0, sticky='w', padx=(16, 8), pady=14)

        self.rate_btn = tk.CTkButton(
            master=self.title_row, text='⭐ Rate', width=110, height=46,
            font=tk.CTkFont(size=15, weight='bold'),
            corner_radius=10,
            fg_color=("#E9E9EF", "#2E2E38"),
            text_color=TEXT_PRIMARY,
            hover_color=("#DCDCE4", "#3A3A46"),
            command=self._on_rate_click,
        )
        self.rate_btn.grid(row=0, column=1, padx=(8, 6), pady=14, sticky='e')

        self.pay_btn = tk.CTkButton(
            master=self.title_row, text='💳 Pay', width=110, height=46,
            font=tk.CTkFont(size=16, weight='bold'),
            corner_radius=10,
            command=self._on_pay_click,
        )
        self.pay_btn.grid(row=0, column=2, padx=(0, 16), pady=14, sticky='e')

        # row1 / row2: two cards
        self.info_shell, self.info_body = self._build_card(self, '📋 Basic info', CARD_INFO_BG)
        self.info_shell.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 6))

        self.dine_shell, self.dine_body = self._build_card(
            self, '🍽️ Dine-in / Restaurant info', CARD_DINE_BG,
        )
        self.dine_shell.grid(row=2, column=0, sticky='nsew', padx=10, pady=(0, 10))
        logging.debug(f"{_tag} order view ready, on_pay={on_pay is not None}")

    def _build_card(self, master, heading: str, body_bg: tuple[str, str]) -> tuple[tk.CTkFrame, tk.CTkLabel]:
        """Returns (outer shell, body label). shell for layout, body for text."""
        # outer: flat dark block, only a sliver shows at bottom-right
        shell = tk.CTkFrame(master=master, fg_color=SHADOW, corner_radius=12)

        card = tk.CTkFrame(
            master=shell, fg_color=body_bg, corner_radius=12,
            border_width=1, border_color=CARD_BORDER,
        )
        card.pack(
            fill='both', expand=True,
            padx=(0, self.SHADOW_OFFSET),
            pady=(0, self.SHADOW_OFFSET),
        )

        heading_label = tk.CTkLabel(
            master=card, text=heading, anchor='w',
            font=tk.CTkFont(size=17, weight='bold'),
            text_color=TEXT_HEADING,
        )
        heading_label.pack(side='top', fill='x', padx=16, pady=(14, 6))

        body = tk.CTkLabel(
            master=card,
            text='(no data)',
            anchor='nw',
            justify='left',
            font=tk.CTkFont(size=15),
            text_color=TEXT_PRIMARY,
        )
        body.pack(side='top', fill='both', expand=True, padx=16, pady=(0, 14))
        return shell, body

    def load(self, food) -> None:
        """Project one FoodInfo onto the widgets."""
        _tag = "[order.load]"

        # 36pt only fits ~6 CJK glyphs in a 600px window, so step the size down
        title_text, title_size = self._adaptive_title(food.title)
        self.big_title.configure(text=title_text, font=tk.CTkFont(size=title_size, weight='bold'))

        info_lines = [
            f"Price: {food.price_text}",
            f"Wait: {food.wait_text}",
            f"Distance: {food.distance_text}",
            f"Tags: {food.tag_str or '-'}",
            f"Contains: {', '.join(food.food_component) if food.food_component else '-'}",
        ]
        if food.extra_price_info:
            info_lines.append(f"Extras: {food.extra_price_info}")
        self.info_body.configure(text='\n'.join(info_lines))

        # no dine-in data source yet, but show which dish this is
        self.dine_body.configure(text=f"• {food.title}\n• Restaurant address, info and balance")
        logging.debug(f"{_tag} loaded {food.food_id}, {len(info_lines)} lines, title size {title_size}")

    @staticmethod
    def _adaptive_title(raw_title: str | None) -> tuple[str, int]:
        """Shrink the font first, truncate only as a last resort."""
        if not raw_title:
            logging.warning("empty title, using placeholder")
            return '(untitled)', 36
        length = len(raw_title)
        if length <= 6:
            return raw_title, 36
        if length <= 10:
            return raw_title, 28
        logging.debug(f"title too long ({length}), truncating")
        return raw_title[:10] + '…', 22

    def _on_rate_click(self) -> None:
        # TODO: rating dialog
        logging.info("rate clicked")

    def _on_pay_click(self) -> None:
        if self.on_pay is None:
            logging.error("pay clicked but unbound")
            return
        self.on_pay()

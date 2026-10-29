import logging
from typing import Any, Callable

import customtkinter as tk

from food_model import FoodInfo


class PolishedFoodCard(tk.CTkFrame):
    @classmethod
    def from_food_info(
        cls,
        master: Any,  # CTkScrollableFrame is not a CTkBaseClass, so keep it loose
        info: FoodInfo,
        on_order_click: Callable[[int], None],
    ) -> "PolishedFoodCard":
        """Build straight from the model instead of unrolling 9 args at the call site."""
        logging.debug(f"card build: {info.food_id} {info.title}")
        return cls(
            master=master,
            food_id=info.food_id,
            title=info.title,
            tag_str=info.tag_str,
            wait_mins=info.wait_mins,
            distance_km=info.distance_km,
            base_price=info.base_price,
            extra_price_info=info.extra_price_info,
            crowd_color=info.crowd_color,
            on_order_click=on_order_click,
        )

    def __init__(
        self,
        master: Any,
        food_id: int,
        title: str,
        tag_str: str,           # e.g. "low caffeine"
        wait_mins: int,         # 32 -> "32min"
        distance_km: int,       # 32 -> "32km"
        base_price: int,        # 32 -> "32¥"
        extra_price_info: str,  # e.g. "to 52¥ (extra)"
        crowd_color: str,       # crowd badge hex
        on_order_click: Callable[[int], None]
    ):
        # big radius + hairline border + inner padding, that's the whole look
        super().__init__(
            master,
            corner_radius=16,
            fg_color=("#FFFFFF", "#1E1E24"),
            border_width=1,
            border_color=("#E5E5EA", "#2E2E38")
        )
        self.food_id = food_id
        self.on_click: Callable = on_order_click

        self.grid_columnconfigure((0, 2, 3), weight=0)
        self.grid_columnconfigure(1, weight=1)

        clean_title, title_font_size = self._compute_adaptive_title(title)
        self.lbl_title = tk.CTkLabel(
            self, text=clean_title,
            font=tk.CTkFont(size=title_font_size, weight='bold')
        )
        self.lbl_title.grid(row=0, column=0, padx=(16, 6), pady=(12, 2), sticky='sw')

        self.lbl_tag = tk.CTkLabel(
            self, text=tag_str,
            font=tk.CTkFont(size=13),
            text_color=("#6C6C70", "#8E8E93")
        )
        self.lbl_tag.grid(row=0, column=1, padx=4, pady=(12, 5), sticky="sw")

        self.lbl_price = tk.CTkLabel(
            self, text=f"{base_price}¥",
            font=tk.CTkFont(size=28, weight="bold")
        )
        self.lbl_price.grid(row=0, column=2, padx=12, pady=(12, 0), sticky="se")

        self.badge_time = tk.CTkLabel(
            self, text=f"{wait_mins}min",
            font=tk.CTkFont(size=12, weight="bold"),
            fg_color=crowd_color, text_color="#FFFFFF",
            corner_radius=6, padx=8, pady=2
        )
        # nw anchor keeps it glued next to the distance label
        self.badge_time.grid(row=1, column=0, padx=(16, 6), pady=(4, 12), sticky="nw")

        self.lbl_distance = tk.CTkLabel(master=self, text=str(distance_km))
        self.lbl_distance.grid(row=1, column=1, padx=4, pady=(4, 12), sticky='nw')

        self.lbl_extra = tk.CTkLabel(master=self, text=extra_price_info)
        self.lbl_extra.grid(row=1, column=2, padx=12, pady=(4, 12), sticky='ne')

        self.btn_order = tk.CTkButton(
            self, text="+", width=44, height=44, corner_radius=12,
            font=tk.CTkFont(size=20, weight="bold"),
            command=self._on_btn_pressed
        )
        self.btn_order.grid(row=0, column=3, rowspan=2, padx=(4, 16), pady=12, sticky="ns")

    def _compute_adaptive_title(self, raw_title: str) -> tuple[str, int]:
        """O(1) staircase instead of live pixel measuring."""
        return (raw_title, 26) if len(raw_title) <= 5 else (raw_title, 20) if len(raw_title) < 8 else (raw_title[:8] + '...', 18)

    def _on_btn_pressed(self) -> None:
        logging.info(f"order triggered: {self.food_id}")
        self.on_click(self.food_id)

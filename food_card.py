import customtkinter as tk
import logging
from typing import Any, Callable, Tuple

from food_model import FoodInfo

class PolishedFoodCard(tk.CTkFrame):
    @classmethod
    def from_food_info(
        cls,
        master: "tk.CTkBaseClass",
        info: FoodInfo,
        on_order_click: Callable[[int], None],
    ) -> "PolishedFoodCard":
        """用数据模型直接构造卡片, 避免调用方手工摊开 8 个参数。"""
        logging.debug(f"[PolishedFoodCard.from_food_info] entry food_id={info.food_id!r} title={info.title!r}")
        card = cls(
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
        logging.debug(f"[PolishedFoodCard.from_food_info] exit food_id={info.food_id!r}")
        return card

    def __init__(
        self, 
        master: tk.CTkBaseClass, 
        food_id: int,
        title: str,
        tag_str: str,       # 如: "低咖啡因"
        wait_mins: int,     # 如: 32 -> "32min"[cite: 2]
        distance_km: int,   # 如: 32 -> "32km"[cite: 2]
        base_price: int,    # 如: 32 -> "32¥"[cite: 2]
        extra_price_info: str, # 如: "to 52$(配料)"[cite: 2]
        crowd_color: str,   # 拥挤度颜色方块 HEX[cite: 2]
        on_order_click: Callable[[int], None]
    ):
        # Level 2 精致度契约：大圆角 (16) + 1px 极细微边框 + 内部呼吸感内边距
        super().__init__(
            master, 
            corner_radius=16, 
            fg_color=("#FFFFFF", "#1E1E24"), 
            border_width=1, 
            border_color=("#E5E5EA", "#2E2E38")
        )
        self.food_id = food_id

        self.on_click: Callable = on_order_click
        self.grid_columnconfigure((0,2,3), weight=0)
        self.grid_columnconfigure(1,weight=1)
        clean_title, title_font_size = self._compute_adaptive_title(title)
        self.lbl_title = tk.CTkLabel(
            self, text=clean_title,
            font=tk.CTkFont(size=title_font_size,weight='bold')
        )
        self.lbl_title.grid(row=0,column=0,padx=(16,6),pady=(12,2), sticky='sw')

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


        # 颜色小方块 (32min 餐厅拥挤度胶囊)
        self.badge_time = tk.CTkLabel(
            self, text=f"{wait_mins}min",
            font=tk.CTkFont(size=12, weight="bold"),
            fg_color=crowd_color, text_color="#FFFFFF",
            corner_radius=6, padx=8, pady=2
        )
        # sticky="nw" 锁死在左上，绝不会跟旁边的 32km 失散[cite: 2]！
        self.badge_time.grid(row=1, column=0, padx=(16, 6), pady=(4, 12), sticky="nw")
        
        self.lbl_distance = tk.CTkLabel(
            self, text=str(distance_km),
            row=1, col=1, sticky='nw'
        )

        self.lbl_extra = tk.CTkLabel(extra_price_info, row=1, col=2, sticky = 'ne')

        self.btn_order = tk.CTkButton(
            self, text="+", width=44, height=44, corner_radius=12,
            font=tk.CTkFont(size=20, weight="bold"),
            command=self._on_btn_pressed
        )
        self.btn_order.grid(row=0, column=3, rowspan=2, padx=(4, 16), pady=12, sticky="ns")

    def _compute_adaptive_title(self, raw_title: str) -> tuple[str, int]:
        """用 O(1) 的阶梯状态机代替蠢爆了的实时像素测量 🤓☝️"""
        if not raw_title:
            logging.error(f"[PolishedFoodCard] Empty title for food_id={self.food_id}!")
            return ("Unknown", 20)
        return (raw_title, 26) if len(raw_title) <= 5 else (raw_title,20) if len(raw_title) < 8 else (raw_title[:8] + '...',18)

    def _on_btn_pressed(self) -> None:
        logging.info(f"[B2 Action] Order triggered for food_id={self.food_id}")
        self.on_click()
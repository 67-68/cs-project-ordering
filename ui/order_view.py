"""订单详情页: 大标题 + 评价/支付动作 + 基本信息 + 堂食信息。"""
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
    """只负责"展示一条 FoodInfo", 不持有数据源; 数据由 load() 灌进来。

    customtkinter 没有阴影 API, 所以用"外层深色 frame + 内层卡片右下沉 2px"模拟硬阴影。
    """

    SHADOW_OFFSET = 2  # 内层卡片相对外层往右下缩进的像素, 露出的部分就是"影子"

    def __init__(self, master, on_pay: Callable[[], None]):
        _tag = "[OrderDetailView.__init__]"
        logging.debug(f"{_tag} entry master={master!r} on_pay={on_pay!r}")
        # 整页铺一层比卡片更深的底色, 卡片才浮得起来
        super().__init__(master=master, fg_color=PAGE_BG, corner_radius=12)

        # 回调存成实例属性: _on_pay_click 里要用它, 光传不进 self 就是个死参数
        self.on_pay: Callable[[], None] | None = on_pay

        # row0 标题行固定高度, row1/row2 平分剩余空间
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ---------- row0: 标题栏(独立底色, 与下面两块卡片区分) ----------
        self.title_row = tk.CTkFrame(
            master=self, fg_color=TITLE_BAR_BG, corner_radius=12,
            border_width=1, border_color=CARD_BORDER,
        )
        self.title_row.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 6))
        self.title_row.grid_columnconfigure(0, weight=1)  # 标题吃掉剩余宽度

        self.big_title = tk.CTkLabel(
            master=self.title_row,
            text='(no dish)',
            font=tk.CTkFont(size=36, weight='bold'),
            text_color=TEXT_PRIMARY,
            anchor='w',
            justify='left',
        )
        self.big_title.grid(row=0, column=0, sticky='w', padx=(16, 8), pady=14)
        logging.debug(f"{_tag} branch=big-title-gridded font_size=36")

        # 先 grid 的更靠左: 评价在左, 支付在右
        self.rate_btn = tk.CTkButton(
            master=self.title_row, text='⭐ 评价', width=110, height=46,
            font=tk.CTkFont(size=15, weight='bold'),
            corner_radius=10,
            fg_color=("#E9E9EF", "#2E2E38"),
            text_color=TEXT_PRIMARY,
            hover_color=("#DCDCE4", "#3A3A46"),
            command=self._on_rate_click,
        )
        self.rate_btn.grid(row=0, column=1, padx=(8, 6), pady=14, sticky='e')

        self.pay_btn = tk.CTkButton(
            master=self.title_row, text='💳 支付', width=110, height=46,
            font=tk.CTkFont(size=16, weight='bold'),
            corner_radius=10,
            command=self._on_pay_click,
        )
        self.pay_btn.grid(row=0, column=2, padx=(0, 16), pady=14, sticky='e')
        logging.debug(f"{_tag} branch=action-buttons-gridded btn_size=110x46")

        # ---------- row1: 基本信息 ----------
        self.info_shell, self.info_body = self._build_card(self, '📋 基本信息', CARD_INFO_BG)
        self.info_shell.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 6))

        # ---------- row2: 堂食信息 ----------
        self.dine_shell, self.dine_body = self._build_card(
            self, '🍽️ 堂食 / 餐厅信息 (At Restaurant)', CARD_DINE_BG,
        )
        self.dine_shell.grid(row=2, column=0, sticky='nsew', padx=10, pady=(0, 10))
        logging.debug(f"{_tag} exit cards=2 shadow_offset={self.SHADOW_OFFSET}")

    def _build_card(self, master, heading: str, body_bg: tuple[str, str]) -> tuple[tk.CTkFrame, tk.CTkLabel]:
        """造一张"带阴影的卡片": 外层深色当影子, 内层亮色当卡片表面。

        返回 (外层 shell, 正文 label)。shell 用于 grid 定位, 正文往里写文字。
        """
        _tag = "[OrderDetailView._build_card]"
        logging.debug(f"{_tag} entry heading={heading!r} body_bg={body_bg!r}")

        # 外层: 纯色深底, 不需要圆角对齐, 它只会在右下露出一条边
        shell = tk.CTkFrame(master=master, fg_color=SHADOW, corner_radius=12)

        # 内层: 真正呈现给用户的卡片表面, 往左上偏移 -> 右下露出 SHADOW_OFFSET 像素
        card = tk.CTkFrame(
            master=shell, fg_color=body_bg, corner_radius=12,
            border_width=1, border_color=CARD_BORDER,
        )
        card.pack(
            fill='both', expand=True,
            padx=(0, self.SHADOW_OFFSET),   # 右边留出影子
            pady=(0, self.SHADOW_OFFSET),   # 下边留出影子
        )
        logging.debug(f"{_tag} branch=card-packed padx={self.SHADOW_OFFSET} pady={self.SHADOW_OFFSET}")

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
        logging.debug(f"{_tag} exit heading_size=17 body_size=15")
        return shell, body

    def load(self, food) -> None:
        """把一条 FoodInfo 投影到界面。所有分支都留日志。"""
        _tag = "[OrderDetailView.load]"
        logging.debug(f"{_tag} entry food_id={getattr(food, 'food_id', None)!r} title={getattr(food, 'title', None)!r}")

        # 36pt 在 600px 窗口里只放得下 6 个中文字, 超了会把按钮挤出界 -> 阶梯降字号
        title_text, title_size = self._adaptive_title(food.title)
        self.big_title.configure(text=title_text, font=tk.CTkFont(size=title_size, weight='bold'))
        logging.debug(f"{_tag} branch=title-set text={title_text!r} font_size={title_size} raw_len={len(food.title or '')}")

        # 基本信息: 用模型里的派生 property, 不要在 UI 层重新格式化
        info_lines = [
            f"价格: {food.price_text}",
            f"等待: {food.wait_text}",
            f"距离: {food.distance_text}",
            f"标签: {food.tag_str or '-'}",
            f"配料: {'、'.join(food.food_component) if food.food_component else '-'}",
        ]
        if food.extra_price_info:
            info_lines.append(f"加料: {food.extra_price_info}")
            logging.debug(f"{_tag} branch=has-extra extra={food.extra_price_info!r}")
        else:
            logging.debug(f"{_tag} branch=no-extra")
        self.info_body.configure(text='\n'.join(info_lines))
        logging.debug(f"{_tag} branch=info-set lines={len(info_lines)}")

        # 堂食区目前没有数据源, 保留占位但把菜品名带进去, 免得顾客看不出在哪个菜上
        self.dine_body.configure(text=f"• {food.title}\n• 餐厅地址，信息和平衡")
        logging.debug(f"{_tag} exit food_id={food.food_id!r}")

    @staticmethod
    def _adaptive_title(raw_title: str | None) -> tuple[str, int]:
        """阶梯状态机代替像素测量: 先缩字号, 缩到头才截断 —— 比一上来就加省略号好读。"""
        if not raw_title:
            logging.warning("[OrderDetailView._adaptive_title] branch=empty-title, 降级为占位文案")
            return '(untitled)', 36
        length = len(raw_title)
        if length <= 6:
            logging.debug(f"[OrderDetailView._adaptive_title] branch=short len={length} size=36")
            return raw_title, 36
        if length <= 10:
            logging.debug(f"[OrderDetailView._adaptive_title] branch=medium len={length} size=28")
            return raw_title, 28
        logging.debug(f"[OrderDetailView._adaptive_title] branch=long len={length} size=22, 截断到 10 字")
        return raw_title[:10] + '…', 22

    def _on_rate_click(self) -> None:
        logging.info("[OrderDetailView._on_rate_click] branch=rate-clicked")
        # TODO: 接评价弹窗/页面, 当前只留痕

    def _on_pay_click(self) -> None:
        logging.info(f"[OrderDetailView._on_pay_click] branch=pay-clicked has_callback={self.on_pay is not None}")
        if self.on_pay is None:
            logging.error("[OrderDetailView._on_pay_click] branch=no-callback, 支付按钮无响应")
            return
        self.on_pay()

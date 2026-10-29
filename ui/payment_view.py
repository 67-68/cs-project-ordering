"""支付页: payment 标题 + 支付方式 dropdown + 优惠券 dropdown + 等待提示 + pay 按钮。"""
import logging
from typing import Any, Callable

import customtkinter as tk

from food_model import AppData
from ui.filters import SimpleDropdownFrame
from ui.theme import (
    CARD_BORDER,
    CARD_DINE_BG,
    CARD_INFO_BG,
    NO_COUPON,
    PAGE_BG,
    PAYMENT_METHODS,
    TEXT_HEADING,
    TEXT_PRIMARY,
    TITLE_BAR_BG,
)


class PaymentView(tk.CTkFrame):
    """两个 dropdown 各自独立: 支付方式用原生 CTkOptionMenu, 优惠券复用 SimpleDropdownFrame。

    状态全部落在 _state 里, _recompute() 是唯一的汇总出口。
    """

    def __init__(self, master, data: AppData, on_paid: Callable[[int], None] | None = None):
        _tag = "[PaymentView.__init__]"
        logging.debug(f"{_tag} entry master={master!r} foods={len(data.foods)} coupons={len(data.coupons)}")
        super().__init__(master=master, fg_color=PAGE_BG, corner_radius=12)

        self.data = data
        self.on_paid = on_paid

        # ---- 状态: 单一真相, 所有 UI 都由它推导 ----
        self._state: dict[str, Any] = {
            'food': None,
            'method': '',
            'coupon': None,
            'total': 0,
            'cut': 0,
            'payable': 0,
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # 中间空白区吃掉多余高度, 把 pay 按钮压到底

        # ---------- row0: payment 标题(header 文案就是 payment) ----------
        self.header = tk.CTkFrame(
            master=self, fg_color=TITLE_BAR_BG, corner_radius=12,
            border_width=1, border_color=CARD_BORDER,
        )
        self.header.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 6))
        self.header.grid_columnconfigure(0, weight=1)

        self.title_label = tk.CTkLabel(
            master=self.header,
            text='payment',
            font=tk.CTkFont(size=32, weight='bold'),
            text_color=TEXT_PRIMARY,
            anchor='w',
        )
        self.title_label.grid(row=0, column=0, sticky='w', padx=(16, 8), pady=14)
        logging.debug(f"{_tag} branch=header-gridded text='payment'")

        # ---------- row1: 支付方式 + 优惠券(同一个卡片里) ----------
        self.method_card = tk.CTkFrame(
            master=self, fg_color=CARD_INFO_BG, corner_radius=12,
            border_width=1, border_color=CARD_BORDER,
        )
        self.method_card.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 6))
        self.method_card.grid_columnconfigure(1, weight=1)

        label_font = tk.CTkFont(size=15, weight='bold')

        self.method_label = tk.CTkLabel(
            master=self.method_card, text='method of payment',
            font=label_font, text_color=TEXT_HEADING, anchor='w',
        )
        self.method_label.grid(row=0, column=0, sticky='w', padx=(16, 10), pady=(16, 6))

        self.method_menu = tk.CTkOptionMenu(
            master=self.method_card,
            values=PAYMENT_METHODS,
            command=self._on_method_change,
            width=160, height=36, corner_radius=8,
        )
        self.method_menu.grid(row=0, column=1, sticky='e', padx=(0, 16), pady=(16, 6))
        logging.debug(f"{_tag} branch=method-built values={PAYMENT_METHODS!r}")

        self.coupon_label = tk.CTkLabel(
            master=self.method_card, text='use coupon',
            font=label_font, text_color=TEXT_HEADING, anchor='w',
        )
        self.coupon_label.grid(row=1, column=0, sticky='w', padx=(16, 10), pady=(0, 16))

        # 优惠券下拉: 用 BaseDropdownFrame 的 simple 变体, 与筛选条共用同一套骨架。
        # 「无券」放在第一位: 默认选中它, 语义上是"不使用优惠券", 而不是默认就打折。
        coupon_values = [NO_COUPON] + [c.display for c in data.coupons]
        logging.debug(f"{_tag} branch=coupon-values values={coupon_values!r}")
        # 构造期间 dropdown 会立刻 select 默认值并回调, 那时 summary_label 还没建出来;
        # 先挂一个空回调占位, 界面搭完再换成真正的处理器。
        self.coupon_dropdown = SimpleDropdownFrame(
            master_=self.method_card,
            filter_name='coupon',
            display='',
            values=coupon_values,
            on_change=lambda _v: logging.debug(f"{_tag} branch=early-coupon-callback ignored value={_v!r}, summary 尚未建好"),
        )
        self.coupon_dropdown.grid(row=1, column=1, sticky='e', padx=(0, 16), pady=(0, 16))
        # 这个下拉的标题已经在左侧 label 里了, 内建 title 要隐藏, 否则会出现两条重复文案
        self.coupon_dropdown.title.pack_forget()
        logging.debug(f"{_tag} branch=coupon-built inner_title_hidden=True default={coupon_values[0]!r}")

        # ---------- row2: 金额明细 ----------
        self.summary_card = tk.CTkFrame(
            master=self, fg_color=CARD_DINE_BG, corner_radius=12,
            border_width=1, border_color=CARD_BORDER,
        )
        self.summary_card.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 6))
        self.summary_card.grid_columnconfigure(0, weight=1)

        self.wait_label = tk.CTkLabel(
            master=self.summary_card,
            text='expect wait until ....',
            font=tk.CTkFont(size=18, weight='bold'),
            text_color=TEXT_PRIMARY,
            anchor='w', justify='left',
        )
        self.wait_label.grid(row=0, column=0, sticky='w', padx=16, pady=(14, 4))

        self.summary_label = tk.CTkLabel(
            master=self.summary_card,
            text='total 0¥  ·  coupon -0¥  ·  payable 0¥',
            font=tk.CTkFont(size=14),
            text_color=TEXT_HEADING,
            anchor='w', justify='left',
        )
        self.summary_label.grid(row=1, column=0, sticky='w', padx=16, pady=(0, 14))
        logging.debug(f"{_tag} branch=summary-built")

        # ---------- row4(网格底部): pay 按钮 ----------
        self.pay_btn = tk.CTkButton(
            master=self, text='pay',
            height=52, corner_radius=10,
            font=tk.CTkFont(size=18, weight='bold'),
            command=self._on_pay_click,
        )
        self.pay_btn.grid(row=4, column=0, sticky='ew', padx=10, pady=(0, 10))
        logging.debug(f"{_tag} exit grid_rows=5")

        # 界面全部就位, 此时才把真实的优惠券处理器接上
        self.coupon_dropdown.on_change = self._on_coupon_change
        logging.debug(f"{_tag} branch=coupon-handler-bound callback={self._on_coupon_change!r}")

    # ---------------- 数据入口 ----------------

    def load(self, food) -> None:
        """进入支付页时灌入菜品, 并按该菜品重算金额。"""
        _tag = "[PaymentView.load]"
        logging.debug(f"{_tag} entry food_id={getattr(food, 'food_id', None)!r} title={getattr(food, 'title', None)!r}")
        self._state['food'] = food
        self._state['total'] = int(getattr(food, 'base_price', 0) or 0)
        logging.debug(f"{_tag} branch=total-set total={self._state['total']!r}")
        self._reset_ui()
        self._recompute('load-food')

    def _reset_ui(self) -> None:
        # 换菜品时把上一单的选择清掉, 否则会拿着一杯咖啡的券去付一碗面
        _tag = "[PaymentView._reset_ui]"
        logging.debug(f"{_tag} entry method={self._state['method']!r} coupon={self._state['coupon']!r} before_total={self._state['total']!r}")
        self._state['method'] = ''
        self._state['coupon'] = None
        # 菜单显示也要一起回默认, 否则界面还挂着上一单的支付方式/券, 但模型已经清空了
        if PAYMENT_METHODS:
            self.method_menu.set(PAYMENT_METHODS[0])
            logging.debug(f"{_tag} branch=method-menu-reset displayed={PAYMENT_METHODS[0]!r}")
        else:
            logging.warning(f"{_tag} branch=no-payment-methods, 支付方式列表为空")
        if self.coupon_dropdown is not None:
            # 显式指回"不使用优惠券", 而不是传空串 —— 空串在 select() 里表示"沿用菜单现值",
            # 会把上一单的券原样留下来
            self.coupon_dropdown.select(NO_COUPON)
            logging.debug(f"{_tag} branch=coupon-reset-to-default displayed={self.coupon_dropdown.menu.get()!r} content={self.coupon_dropdown.selected_values()!r}")
        self.summary_label.configure(text=f"total {self._state['total']}¥  ·  coupon -0¥  ·  payable {self._state['total']}¥")
        self.wait_label.configure(text='expect wait until ....')
        logging.debug(f"{_tag} exit method={self._state['method']!r} coupon={self._state['coupon']!r}")

    # ---------------- 事件 ----------------

    def _on_method_change(self, selected: str) -> None:
        logging.info(f"[PaymentView._on_method_change] entry selected={selected!r}")
        if not selected:
            logging.warning("[PaymentView._on_method_change] branch=empty, 支付方式未变")
            return
        self._state['method'] = selected
        self._recompute('method-change')

    def _on_coupon_change(self, selected: str) -> None:
        _tag = "[PaymentView._on_coupon_change]"
        logging.info(f"{_tag} entry selected={selected!r} total={self._state['total']!r}")
        if selected == NO_COUPON:
            # 显式的"不用券"分支, 与"查不到券"分开记日志, 免得把正常操作记成警告
            self._state['coupon'] = None
            logging.debug(f"{_tag} branch=no-coupon-selected, 用户选择不使用优惠券")
        else:
            # 父类传的是被点选的值(如 '满30减5'), 可以直接反查
            coupon = self.data.coupon_by_display(selected) if selected else None
            self._state['coupon'] = coupon
            if coupon is None:
                logging.warning(f"{_tag} branch=no-coupon-match selected={selected!r}, 按不减价处理")
            else:
                logging.debug(f"{_tag} branch=coupon-set display={coupon.display!r} threshold={coupon.threshold!r} discount={coupon.discount!r}")
        self._recompute('coupon-change')
        logging.debug(f"{_tag} exit cut={self._state['cut']!r} payable={self._state['payable']!r}")

    def _recompute(self, reason: str) -> None:
        """唯一的金额汇总出口: 所有改动最后都汇聚到这里, 界面只在这里刷新。"""
        _tag = "[PaymentView._recompute]"
        total = self._state['total']
        coupon = self._state['coupon']
        method = self._state['method']

        cut = coupon.compute(total) if coupon is not None else 0
        payable = total - cut
        self._state['cut'] = cut
        self._state['payable'] = payable
        logging.debug(f"{_tag} entry reason={reason!r} total={total!r} coupon={coupon!r} method={method!r} cut={cut!r} payable={payable!r}")

        food = self._state['food']
        if food is not None:
            # 等待提示: 时间来自菜品模型, 支付方式只影响提示措辞
            self.wait_label.configure(text=f"{method or '未选择支付方式'} · 预计等待 {food.wait_text}")
            logging.debug(f"{_tag} branch=wait-updated method={method!r} wait={food.wait_text!r}")
        else:
            logging.warning(f"{_tag} branch=no-food, 还没有菜品, 只刷新金额")

        self.summary_label.configure(
            text=f"total {total}¥  ·  coupon -{cut}¥  ·  payable {payable}¥"
        )
        logging.debug(f"{_tag} branch=summary-updated cut={cut!r} payable={payable!r}")

        # 没有支付方式就不让点 pay, 否则会出现"钱付了但不知道付给谁"的状态
        self.pay_btn.configure(state='normal' if method else 'disabled')
        logging.debug(f"{_tag} exit pay_btn_state={'normal' if method else 'disabled'}")

    def _on_pay_click(self) -> None:
        _tag = "[PaymentView._on_pay_click]"
        if not self._state['method']:
            logging.error(f"{_tag} branch=no-method, 支付方式为空, 拒绝支付")
            return
        payable = self._state['payable']
        logging.info(f"{_tag} branch=paying total={self._state['total']!r} cut={self._state['cut']!r} payable={payable!r} method={self._state['method']!r}")
        if self.on_paid is None:
            logging.warning(f"{_tag} branch=no-callback, 只打日志不跳转")
            return
        self.on_paid(payable)

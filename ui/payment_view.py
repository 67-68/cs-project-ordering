"""Payment page: title, method dropdown, coupon dropdown, wait hint, pay button."""
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
    """Two independent dropdowns. All state lives in _state and _recompute() is
    the single place that refreshes the UI.
    """

    def __init__(self, master, data: AppData, on_paid: Callable[[int], None] | None = None):
        _tag = "[payment]"
        super().__init__(master=master, fg_color=PAGE_BG, corner_radius=12)

        self.data = data
        self.on_paid = on_paid

        self._state: dict[str, Any] = {
            'food': None,
            'method': '',
            'coupon': None,
            'total': 0,
            'cut': 0,
            'payable': 0,
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # spacer pushes pay to the bottom

        # row0: header
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

        # row1: method + coupon inside one card
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

        self.coupon_label = tk.CTkLabel(
            master=self.method_card, text='use coupon',
            font=label_font, text_color=TEXT_HEADING, anchor='w',
        )
        self.coupon_label.grid(row=1, column=0, sticky='w', padx=(16, 10), pady=(0, 16))

        # NO_COUPON sits first so the default means "no discount", not a free discount
        coupon_values = [NO_COUPON] + [c.display for c in data.coupons]
        # the dropdown fires a callback while building, before summary_label exists,
        # so bind a throwaway handler now and swap it in at the end
        self.coupon_dropdown = SimpleDropdownFrame(
            master_=self.method_card,
            filter_name='coupon',
            display='',
            values=coupon_values,
            on_change=lambda _v: logging.debug(f"{_tag} early coupon callback ignored: {_v!r}"),
        )
        self.coupon_dropdown.grid(row=1, column=1, sticky='e', padx=(0, 16), pady=(0, 16))
        # the label on the left already names it, hide the built-in title
        self.coupon_dropdown.title.pack_forget()

        # row2: amounts
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

        # row4: pay button
        self.pay_btn = tk.CTkButton(
            master=self, text='pay',
            height=52, corner_radius=10,
            font=tk.CTkFont(size=18, weight='bold'),
            command=self._on_pay_click,
        )
        self.pay_btn.grid(row=4, column=0, sticky='ew', padx=10, pady=(0, 10))

        self.coupon_dropdown.on_change = self._on_coupon_change
        logging.debug(f"{_tag} built, coupons={coupon_values}")

    def load(self, food) -> None:
        """Load a dish and recompute amounts for it."""
        self._state['food'] = food
        self._state['total'] = int(getattr(food, 'base_price', 0) or 0)
        self._reset_ui()
        self._recompute('load-food')
        logging.debug(f"[payment.load] {getattr(food, 'food_id', None)} total={self._state['total']}")

    def _reset_ui(self) -> None:
        # wiping selection per dish, or a coffee coupon follows you to the noodles
        self._state['method'] = ''
        self._state['coupon'] = None
        if PAYMENT_METHODS:
            self.method_menu.set(PAYMENT_METHODS[0])
        else:
            logging.warning("no payment methods configured")
        if self.coupon_dropdown is not None:
            # explicit NO_COUPON, not '': empty string means "keep what the menu shows"
            self.coupon_dropdown.select(NO_COUPON)
            logging.debug(f"reset to default coupon {NO_COUPON!r}")
        self.summary_label.configure(text=f"total {self._state['total']}¥  ·  coupon -0¥  ·  payable {self._state['total']}¥")
        self.wait_label.configure(text='expect wait until ....')

    def _on_method_change(self, selected: str) -> None:
        self._state['method'] = selected
        self._recompute('method-change')
        logging.info(f"method picked: {selected}")

    def _on_coupon_change(self, selected: str) -> None:
        if selected == NO_COUPON:
            # explicit "no coupon", separate from "coupon not found"
            self._state['coupon'] = None
            logging.debug("user chose no coupon")
        else:
            coupon = self.data.coupon_by_display(selected) if selected else None
            self._state['coupon'] = coupon
            if coupon is None:
                logging.warning(f"coupon {selected!r} not found, no discount")
        self._recompute('coupon-change')

    def _recompute(self, reason: str) -> None:
        """Single place where money is recalculated and the page repaints."""
        total = self._state['total']
        coupon = self._state['coupon']
        method = self._state['method']

        cut = coupon.compute(total) if coupon is not None else 0
        payable = total - cut
        self._state['cut'] = cut
        self._state['payable'] = payable

        food = self._state['food']
        if food is not None:
            self.wait_label.configure(text=f"{method or '未选择支付方式'} · 预计等待 {food.wait_text}")
        else:
            logging.warning("no food loaded, only amounts refreshed")

        self.summary_label.configure(
            text=f"total {total}¥  ·  coupon -{cut}¥  ·  payable {payable}¥"
        )

        # no method, no payment
        self.pay_btn.configure(state='normal' if method else 'disabled')
        logging.debug(f"recomputed ({reason}): total={total} cut={cut} payable={payable} method={method!r}")

    def _on_pay_click(self) -> None:
        if not self._state['method']:
            logging.error("pay clicked without a method")
            return
        payable = self._state['payable']
        logging.info(f"paying {payable} via {self._state['method']}")
        if self.on_paid is None:
            logging.warning("pay clicked but unbound")
            return
        self.on_paid(payable)

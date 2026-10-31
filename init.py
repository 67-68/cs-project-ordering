"""Application entry point. Two doors, pick one per caller:

    open_food_app()                     -> brand new OS process, own window
    create_food_app_frame(master, ...)  -> ready-made widget, caller packs it

Nothing outside this file may touch FoodApp / FoodAppFrame directly.
"""
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import customtkinter as tk

from food_card import PolishedFoodCard
from food_model import DISTANCE_ANY, AppData, filter_foods, load_app_data
from ui.back_frame import BackFrame
from ui.filters import BaseDropdownFrame, DropdownFrame, SimpleDropdownFrame
from ui.order_view import OrderDetailView
from ui.payment_view import PaymentView

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# anchored on this file, so a child process can be spawned from any cwd
_PROJECT_ROOT = Path(__file__).resolve().parent
_ENTRY_SCRIPT = _PROJECT_ROOT / "init.py"

# values must exist in data/foods.json
SEARCH_FILTERS = [
    # (data key, label the customer sees, values, simple)
    ('food_component', 'allergies', ['caffeine', 'milk', 'water', 'peanut', 'gluten', 'shrimp', 'egg', 'oat', 'nuts'], False),
    ('distance_km', 'distance', [DISTANCE_ANY, '0', '1', '2', '3', '4', '5', '6'], True),
]


class FoodAppFrame(tk.CTkFrame):
    """The whole three page flow as one embeddable widget.

    The only callback that used to reach for the root window is quit, so it is
    routed through on_quit and the embedder decides what quitting means.
    """

    def __init__(
        self,
        master,
        on_quit: Callable[[], None] | None = None,
        data: AppData | None = None,
    ):
        _tag = "[FoodAppFrame.__init__]"
        # transparent, the embedder's background must show through
        super().__init__(master=master, fg_color="transparent")

        self.on_quit: Callable[[], None] | None = on_quit
        self.filters: list[BaseDropdownFrame] = []
        self.cards: list[PolishedFoodCard] = []
        # carries the dish from the order page to the payment page
        self.current_food = None

        # data first, UI second
        if data is None:
            logging.debug(f"{_tag} no data injected, loading from disk")
            self.data: AppData = load_app_data()
        else:
            logging.debug(f"{_tag} using injected AppData object")
            self.data = data
        logging.debug(f"{_tag} foods={len(self.data.foods)} coupons={len(self.data.coupons)}")

        # all three pages share one grid cell, weights make them stretch
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.init_pages()
        self.init_search_page()
        self.init_order_page()
        self.init_payment_page()
        logging.info(f"{_tag} frame built, on_quit={on_quit is not None}")

    def init_pages(self):
        _tag = "[init_pages]"
        pages = []

        for i in range(3):
            page = tk.CTkFrame(master=self, corner_radius=10)
            page.grid(row=0, column=0, sticky='nsew', padx=12, pady=12)

            top_frame = tk.CTkFrame(master=page, fg_color="transparent")
            top_frame.pack(side='top', fill='x', pady=(0, 8))

            name_label = tk.CTkLabel(master=top_frame, text=f"page {i}")
            name_label.pack(side='left', padx=(8, 0))

            # search page (0) has nowhere to go back to
            on_back = self.on_back_to_search if i > 0 else None
            back_frame = BackFrame(top_frame, on_back=on_back, on_quit=self._on_quit_requested)
            back_frame.pack(side='right', padx=(0, 8))
            pages.append(page)

        self.search_page: tk.CTkFrame = pages[0]
        self.order_page = pages[1]
        self.payment_page = pages[2]
        # later grids stack on top, so raise the search page back up
        self.search_page.tkraise()
        logging.info(f"{_tag} pages built: 3, search page on top")

    def add_filter(
        self,
        name: str,
        display: str,
        value: list[str],
        master,
        side: str,
        simple: bool = False,
    ) -> BaseDropdownFrame:
        """name is the data key (never rendered), display is the customer label."""
        _tag = "[add_filter]"
        filter_cls = DropdownFrame if not simple else SimpleDropdownFrame
        filter_ = filter_cls(
            master_=master,
            filter_name=name,
            display=display,
            values=value,
            on_change=self._on_filter_changed,
        )
        self.filters.append(filter_)
        filter_.pack(side=side, fill='x', padx=4, pady=4)
        logging.debug(f"{_tag} filter added: {name} ({filter_cls.__name__})")
        return filter_

    def get_filters(self) -> dict[str, list[str]]:
        # contract: {filter_name: [selected...]}, empty list keeps the key
        result: dict[str, list[str]] = {}
        for filter_ in self.filters:
            result[filter_.filter_name] = filter_.selected_values()
        logging.debug(f"[get_filters] snapshot: {result}")
        return result

    def init_search_page(self):
        _tag = "[init_search_page]"
        self.search_controls = tk.CTkFrame(master=self.search_page, fg_color="transparent")
        self.search_controls.pack(side='top', fill='x', padx=4, pady=(4, 8))

        for name, display, values, simple in SEARCH_FILTERS:
            created = self.add_filter(name, display, values, self.search_controls, 'top', simple=simple)
            if name == 'distance_km':
                self.location_filter = created
                logging.debug(f"{_tag} location filter bound")
            else:
                logging.debug(f"{_tag} generic filter {name} created")

        self.search_button = tk.CTkButton(master=self.search_controls, text='search', height=32, command=self.on_searched)
        self.search_button.pack(side='top', fill='x', padx=4, pady=(6, 0))

        self.food_list_container = tk.CTkScrollableFrame(
            master=self.search_page,
            label_text='Available food',
            corner_radius=10,
        )
        self.food_list_container.pack(side='top', fill="both", expand=True, padx=4, pady=(0, 4))
        logging.info(f"{_tag} search page built with {len(self.filters)} filters")

    def _on_filter_changed(self, selected_value: str) -> None:
        # the callback only reports what was just clicked; reread get_filters() for the rest
        logging.debug(f"[filter picked] {selected_value!r}, snapshot={self.get_filters()}")

    def on_searched(self) -> None:
        _tag = "[on_searched]"
        criteria = self.get_filters()
        foods = filter_foods(self.data.foods, criteria)
        logging.info(f"{_tag} criteria {criteria} -> {len(foods)}/{len(self.data.foods)} foods")

        for old in self.cards:
            old.destroy()
        self.cards.clear()
        logging.debug(f"{_tag} cleared old cards")

        for food in foods:
            card = PolishedFoodCard.from_food_info(
                master=self.food_list_container,
                info=food,
                on_order_click=self.on_order_click,
            )
            card.pack(fill='x', padx=4, pady=4)
            self.cards.append(card)
        logging.info(f"{_tag} search done, {len(self.cards)} cards")

    def init_order_page(self) -> None:
        _tag = "[init_order_page]"
        # header comes from init_pages(), no need to build one here
        self.order_view = OrderDetailView(master=self.order_page, on_pay=self.on_pay)
        self.order_view.pack(fill='both', expand=True, padx=4, pady=4)
        logging.debug(f"{_tag} order view packed")

    def init_payment_page(self) -> None:
        _tag = "[init_payment_page]"
        self.payment_view = PaymentView(
            master=self.payment_page,
            data=self.data,
            on_paid=self.on_paid,
        )
        self.payment_view.pack(fill='both', expand=True, padx=4, pady=4)
        logging.debug(f"{_tag} payment view packed")

    def on_order_click(self, food_id: int) -> None:
        food = next((f for f in self.data.foods if f.food_id == food_id), None)
        if food is None:
            logging.error(f"[on_order_click] unknown food {food_id}")
            return
        self.current_food = food
        self.order_view.load(food)
        self.order_page.tkraise()
        logging.info(f"[on_order_click] order page opened: {food_id}")

    def on_back_to_search(self) -> None:
        self.search_page.tkraise()
        logging.debug("[on_back_to_search] back to search")

    def on_pay(self) -> None:
        food = self.current_food
        if food is None:
            logging.error("[on_pay] pay without a dish selected")
            return
        # reload every time, last order's coupon must not leak
        self.payment_view.load(food)
        self.payment_page.tkraise()
        logging.info(f"[on_pay] payment page opened: {food.food_id}")

    def on_paid(self, payable: int) -> None:
        logging.info(f"[on_paid] paid {payable}")
        self.search_page.tkraise()

    def _on_quit_requested(self) -> None:
        """Quit button sink: hand control to the embedder, never kill the root."""
        if self.on_quit is None:
            logging.warning("[quit] no on_quit bound, destroying this frame only")
            self.destroy()
            return
        logging.info("[quit] delegating quit to embedder")
        self.on_quit()


class FoodApp(tk.CTk):
    """Standalone window: a root plus one FoodAppFrame stretched over it."""

    def __init__(self):
        _tag = "[FoodApp.__init__]"
        super().__init__()
        logging.debug(f"{_tag} root window created")
        # self.title is a method; assigning a string would kill it for good
        self.title('food system')
        self.geometry("600x500")
        self.minsize(480, 380)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # the root's only job now is owning the window and dying on quit
        self.app_frame = create_food_app_frame(master=self, on_quit=self.destroy)
        self.app_frame.grid(row=0, column=0, sticky='nsew')
        logging.info(f"{_tag} standalone window ready")


def create_food_app_frame(
    master: Any,
    on_quit: Callable[[], None] | None = None,
    data: AppData | None = None,
) -> FoodAppFrame:
    """Public door #2: returns a complete app widget, caller owns layout.

    The frame never calls mainloop and never touches the root window, so it is
    safe to pack into an existing window.
    """
    _tag = "[create_food_app_frame]"
    logging.info(
        f"{_tag} master={type(master).__name__} on_quit={on_quit is not None} injected_data={data is not None}"
    )
    frame = FoodAppFrame(master=master, on_quit=on_quit, data=data)
    logging.debug(f"{_tag} frame ready: {type(frame).__name__}")
    return frame


def open_food_app(wait: bool = False) -> subprocess.Popen | None:
    """Public door #1: launch the app in its own OS process, own window.

    A second Tk mainloop inside this process would fight over the CTk theme and
    the event loop, so the window gets a fresh interpreter. Returns the handle,
    or None when the spawn failed.
    """
    _tag = "[open_food_app]"
    if not _ENTRY_SCRIPT.exists():
        logging.error(f"{_tag} entry script missing: {_ENTRY_SCRIPT}")
        return None

    # sys.executable, not a hardcoded path: keeps the caller's interpreter (venv)
    argv = [sys.executable, str(_ENTRY_SCRIPT)]
    logging.info(f"{_tag} launching {argv} cwd={_PROJECT_ROOT} wait={wait}")

    try:
        process = subprocess.Popen(argv, cwd=str(_PROJECT_ROOT))
    except OSError as exc:
        logging.error(f"{_tag} spawn failed: {exc}")
        return None

    logging.debug(f"{_tag} spawned pid={process.pid}")

    if wait:
        returncode = process.wait()
        logging.info(f"{_tag} child pid={process.pid} exited with {returncode}")
    else:
        logging.debug(f"{_tag} not waiting, parent keeps running")
    return process


def main() -> None:
    logging.info("[main] starting standalone app")
    app = FoodApp()
    app.mainloop()
    logging.info("[main] app closed")


if __name__ == "__main__":
    main()

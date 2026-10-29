import logging

import customtkinter as tk

from food_card import PolishedFoodCard
from food_model import AppData, load_app_data
from ui.back_frame import BackFrame
from ui.filters import BaseDropdownFrame, DropdownFrame, SimpleDropdownFrame
from ui.order_view import OrderDetailView
from ui.payment_view import PaymentView

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# 'any' means the distance filter is off; otherwise it acts as a radius in km
DISTANCE_FIELD = 'distance_km'
DISTANCE_ANY = 'any'

# values must exist in data/foods.json
SEARCH_FILTERS = [
    # (data key, label the customer sees, values, simple)
    ('food_component', 'allergies', ['caffeine', 'milk', 'water', 'peanut', 'gluten', 'shrimp', 'egg', 'oat', 'nuts'], False),
    ('distance_km', 'distance', [DISTANCE_ANY, '0', '1', '2', '3', '4', '5', '6'], True),
]


class FoodApp(tk.CTk):
    def __init__(self):
        super().__init__()
        # self.title is a method; assigning a string would kill it for good
        self.title('food system')
        self.filters: list[BaseDropdownFrame] = []
        self.geometry("600x500")
        self.minsize(480, 380)
        self.cards: list[PolishedFoodCard] = []
        # carries the dish from the order page to the payment page
        self.current_food = None

        # data first, UI second
        self.data: AppData = load_app_data()
        logging.debug(f"app start: foods={len(self.data.foods)} coupons={len(self.data.coupons)}")

        # all three pages share one grid cell, weights make them stretch
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.init_pages()
        self.init_search_page()
        self.init_order_page()
        self.init_payment_page()

    def init_pages(self):
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
            back_frame = BackFrame(top_frame, on_back=on_back, on_quit=self.destroy)
            back_frame.pack(side='right', padx=(0, 8))
            pages.append(page)

        self.search_page: tk.CTkFrame = pages[0]
        self.order_page = pages[1]
        self.payment_page = pages[2]
        # later grids stack on top, so raise the search page back up
        self.search_page.tkraise()
        logging.info("pages built: 3, search page on top")

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
        logging.debug(f"filter added: {name} ({filter_cls.__name__})")
        return filter_

    def get_filters(self) -> dict[str, list[str]]:
        # contract: {filter_name: [selected...]}, empty list keeps the key
        result: dict[str, list[str]] = {}
        for filter_ in self.filters:
            result[filter_.filter_name] = filter_.selected_values()
        logging.debug(f"filters snapshot: {result}")
        return result

    def init_search_page(self):
        self.search_controls = tk.CTkFrame(master=self.search_page, fg_color="transparent")
        self.search_controls.pack(side='top', fill='x', padx=4, pady=(4, 8))

        for name, display, values, simple in SEARCH_FILTERS:
            created = self.add_filter(name, display, values, self.search_controls, 'top', simple=simple)
            if name == 'distance_km':
                self.location_filter = created

        self.search_button = tk.CTkButton(master=self.search_controls, text='search', height=32, command=self.on_searched)
        self.search_button.pack(side='top', fill='x', padx=4, pady=(6, 0))

        self.food_list_container = tk.CTkScrollableFrame(
            master=self.search_page,
            label_text='Available food',
            corner_radius=10,
        )
        self.food_list_container.pack(side='top', fill="both", expand=True, padx=4, pady=(0, 4))
        logging.info(f"search page built with {len(self.filters)} filters")

    def _on_filter_changed(self, selected_value: str) -> None:
        # the callback only reports what was just clicked; reread get_filters() for the rest
        logging.debug(f"filter picked {selected_value!r}, snapshot={self.get_filters()}")

    def on_searched(self):
        # each filter shrinks the candidate set in turn:
        # list fields (allergies) exclude, distance is a radius, scalars are exact
        foods = list(self.data.foods)
        for filter_ in self.filters:  # not 'f', the food loop below would shadow it
            name = filter_.filter_name
            wanted = set(filter_.selected_values())
            if not wanted:
                logging.debug(f"{name}: nothing selected, skipped")
                continue
            if name == DISTANCE_FIELD and DISTANCE_ANY in wanted:
                logging.debug(f"{name}: 'any' selected, filter skipped")
                continue
            max_km = None
            if name == DISTANCE_FIELD:
                max_km = min(int(v) for v in wanted)
            kept = []
            for food in foods:
                if not hasattr(food, name):
                    # filter_name must match a FoodInfo field
                    logging.error(f"{name}: no such field on food {food.food_id}")
                    continue
                field_value = getattr(food, name)
                if isinstance(field_value, (list, tuple, set)):
                    # allergies: drop the food if it contains ANY selected allergen
                    matched = not wanted.intersection({str(v) for v in field_value})
                elif max_km is not None:
                    # distance is a radius, not an exact value
                    matched = int(field_value) <= max_km
                else:
                    # scalar field: menu values are strings, distance_km is int
                    matched = str(field_value) in wanted
                if matched:
                    kept.append(food)
            logging.debug(f"{name}: wanted={sorted(wanted)} kept {len(kept)}/{len(foods)}")
            foods = kept

        for old in self.cards:
            old.destroy()
        self.cards.clear()

        for food in foods:
            card = PolishedFoodCard.from_food_info(
                master=self.food_list_container,
                info=food,
                on_order_click=self.on_order_click,
            )
            card.pack(fill='x', padx=4, pady=4)
            self.cards.append(card)
        logging.info(f"search done, {len(self.cards)} cards")

    def init_order_page(self) -> None:
        # header comes from init_pages(), no need to build one here
        self.order_view = OrderDetailView(master=self.order_page, on_pay=self.on_pay)
        self.order_view.pack(fill='both', expand=True, padx=4, pady=4)

    def init_payment_page(self) -> None:
        self.payment_view = PaymentView(
            master=self.payment_page,
            data=self.data,
            on_paid=self.on_paid,
        )
        self.payment_view.pack(fill='both', expand=True, padx=4, pady=4)

    def on_order_click(self, food_id: int) -> None:
        food = next((f for f in self.data.foods if f.food_id == food_id), None)
        if food is None:
            logging.error(f"order clicked for unknown food {food_id}")
            return
        self.current_food = food
        self.order_view.load(food)
        self.order_page.tkraise()
        logging.info(f"order page opened: {food_id}")

    def on_back_to_search(self) -> None:
        self.search_page.tkraise()
        logging.debug("back to search")

    def on_pay(self) -> None:
        food = self.current_food
        if food is None:
            logging.error("pay without a dish selected")
            return
        # reload every time, last order's coupon must not leak
        self.payment_view.load(food)
        self.payment_page.tkraise()
        logging.info(f"payment page opened: {food.food_id}")

    def on_paid(self, payable: int) -> None:
        logging.info(f"paid {payable}")
        self.search_page.tkraise()


def main() -> None:
    app = FoodApp()
    app.mainloop()
    logging.info("app closed")


if __name__ == "__main__":
    main()

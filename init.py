"""应用入口。

这里只留 FoodApp 这个"装配器": 负责页面切换、事件路由、把数据灌进各 View。
具体控件的实现都在 ui/ 包里, 数据与业务规则在 food_model.py。
"""
import logging

import customtkinter as tk

from food_card import PolishedFoodCard
from food_model import AppData, load_app_data
from ui.back_frame import BackFrame
from ui.filters import BaseDropdownFrame, DropdownFrame, SimpleDropdownFrame
from ui.order_view import OrderDetailView
from ui.payment_view import PaymentView

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


# ---- 搜索页的滤镜配置: 候选值必须与 data/foods.json 里的实际取值一致 ----
SEARCH_FILTERS = [
    # (filter_name=数据 key, display=顾客看到的标题, values, simple)
    ('food_component', 'allergies', ['咖啡因', '牛奶', '水', '花生', '麸质', '虾', '蛋', '燕麦', '坚果'], False),
    ('distance_km', 'distance', ['0', '1', '2', '3', '4', '5', '6'], True),
]


class FoodApp(tk.CTk):
    def __init__(self):
        super().__init__()
        # tkinter 的 self.title 是方法, 赋值字符串会覆盖方法, 标题永远设不上 -> 用 self.title(...)
        self.title('food system')
        # 两个子类共享 BaseDropdownFrame 的 filter_name / filter_content 契约
        self.filters: list[BaseDropdownFrame] = []
        self.geometry("600x500")
        self.minsize(480, 380)
        self.cards: list[PolishedFoodCard] = []
        # 从订单页跳到支付页时要带着这条菜品, 否则支付页不知道在给谁收钱
        self.current_food = None

        # 先加载数据, 再建 UI: 建 UI 时要用到 self.data.foods
        logging.debug("[FoodApp.__init__] branch=load-data-before-ui")
        self.data: AppData = load_app_data()
        logging.debug(f"[FoodApp.__init__] data loaded, foods={len(self.data.foods)} coupons={len(self.data.coupons)}")
        # 三个 page 都 grid 在同一 cell, 不配置权重的话窗口变大时 page 不会跟着拉伸
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        logging.debug("[FoodApp.__init__] grid weights set (row0/col0=1)")
        self.init_pages()
        self.init_search_page()
        self.init_order_page()
        self.init_payment_page()
        logging.debug("[FoodApp.__init__] exit all pages built")

    # ---------------- 页面骨架 ----------------

    def init_pages(self):
        logging.info('start init pages')
        pages = []

        for i in range(3):
            # 每个 page 自带一圈内边距, 免得控件贴着窗口边缘
            page = tk.CTkFrame(master=self, corner_radius=10)
            page.grid(row=0, column=0, sticky='nsew', padx=12, pady=12)
            logging.debug(f"[init_pages] branch=build page index={i}")

            top_frame = tk.CTkFrame(master=page, fg_color="transparent")
            # fill='x' 让顶栏横向铺满, 否则 back_frame 会缩在中间
            top_frame.pack(side='top', fill='x', pady=(0, 8))

            name_label = tk.CTkLabel(master=top_frame, text=f"page {i}")
            name_label.pack(side='left', padx=(8, 0))
            # 只有 search_page(index 0) 无路可退, 其余页的 back 回搜索页
            on_back = self.on_back_to_search if i > 0 else None
            back_frame = BackFrame(top_frame, on_back=on_back, on_quit=self.destroy)
            back_frame.pack(side='right', padx=(0, 8))
            pages.append(page)
            logging.debug(f"[init_pages] branch=backframe index={i} back_bound={on_back is not None}")

        self.search_page: tk.CTkFrame = pages[0]
        self.order_page = pages[1]
        self.payment_page = pages[2]
        # 三个 page 都 grid 在同一个 cell(row=0,column=0), 后 grid 的会盖住先 grid 的,
        # 所以默认可见的是最后创建的 payment_page。tkraise() 把 search_page 提到最上层。
        logging.debug(f"[init_pages] branch=raise search_page={self.search_page} (pages[0])")
        self.search_page.tkraise()
        logging.debug("[init_pages] search_page raised to top, other pages stay behind")

    # ---------------- 搜索页 ----------------

    def add_filter(
        self,
        name: str,
        display: str,
        value: list[str],
        master,
        side: str,
        simple: bool = False,
    ) -> BaseDropdownFrame:
        """name = 筛选用的数据 key (如 food_component), 永不出现在界面上;
        display = 给顾客看的文案 (如 allergies), 只进 title label。两者故意解耦。
        """
        # 分支: simple=True -> 单选 SimpleDropdownFrame; simple=False -> 多条件 DropdownFrame
        filter_cls = DropdownFrame if not simple else SimpleDropdownFrame
        logging.debug(f"[add_filter] entry name={name!r} display={display!r} values={value!r} master={master!r} side={side!r} simple={simple} cls={filter_cls.__name__}")
        if not name:
            logging.warning(f"[add_filter] branch=empty-name, 之后 get_filters() 会拿到空 key display={display!r}")
        if not display:
            logging.warning(f"[add_filter] branch=empty-display, 顾客会看到一个没有标题的滤镜条 name={name!r}")
        if not value:
            logging.warning(f"[add_filter] branch=empty-values, menu would have nothing to choose, name={name!r} display={display!r}")
        # on_change 必须是可调用对象, 这里传 self._on_filter_changed
        filter_ = filter_cls(
            master_=master,
            filter_name=name,
            display=display,
            values=value,
            on_change=self._on_filter_changed,
        )
        logging.debug(f"[add_filter] branch=created obj={filter_.__class__.__name__}")
        self.filters.append(filter_)
        # fill='x' 让滤镜条横向铺满, pady 给它和邻居留呼吸空间
        filter_.pack(side=side, fill='x', padx=4, pady=4)
        logging.debug(f"[add_filter] branch=packed side={side!r} total={len(self.filters)}")
        return filter_

    def get_filters(self) -> dict[str, list[str]]:
        # 统一数据契约: {filter_name: [选中的内容...]}, 空内容也保留 key 便于调试
        logging.debug(f"[get_filters] entry total={len(self.filters)}")
        result: dict[str, list[str]] = {}
        for filter_ in self.filters:
            name = filter_.filter_name
            content = filter_.selected_values()
            logging.debug(f"[get_filters] branch=collect name={name!r} content={content!r}")
            if name in result:
                logging.warning(f"[get_filters] branch=duplicate-name name={name!r}, 后者覆盖前者")
            result[name] = content
        logging.debug(f"[get_filters] exit result={result!r}")
        return result

    def init_search_page(self):
        # 控件区容器: 上方是滤镜/按钮, 下方是滚动列表, 两者都能横向铺满
        self.search_controls = tk.CTkFrame(master=self.search_page, fg_color="transparent")
        self.search_controls.pack(side='top', fill='x', padx=4, pady=(4, 8))

        logging.debug(f"[init_search_page] branch=build-filters config={SEARCH_FILTERS!r}")
        for name, display, values, simple in SEARCH_FILTERS:
            created = self.add_filter(name, display, values, self.search_controls, 'top', simple=simple)
            if name == 'distance_km':
                self.location_filter = created
                logging.debug("[init_search_page] branch=keep-ref name='distance_km'")

        self.search_button = tk.CTkButton(master=self.search_controls, text='search', height=32, command=self.on_searched)
        self.search_button.pack(side='top', fill='x', padx=4, pady=(6, 0))

        self.food_list_container = tk.CTkScrollableFrame(
            master=self.search_page,
            label_text='Available food',
            corner_radius=10,
        )
        self.food_list_container.pack(side='top', fill="both", expand=True, padx=4, pady=(0, 4))
        logging.debug(f"[init_search_page] built controls + list, total_filters={len(self.filters)}")

    def _on_filter_changed(self, selected_value: str) -> None:
        # 回调只告诉你"刚点了什么"; 想要全部滤镜的当前状态, 统一回查 get_filters()
        logging.debug(f"[_on_filter_changed] selected_value={selected_value!r} snapshot={self.get_filters()!r}")

    def on_searched(self):
        logging.debug(f"[on_searched] entry foods={len(self.data.foods)} filters={len(self.filters)}")
        # 筛选算法: 每个滤镜都对候选集做一次收缩(交集), 缩完再交给下一个滤镜
        foods = list(self.data.foods)
        for filter_ in self.filters:  # 变量不能叫 f, 否则会被内层的食物循环覆盖
            name = filter_.filter_name
            wanted = set(filter_.selected_values())  # 缺括号会拿到方法对象, set(*[...]) 还会 TypeError
            logging.debug(f"[on_searched] branch=filter name={name!r} wanted={wanted!r} candidates={len(foods)}")
            if not wanted:
                logging.debug(f"[on_searched] branch=skip name={name!r}, 没有选中内容, 该滤镜不参与筛选")
                continue
            kept = []
            for food in foods:
                if not hasattr(food, name):
                    # filter_name 必须能对上 FoodInfo 的字段名, 对不上就是配置错误
                    logging.error(f"[on_searched] branch=no-field name={name!r} food_id={food.food_id!r}")
                    continue
                field_value = getattr(food, name)
                if isinstance(field_value, (list, tuple, set)):
                    # 列表字段(如 food_component): 任一分量命中就算匹配, 直接 str() 整个列表是对不上的
                    matched = bool(wanted.intersection({str(v) for v in field_value}))
                    logging.debug(f"[on_searched] branch=list-field name={name!r} food_id={food.food_id!r} values={list(field_value)!r} matched={matched}")
                else:
                    # 标量字段: 菜单值永远是 str, 而 distance_km 是 int -> 统一转 str 再比
                    matched = str(field_value) in wanted
                    logging.debug(f"[on_searched] branch=scalar-field name={name!r} food_id={food.food_id!r} value={field_value!r} matched={matched}")

                if matched:
                    kept.append(food)
                else:
                    logging.debug(f"[on_searched] branch=reject name={name!r} food_id={food.food_id!r}")
            logging.debug(f"[on_searched] branch=filtered name={name!r} kept={len(kept)}/{len(foods)}")
            foods = kept

        # 创建食物卡片: 先清掉上一轮的, 否则重复点 search 会无限堆叠
        logging.debug(f"[on_searched] branch=clear-old cards={len(self.cards)}")
        for old in self.cards:
            old.destroy()
        self.cards.clear()

        for food in foods:
            card = PolishedFoodCard.from_food_info(
                master=self.food_list_container,
                info=food,
                on_order_click=self.on_order_click,
            )
            card.pack(fill='x', padx=4, pady=4)  # 建了不 pack, 控件在界面上就是孤儿
            self.cards.append(card)
        logging.debug(f"[on_searched] exit cards={len(self.cards)}")

    # ---------------- 订单页 / 支付页 ----------------

    def init_order_page(self) -> None:
        # header 不在这里建: init_pages() 已经给每个 page 铺了 top_frame(标题 + back/quit)
        self.order_view = OrderDetailView(master=self.order_page, on_pay=self.on_pay)
        self.order_view.pack(fill='both', expand=True, padx=4, pady=4)
        logging.debug(f"[init_order_page] built order_view={self.order_view!r}")

    def init_payment_page(self) -> None:
        self.payment_view = PaymentView(
            master=self.payment_page,
            data=self.data,
            on_paid=self.on_paid,
        )
        self.payment_view.pack(fill='both', expand=True, padx=4, pady=4)
        logging.debug(f"[init_payment_page] built payment_view={self.payment_view!r} coupons={len(self.data.coupons)}")

    # ---------------- 事件路由 ----------------

    def on_order_click(self, food_id: int) -> None:
        logging.info(f"[on_order_click] entry food_id={food_id!r}")
        food = next((f for f in self.data.foods if f.food_id == food_id), None)
        if food is None:
            logging.error(f"[on_order_click] branch=not-found food_id={food_id!r}, 数据里没有这条记录")
            return
        logging.debug(f"[on_order_click] branch=found title={food.title!r}")

        self.current_food = food
        self.order_view.load(food)
        logging.debug("[on_order_click] branch=order-view-loaded")
        self.order_page.tkraise()
        logging.debug(f"[on_order_click] branch=raised page=order_page food_id={food_id!r}")

    def on_back_to_search(self) -> None:
        logging.info("[on_back_to_search] branch=raise search_page")
        self.search_page.tkraise()

    def on_pay(self) -> None:
        """订单页的"支付"按钮 -> 带着当前菜品进支付页。"""
        _tag = "[on_pay]"
        food = self.current_food
        logging.info(f"{_tag} entry food_id={getattr(food, 'food_id', None)!r}")
        if food is None:
            logging.error(f"{_tag} branch=no-current-food, 没有选中菜品, 拒绝进入支付页")
            return
        # 每次进入都要重新灌数据: 上一单选的券不能带到这一单
        self.payment_view.load(food)
        logging.debug(f"{_tag} branch=payment-view-loaded food_id={food.food_id!r}")
        self.payment_page.tkraise()
        logging.debug(f"{_tag} branch=raised page=payment_page")

    def on_paid(self, payable: int) -> None:
        """支付成功回调: 目前只留痕并退回搜索页。"""
        logging.info(f"[on_paid] entry payable={payable!r}")
        self.search_page.tkraise()
        logging.debug("[on_paid] branch=raised page=search_page")


def main() -> None:
    logging.debug("[main] branch=start app")
    app = FoodApp()
    app.mainloop()
    logging.debug("[main] branch=app closed")


if __name__ == "__main__":
    main()

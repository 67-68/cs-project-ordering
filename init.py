from typing import Any, Callable, Tuple

import customtkinter as tk
import logging
from food_card import PolishedFoodCard
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

from food_model import AppData, Coupon, load_app_data

# ---- 支付方式候选值: 与后端对接前先硬编码 ----
PAYMENT_METHODS = ['Apple Pay', '微信支付', '支付宝', '银行卡', '校园卡']

# 优惠券下拉的"不使用"哨兵值, 单独抽出来避免各处硬编码中文字面量
NO_COUPON = '不使用优惠券'

# ---- 全局视觉常量: customtkinter 的所有颜色都要 (浅色, 深色) 成对给 ----
# 放在文件顶部, 因为 PaymentView / OrderDetailView 都要用
PAGE_BG = ("#EFEFF4", "#141419")       # 整页底色, 比卡片更深一档, 衬托卡片浮起
TITLE_BAR_BG = ("#FFFFFF", "#23232B")  # 标题栏底色
SHADOW = ("#C7C7CC", "#07070A")        # 模拟阴影的实心色, 只在右下露出 2px
CARD_INFO_BG = ("#FFFFFF", "#1E1E24")  # 中性卡片
CARD_DINE_BG = ("#EAF2FB", "#1A2733")  # 冷色卡片, 用于区分区域
CARD_BORDER = ("#DCDCE1", "#33333D")   # 1px 描边, 强化卡片边界
TEXT_PRIMARY = ("#1C1C1E", "#F2F2F7")
TEXT_HEADING = ("#3A3A3C", "#C7C7CC")


class FoodApp(tk.CTk):
    def __init__(self):
        super().__init__()
        # tkinter 的 self.title 是方法, 赋值字符串会覆盖方法, 标题永远设不上 -> 用 self.title(...)
        self.title('food system')
        # 两个子类共享 BaseDropdownFrame 的 filter_name / filter_content 契约
        self.filters: list["BaseDropdownFrame"] = []
        self.geometry("600x500")
        self.minsize(480, 380)
        self.cards: list[PolishedFoodCard] = []
        # 从订单页跳到支付页时要带着这条菜品, 否则支付页不知道在给谁收钱
        self.current_food = None

        # 先加载数据, 再建 UI: 建 UI 时要用到 self.data.foods
        logging.debug("[FoodApp.__init__] branch=load-data-before-ui")
        self.data: AppData = load_app_data()
        logging.debug(f"[FoodApp.__init__] data loaded, foods={len(self.data.foods)}")
        # 三个 page 都 grid 在同一 cell, 不配置权重的话窗口变大时 page 不会跟着拉伸
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        logging.debug("[FoodApp.__init__] grid weights set (row0/col0=1)")
        self.init_pages()
        self.init_search_page()
        self.init_order_page()
        self.init_payment_page()

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
                on_order_click=self.on_order_click,  # 裸名 on_order_click 是 NameError
            )
            card.pack(fill='x', padx=4, pady=4)  # 建了不 pack, 控件在界面上就是孤儿
            self.cards.append(card)
        logging.debug(f"[on_searched] exit cards={len(self.cards)}")

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

    def add_filter(self, name: str, display: str, value: list[str], master, side: str, simple: bool = False) -> "BaseDropdownFrame":
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
            on_change=self._on_filter_changed
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

        # name 是数据 key(用于筛选), display 是顾客看到的标题
        # 候选值必须与 data/foods.json 里的实际取值一致, 否则菜单里选的永远匹配不到任何条目
        component_values = ['咖啡因', '牛奶', '水', '花生', '麸质', '虾', '蛋', '燕麦', '坚果']
        distance_values = ['0', '1', '2', '3', '4', '5', '6']
        logging.debug(f"[init_search_page] branch=build-filters component_values={component_values!r} distance_values={distance_values!r}")
        self.add_filter('food_component', 'allergies', component_values, self.search_controls, 'top')
        self.location_filter = self.add_filter('distance_km', 'distance', distance_values, self.search_controls, 'top', simple=True)

        self.search_button = tk.CTkButton(master=self.search_controls, text='search', height=32, command=self.on_searched)
        self.search_button.pack(side='top', fill='x', padx=4, pady=(6, 0))

        self.food_list_container = tk.CTkScrollableFrame(
            master=self.search_page,
            label_text='Available food',
            corner_radius=10,
        )
        self.food_list_container.pack(side='top', fill="both", expand=True, padx=4, pady=(0, 4))
        logging.debug(f"[init_search_page] built controls + list, total_filters={len(self.filters)}")


class PaymentView(tk.CTkFrame):
    """支付页主体: payment 标题 + 支付方式 dropdown + 优惠券 dropdown + 等待提示 + pay 按钮。

    两个 dropdown 复用同一个 BaseDropdownFrame 家族, 只是 simple=True(单选)。
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

        # 优惠券下拉: 用 BaseDropdownFrame 的 simple 变体, 与筛选条共用同一套骨架
        # 「无券」放在第一位: 默认选中它, 语义上是"不使用优惠券", 而不是默认就打折
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
            # 父类现在传的是被点选的值(如 '满30减5'), 可以直接反查
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
            # 费用文案 + 等待提示: 等待时间来自菜品模型, 支付方式只影响提示措辞
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
        return

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

FONT_TITLE = ("", 36, "bold")   # CTkFont 用 size 更稳, 这里只留语义名
FONT_SECTION = ("", 17, "bold")
FONT_BODY = ("", 15)
FONT_BUTTON = ("", 15, "bold")


class OrderDetailView(tk.CTkFrame):
    """订单详情页主体: 大标题 + 评价/支付动作 + 基本信息 + 堂食信息。

    只负责"展示一条 FoodInfo", 不持有数据源; 数据由 load() 灌进来。
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
        self.info_shell, self.info_body = self._build_card(
            self, '📋 基本信息', CARD_INFO_BG,
        )
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
        _tag = f"[OrderDetailView._build_card]"
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


class BackFrame(tk.CTkFrame):
    def __init__(self, master_, on_back: Callable[[], None] | None = None, on_quit: Callable[[], None] | None = None):
        # 不传回调时降级为纯展示, 不会因为 None 而在点击时炸
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

class BaseDropdownFrame(tk.CTkFrame):
    """下拉滤镜家族的唯一父类: 只负责骨架 + 数据模型 + 事件出口, 自身永不被实例化。

    契约:
      1. 数据模型(filter_name / filter_content)由父类持有, 子类只通过 _update_filter_content() 改;
      2. 想改"选中语义" -> override _apply_select(多选累积就是这么做的);
      3. 想改"UI 投影"   -> override _render_content(多选 label 就是这么做的);
      4. 不要 override _emit, 它保证 on_change 一定在模型更新之后、带着最新快照触发。
    """

    def __init__(
        self,
        master_,
        filter_name: str,
        display: str,
        values: list[str],
        on_change: Callable[[str], None] | None = None,
    ):
        # 用 type(self).__name__ 而不是写死类名: 父类不承担任何具体身份
        _tag = f"[{type(self).__name__}.__init__]"
        logging.debug(f"{_tag} entry filter_name={filter_name!r} display={display!r} values={values!r} on_change={on_change!r}")
        super().__init__(master=master_, corner_radius=8)

        # ---- 共同数据模型: 父类是唯一权威来源 ----
        self.filter_name: str = filter_name      # 筛选用的数据 key, 不上界面
        self.display: str = display              # 给顾客看的文案, 只进 title
        self.filter_content: list[str] = []      # 当前选中的内容, 可以有多个
        logging.debug(f"{_tag} branch=model-init filter_name={self.filter_name!r} display={self.display!r} content={self.filter_content!r}")

        self.on_change: Callable[[str], None] | None = on_change

        if not filter_name:
            logging.warning(f"{_tag} branch=empty-filter-name, get_filters() 之后会拿到空 key display={display!r}")
        if not display:
            logging.warning(f"{_tag} branch=empty-display, 标题会是空白 filter_name={filter_name!r}")

        # 界面上只出现 display, filter_name 绝不外泄给顾客
        self.title = tk.CTkLabel(master=self, text=display, width=70, anchor='w')
        self.title.pack(side='left', padx=(10, 6), pady=6)
        logging.debug(f"{_tag} branch=title-packed display={display!r}")

        if not values:
            logging.warning(f"{_tag} branch=empty-values, menu 没有可选项 filter_name={filter_name!r} display={display!r}")

        # 统一命名 self.menu: 外部只有一个句柄, 不再有 menu/dropdown 两套名字
        self.menu = tk.CTkOptionMenu(
            master=self,
            values=values,
            command=self._emit,
            width=110,
        )
        self.menu.pack(side='right', padx=(6, 10), pady=6)
        logging.debug(f"{_tag} branch=menu-packed values={values!r}")

        if on_change is None:
            logging.warning(f"{_tag} branch=no-on_change, 选择只改模型, 不向外通知")
        else:
            logging.debug(f"{_tag} branch=on_change-bound callback={on_change!r}")
        logging.debug(f"{_tag} exit filter_name={self.filter_name!r} content={self.filter_content!r}")

    # ---------------- 事件出口 ----------------

    def _emit(self, selected_value: str) -> None:
        # CTkOptionMenu 的 command 会把被点选的值传进来
        _tag = f"[{type(self).__name__}._emit]"
        logging.debug(f"{_tag} entry selected_value={selected_value!r} filter_name={self.filter_name!r} before={self.filter_content!r}")
        if not selected_value:
            logging.warning(f"{_tag} branch=empty-value, 忽略")
            return
        # 1) 先改数据模型(子类通过 override _apply_select 决定累积还是覆盖)
        self._apply_select(selected_value)
        # 2) 模型已是最新, 把被点选的原始值转给订阅方
        self._notify_change('select', selected_value)

    def _notify_change(self, reason: str, selected_value: str = '') -> None:
        """通知外部订阅者。

        契约: 回调收到的是**刚被点选的那个值**(str), 不是 filter_name。
        早先版本传的是 filter_name, 结果支付页拿 'coupon' 去 coupon_by_display() 必然查不到。
        订阅方若需要"当前全部选中内容", 自己回查 selected_values() / get_filters()。
        """
        _tag = f"[{type(self).__name__}._notify_change]"
        snapshot = self.selected_values()
        logging.debug(f"{_tag} entry reason={reason!r} name={self.filter_name!r} selected_value={selected_value!r} snapshot={snapshot!r} has_callback={self.on_change is not None}")
        if self.on_change is None:
            logging.debug(f"{_tag} branch=no-callback, 只更新模型")
            return

        logging.debug(f"{_tag} branch=fire callback={getattr(self.on_change, '__name__', repr(self.on_change))} arg={selected_value!r}")
        self.on_change(selected_value)
        logging.debug(f"{_tag} exit reason={reason!r}")

    # ---------------- 数据模型面 ----------------

    def selected_values(self) -> list[str]:
        """当前选择内容 (统一数据模型), 由 get_filters() 读取。返回副本, 外部改不动内部状态。"""
        snapshot = list(self.filter_content)
        logging.debug(f"[{type(self).__name__}.selected_values] name={self.filter_name!r} content={snapshot!r}")
        return snapshot

    def select(self, value: str = '') -> None:
        """公共入口: 用代码设定选中值, 并同步向订阅者广播。

        - value 为空时取菜单当前显示值(用于构造后补齐模型);
        - 与用户点选走同一条链: _apply_select -> _render_content -> _notify_change。
        """
        _tag = f"[{type(self).__name__}.select]"
        target = value or self.menu.get()
        logging.debug(f"{_tag} entry value={value!r} resolved={target!r} name={self.filter_name!r} before={self.filter_content!r}")
        if not target:
            logging.warning(f"{_tag} branch=no-value, 菜单也没有默认值, 忽略 name={self.filter_name!r}")
            return
        if value:
            # 代码指定了值 -> 菜单显示也要跟上, 否则界面和模型再次错位
            self.menu.set(target)
            logging.debug(f"{_tag} branch=menu-set displayed={target!r}")
        self._apply_select(target)
        logging.debug(f"{_tag} branch=applied content={self.filter_content!r}")
        self._notify_change('select', target)
        logging.debug(f"{_tag} exit name={self.filter_name!r} content={self.filter_content!r}")

    def _apply_select(self, selected_value: str) -> None:
        """选择语义钩子: 默认"单选覆盖", 多选累积型子类自行 override。"""
        _tag = f"[{type(self).__name__}._apply_select]"
        logging.debug(f"{_tag} entry selected_value={selected_value!r} before={self.filter_content!r}")
        if selected_value in self.filter_content:
            logging.debug(f"{_tag} branch=already-present, 覆盖模式下重写一次保证路径统一")
        self._update_filter_content([selected_value], 'select-replace')

    def _update_filter_content(self, new_content: list[str], reason: str) -> None:
        """改内容的唯一入口: 写模型 + 打日志 + 触发渲染。子类禁止绕过它直接改 filter_content。"""
        _tag = f"[{type(self).__name__}._update_filter_content]"
        old_content = list(self.filter_content)
        logging.debug(f"{_tag} entry reason={reason!r} name={self.filter_name!r} old={old_content!r} new={new_content!r}")
        if old_content == new_content:
            logging.debug(f"{_tag} branch=unchanged, 内容相同, 跳过渲染")
            return
        self.filter_content = list(new_content)
        logging.debug(f"{_tag} branch=content-updated name={self.filter_name!r} content={self.filter_content!r}")
        self._render_content(reason)
        logging.debug(f"{_tag} exit name={self.filter_name!r} content={self.filter_content!r}")

    def _render_content(self, reason: str) -> None:
        """渲染钩子: 把 filter_content 投影到具体控件。默认无内容控件(单选即此)。"""
        logging.debug(f"[{type(self).__name__}._render_content] branch=noop reason={reason!r} content={self.filter_content!r}")


class DropdownFrame(BaseDropdownFrame):
    """多选累积型: 每次从菜单点选一个值, 追加成一个可删的 label。"""

    def __init__(self, master_, filter_name: str, display: str, values: list[str], on_change: Callable[..., None]):
        _tag = "[DropdownFrame.__init__]"
        logging.debug(f"{_tag} entry filter_name={filter_name!r} display={display!r} values={values!r}")
        super().__init__(master_=master_, filter_name=filter_name, display=display, values=values, on_change=on_change)
        logging.debug(f"{_tag} branch=base-built menu={self.menu!r} content={self.filter_content!r}")

        self.filters: list[tk.CTkLabel] = []
        self.delete_btn = tk.CTkButton(
            master=self,
            text='delete',
            width=64,
            command=self._on_user_delete
        )
        # 先 pack 的靠右更远: menu 在父类里已 pack 到最右, delete 落在它左边
        self.delete_btn.pack(side='right', padx=(0, 0), pady=6)
        logging.debug(f"{_tag} branch=delete-btn-packed")

        # 注意: 这里不注册任何回调。选择语义靠 override _apply_select,
        # UI 投影靠 override _render_content, 由父类 _emit 按顺序驱动。
        logging.debug(f"{_tag} exit filters={len(self.filters)}")

    def _apply_select(self, selected_value: str) -> None:
        # 多选累积: 只改数据模型, 重复值在模型层就被拦掉, 不产生任何 UI 抖动
        _tag = "[DropdownFrame._apply_select]"
        logging.debug(f"{_tag} entry selected_value={selected_value!r} name={self.filter_name!r} before={self.filter_content!r}")
        if selected_value in self.filter_content:
            logging.debug(f"{_tag} branch=duplicate selected_value={selected_value!r}, 不重复累积")
            return
        new_content = [*self.filter_content, selected_value]
        logging.debug(f"{_tag} branch=append selected_value={selected_value!r} new={new_content!r}")
        self._update_filter_content(new_content, 'select-append')

    def _render_content(self, reason: str) -> None:
        # 把 filter_content 投影到 label 列表: 模型是权威, UI 只是投影
        _tag = "[DropdownFrame._render_content]"
        wanted = list(self.filter_content)
        existing_texts = [label.cget('text') for label in self.filters]
        logging.debug(f"{_tag} entry reason={reason!r} wanted={wanted!r} existing={existing_texts!r}")

        # 1) 下掉模型里已经不存在的 label
        for label in tuple(self.filters):
            label_text = label.cget('text')
            if label_text in wanted:
                logging.debug(f"{_tag} branch=keep label={label_text!r}")
                continue
            logging.debug(f"{_tag} branch=drop label={label_text!r}")
            label.destroy()
            self.filters.remove(label)

        # 2) 补齐模型里有但界面缺的 label, 顺序按 filter_content
        existing_texts = {label.cget('text') for label in self.filters}
        for label_text in wanted:
            if label_text in existing_texts:
                continue
            logging.debug(f"{_tag} branch=create label={label_text!r}")
            label = tk.CTkLabel(master=self, text=label_text, corner_radius=6, padx=8)
            # before=self.menu 保证插到 menu + delete button 之前(左边)
            label.pack(side='left', before=self.menu, padx=(0, 4), pady=6)
            self.filters.append(label)
            existing_texts.add(label_text)

        logging.debug(f"{_tag} exit labels={len(self.filters)} content={self.filter_content!r}")

    def _on_user_delete(self) -> None:
        _tag = "[DropdownFrame._on_user_delete]"
        logging.debug(f"{_tag} entry name={self.filter_name!r} content={self.filter_content!r}")
        if not self.filter_content:
            logging.warning(f"{_tag} branch=empty, nothing to delete")
            return
        removed = self.filter_content[-1]
        new_content = self.filter_content[:-1]
        logging.debug(f"{_tag} branch=drop-last removed={removed!r} remaining={new_content!r}")
        # 只走一条改内容的路径, _update_filter_content 内部会触发 _render_content
        self._update_filter_content(new_content, 'delete-last')
        # 删除也是状态变更, 外部必须收到通知, 否则筛选条件会静默过期。
        # 删除没有"被点选的值", 传空串; 订阅方回查 selected_values() 拿最新内容。
        self._notify_change('delete', '')


class SimpleDropdownFrame(BaseDropdownFrame):
    """单选直通型: 无累积、无删除、无额外控件。

    行为全部继承自父类: _apply_select 默认即"覆盖", _render_content 默认 noop。
    本类存在的唯一意义 —— 让 add_filter(simple=True) 拿到一个不带 delete 按钮的实例,
    并且产出同样形状的数据: filter_name + filter_content。
    """

    def __init__(self, master_, filter_name: str, display: str, values: list[str], on_change: Callable[..., None]):
        _tag = "[SimpleDropdownFrame.__init__]"
        logging.debug(f"{_tag} entry filter_name={filter_name!r} display={display!r} values={values!r}")
        super().__init__(master_=master_, filter_name=filter_name, display=display, values=values, on_change=on_change)

        # CTkOptionMenu 默认就显示 values[0], 但父类把 filter_content 初始化成空列表。
        # 不补齐的话: 用户从没点过菜单, 界面却已经"显示"了一个值, 模型却是空 —— 筛选必然对不上。
        self.select('')
        logging.debug(f"{_tag} exit content={self.filter_content!r} title={self.title.cget('text')!r}")

    def set_displayed(self, value: str) -> None:
        """把菜单显示同步成 value(不触发回调)。用于"外面重置了状态, 界面要跟上"的场景。"""
        logging.debug(f"[SimpleDropdownFrame.set_displayed] entry value={value!r} current={self.menu.get()!r}")
        if not value:
            logging.debug("[SimpleDropdownFrame.set_displayed] branch=empty, 跳过")
            return
        self.menu.set(value)
        self._update_filter_content([value], 'set-displayed')
        logging.debug(f"[SimpleDropdownFrame.set_displayed] exit displayed={self.menu.get()!r} content={self.filter_content!r}")

app = FoodApp()
app.mainloop()
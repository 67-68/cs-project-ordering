from typing import Any, Callable, Tuple

import customtkinter as tk
import logging
from food_card import PolishedFoodCard
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

from food_model import AppData, load_app_data

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

    def _on_filter_changed(self, filter_name: str) -> None:
        # 父类 _notify_change 传的是 filter_name(key), 不是被点选的内容;
        # 内容请用 get_filters() 统一读取, 避免事件里出现"半更新"的快照
        logging.debug(f"[_on_filter_changed] filter_name={filter_name!r} snapshot={self.get_filters()!r}")

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
                # 菜单值永远是 str, 而字段可能是 int(distance_km) -> 统一转 str 再比
                if str(getattr(food, name)) in wanted:
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
        logging.info(f"[on_order_click] branch=order food_id={food_id!r}")


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
            back_frame = BackFrame(top_frame)
            back_frame.pack(side='right', padx=(0, 8))
            pages.append(page)

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
        self.add_filter('food_component', 'allergies', ['test'], self.search_controls, 'top')
        self.location_filter = self.add_filter('distance_km', 'distance', ['test'], self.search_controls, 'top', simple=True)

        self.search_button = tk.CTkButton(master=self.search_controls, text='search', height=32, command=self.on_searched)
        self.search_button.pack(side='top', fill='x', padx=4, pady=(6, 0))

        self.food_list_container = tk.CTkScrollableFrame(
            master=self.search_page,
            label_text='Available food',
            corner_radius=10,
        )
        self.food_list_container.pack(side='top', fill="both", expand=True, padx=4, pady=(0, 4))
        logging.debug(f"[init_search_page] built controls + list, total_filters={len(self.filters)}")


class BackFrame(tk.CTkFrame):
    def __init__(self,master_):
        super().__init__(master=master_, fg_color="transparent")
        # 没给 text 的按钮是空白的, 先在视觉上补个占位文案
        self.backbtn = tk.CTkButton(master=self, text='back', width=64)
        self.quitbtn = tk.CTkButton(master=self, text='quit', width=64)
        self.backbtn.pack(side='left', padx=(0, 6))
        self.quitbtn.pack(side='left', padx=(0, 0))

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
        # 2) 模型已是最新, 通知外部; 传快照比传原始值更有用, 订阅方不用再回查
        self._notify_change('select')

    def _notify_change(self, reason: str) -> None:
        _tag = f"[{type(self).__name__}._notify_change]"
        snapshot = self.selected_values()
        logging.debug(f"{_tag} entry reason={reason!r} name={self.filter_name!r} snapshot={snapshot!r} has_callback={self.on_change is not None}")
        if self.on_change is None:
            logging.debug(f"{_tag} branch=no-callback, 只更新模型")
            return
        
        logging.debug(f"{_tag} branch=fire callback={getattr(self.on_change, '__name__', repr(self.on_change))}")
        self.on_change(self.filter_name)

    # ---------------- 数据模型面 ----------------

    def selected_values(self) -> list[str]:
        """当前选择内容 (统一数据模型), 由 get_filters() 读取。返回副本, 外部改不动内部状态。"""
        snapshot = list(self.filter_content)
        logging.debug(f"[{type(self).__name__}.selected_values] name={self.filter_name!r} content={snapshot!r}")
        return snapshot

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
        # 删除也是状态变更, 外部必须收到通知, 否则筛选条件会静默过期
        self._notify_change('delete')


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
        default_value = self.menu.get()
        logging.debug(f"{_tag} branch=align-default default_value={default_value!r} content={self.filter_content!r}")
        if default_value:
            self._update_filter_content([default_value], 'init-default')
        else:
            logging.warning(f"{_tag} branch=empty-default, 菜单没有默认值, 内容保持为空")
        logging.debug(f"{_tag} exit content={self.filter_content!r} title={self.title.cget('text')!r}")

app = FoodApp()
app.mainloop()
from typing import Any, Callable, Tuple

import customtkinter as tk
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

class FoodApp(tk.CTk):
    def __init__(self):
        super().__init__()
        # tkinter 的 self.title 是方法, 赋值字符串会覆盖方法, 标题永远设不上 -> 用 self.title(...)
        self.title('food system')
        self.filters: list[tk.CTkFrame] = []
        self.geometry("600x500")
        self.minsize(480, 380)
        # 三个 page 都 grid 在同一 cell, 不配置权重的话窗口变大时 page 不会跟着拉伸
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        logging.debug("[FoodApp.__init__] grid weights set (row0/col0=1)")
        self.init_pages()
        self.init_search_page()

    def _on_filter_changed(self, selected_value: str) -> None:
        logging.debug(f"[build_query] Filter updated: {selected_value}")
        # ... implementation details: 调用 build_query -> fetch_food_list 刷新列表 ...

    def init_pages(self):
        logging.info('start init pages')
        pages = []
        
        for i in range(3):
            # 每个 page 自带一圈内边距, 免得控件贴着窗口边缘
            page = tk.CTkFrame(master=self, corner_radius=10)
            page.grid(row=0, column=0, sticky='nsew', padx=12, pady=12)
            # 注意: page 的子控件全部用 pack 布局, 这里不要再混 grid_rowconfigure
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

    def add_filter(self, name: str, value: list[str], master, side: str, simple: bool = False) -> tk.CTkFrame:
        # 分支: simple=True -> 单选 SimpleDropdownFrame; simple=False -> 多条件 DropdownFrame
        filter_cls = DropdownFrame if not simple else SimpleDropdownFrame
        logging.debug(f"[add_filter] entry name={name!r} values={value!r} master={master!r} side={side!r} simple={simple} cls={filter_cls.__name__}")
        if not value:
            logging.warning(f"[add_filter] branch=empty-values, menu would have nothing to choose, name={name!r}")
        # on_change 必须是可调用对象, 这里传 self._on_filter_changed
        filter_ = filter_cls(
            master_=master,
            text=name,
            values=value,
            on_change=self._on_filter_changed
        )
        logging.debug(f"[add_filter] branch=created obj={filter_.__class__.__name__}")
        self.filters.append(filter_)
        # fill='x' 让滤镜条横向铺满, pady 给它和邻居留呼吸空间
        filter_.pack(side=side, fill='x', padx=4, pady=4)
        logging.debug(f"[add_filter] branch=packed side={side!r} total={len(self.filters)}")
        return filter_

    def get_filters(self):
        # get each filter's name and their exclude str
        pass
    
    def init_search_page(self):
        # 控件区容器: 上方是滤镜/按钮, 下方是滚动列表, 两者都能横向铺满
        self.search_controls = tk.CTkFrame(master=self.search_page, fg_color="transparent")
        self.search_controls.pack(side='top', fill='x', padx=4, pady=(4, 8))

        self.add_filter('allergies',['test'],self.search_controls,'top')
        self.location_filter = self.add_filter('location',['test'],self.search_controls,'top',simple=True)

        self.search_button = tk.CTkButton(master=self.search_controls, text='search', height=32)
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

class DropdownFrame(tk.CTkFrame):
    def __init__(self,master_,text: str, values: list[str], on_change: Callable[..., None]):
        super().__init__(master=master_, corner_radius=8)
        self.filters: list[tk.CTkLabel] = []
        self.title = tk.CTkLabel(master=self, text=text, width=70, anchor='w')
        self.title.pack(side='left', padx=(10, 6), pady=6)
        self.menu = tk.CTkOptionMenu(
            master=self,
            values=values,
            command=self._on_user_add,
            width=110,
        )
        # 先 pack 的靠右更远: menu 在最右, delete 在它左边
        self.menu.pack(side='right', padx=(6, 10), pady=6)
        self.delete_btn = tk.CTkButton(
            master=self,
            text='delete',
            width=64,
            command=self._on_user_delete
        )
        self.delete_btn.pack(side='right', padx=(0, 0), pady=6)
        logging.debug(f"[DropdownFrame.__init__] built title={text!r} values={values!r}")

    def _on_user_add(self, selected_value: str) -> None:
        # command 回调由 CTkOptionMenu 传入被选中的值, 必须接收该参数
        condition = selected_value
        logging.debug(f"[DropdownFrame._on_user_add] entry selected_value={condition!r} filters={[w.cget('text') for w in self.filters]}")
        if not condition:
            return
        for item in self.filters:
            if item.cget('text') == condition:
                break
        else:
            logging.debug(f"[DropdownFrame._on_user_add] branch=new, create label {condition!r}")
            frame = tk.CTkLabel(master=self, text=condition, corner_radius=6, padx=8)
            # before=self.menu 保证插到 menu + delete button 之前(左边)
            frame.pack(side='left', before=self.menu, padx=(0, 4), pady=6)
            self.filters.append(frame)
            logging.debug(f"[DropdownFrame._on_user_add] packed filter label={condition!r}")

    def _on_user_delete(self) -> None:
        # 找到最后一个filter 内容并进行删除
        if not self.filters:
            logging.warning("[DropdownFrame._on_user_delete] branch=empty, nothing to delete")
            return
        victim = self.filters.pop()
        victim.destroy()

class SimpleDropdownFrame(tk.CTkFrame):
    def __init__(self,master_,text: str, values: list[str], on_change: Callable[..., None]):
        super().__init__(master=master_, corner_radius=8)
        self.title = tk.CTkLabel(master=self, text=text, width=70, anchor='w')
        self.title.pack(side='left', padx=(10, 6), pady=6)
        self.dropdown = tk.CTkOptionMenu(
            master=self,
            values=values,
            command=on_change,
            width=110,
        )
        # 原来只创建没 pack, 控件在界面上完全不可见
        self.dropdown.pack(side='right', padx=(6, 10), pady=6)
        logging.debug(f"[SimpleDropdownFrame.__init__] built title={text!r} values={values!r}")

app = FoodApp()
app.mainloop()

# TODO: 具体设计食物卡片。
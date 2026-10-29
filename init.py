from typing import Any, Callable, Tuple

import customtkinter as tk
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

class FoodApp(tk.CTk):
    def __init__(self):
        super().__init__()
        self.title = 'food system'
        self.filters: list[tk.CTkFrame] = []
        self.geometry("600x500")
        self.init_pages()
        self.init_search_page()

    def _on_filter_changed(self, selected_value: str) -> None:
        logging.debug(f"[build_query] Filter updated: {selected_value}")
        # ... implementation details: 调用 build_query -> fetch_food_list 刷新列表 ...

    def init_pages(self):
        logging.info('start init pages')
        pages = []
        
        for i in range(3):
            page = tk.CTkFrame(master=self)
            page.grid(row=0,column=0,sticky='nsew')
            top_frame = tk.CTkFrame(master=page)
            name_label = tk.CTkLabel(master=top_frame)
            name_label.pack(side='left')
            back_frame = BackFrame(top_frame)
            back_frame.pack(side='right')
            top_frame.pack(side='top')
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
        filter_.pack(side=side)
        return filter_

    def get_filters(self):
        # get each filter's name and their exclude str
        pass
    
    def init_search_page(self):
        self.add_filter('allergies',['test'],self.search_page,'top')
        self.location_filter = self.add_filter('location',['test'],self.search_page,'top',simple=True)
        self.search_button = tk.CTkButton(master=self.search_page,text='search')
        self.search_button.pack(side='top')
        self.food_list_container = tk.CTkScrollableFrame(
            master=self.search_page,
            label_text='Available food'
        )
        self.food_list_container.pack(side='top',fill="both", expand=True, padx=10, pady=10)


class BackFrame(tk.CTkFrame):
    def __init__(self,master_):
        super().__init__(master=master_)
        self.backbtn = tk.CTkButton(master=self)
        self.quitbtn = tk.CTkButton(master=self)
        self.backbtn.pack(side='left',expand=True)
        self.quitbtn.pack(side='left',expand=True)

class DropdownFrame(tk.CTkFrame):
    def __init__(self,master_,text: str, values: list[str], on_change: Callable[..., None]):
        super().__init__(master=master_)
        self.filters: list[tk.CTkLabel] = []
        self.title = tk.CTkLabel(master=self,text=text)
        self.title.pack(side='left')
        self.menu = tk.CTkOptionMenu(
            master=self,
            values=values,
            command=self._on_user_add
        )
        self.menu.pack(pady=5,side='right')
        self.delete_btn = tk.CTkButton(
            master=self,
            text='delete',
            command=self._on_user_delete
        )
        self.delete_btn.pack(pady=5,side='right')

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
            frame = tk.CTkLabel(master=self,text=condition)
            # before=self.menu 保证插到 menu + delete button 之前(左边)
            frame.pack(side='left', before=self.menu)
            self.filters.append(frame)

    def _on_user_delete(self) -> None:
        # 找到最后一个filter 内容并进行删除
        if not self.filters:
            logging.warning("[DropdownFrame._on_user_delete] branch=empty, nothing to delete")
            return
        victim = self.filters.pop()
        victim.destroy()

class SimpleDropdownFrame(tk.CTkFrame):
    def __init__(self,master_,text: str, values: list[str], on_change: Callable[..., None]):
        super().__init__(master=master_)
        self.title = tk.CTkLabel(master=self,text=text)
        self.title.pack(side='left')
        self.dropdown = tk.CTkOptionMenu(master=self,values=values,command=on_change)
        # 原来只创建没 pack, 控件在界面上完全不可见
        self.dropdown.pack(side='right')

app = FoodApp()
app.mainloop()

# TODO: 具体设计食物卡片。
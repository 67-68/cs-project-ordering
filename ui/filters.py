"""下拉滤镜家族: 一个抽象骨架 + 两个具体变体。

继承结构:
    BaseDropdownFrame  (骨架 + 数据模型 + 事件出口, 永不被实例化)
      ├── DropdownFrame       多选累积, 带 delete 按钮
      └── SimpleDropdownFrame 单选覆盖, 无额外控件

三个钩子:
    _apply_select(value)   选中语义(累积 / 覆盖)
    _render_content(reason) UI 投影
    _notify_change(...)    唯一事件出口, 不可 override
"""
import logging
from typing import Callable

import customtkinter as tk


class BaseDropdownFrame(tk.CTkFrame):
    """下拉滤镜家族的唯一父类: 只负责骨架 + 数据模型 + 事件出口, 自身永不被实例化。

    契约:
      1. 数据模型(filter_name / display / filter_content)由父类持有,
         子类只通过 _update_filter_content() 改;
      2. 想改"选中语义" -> override _apply_select(多选累积就是这么做的);
      3. 想改"UI 投影"   -> override _render_content(多选 label 就是这么做的);
      4. 不要 override _emit, 它保证 on_change 一定在模型更新之后触发。
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

        契约: 回调收到的是 **刚被点选的那个值**(str), 不是 filter_name。
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

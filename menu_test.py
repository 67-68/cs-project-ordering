"""Menu smoke test: one window, two buttons, both public doors.

    button 1  open_food_app()                 -> separate OS process, own window
    button 2  create_food_app_frame(master)   -> frame mounted into THIS window

Each button calls exactly one interface function and nothing else. No direct use
of FoodApp / FoodAppFrame classes, no hand rolled app widgets, so a green run
means the public surface in init.py is actually usable.

Run:  python menu_test.py
Also: python init.py            (standalone window, same app)
"""
import logging

import customtkinter as tk

from init import create_food_app_frame, open_food_app

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

# menu shell size vs. the size the embedded app needs to look right
MENU_SIZE = "360x220"
EMBEDDED_SIZE = "640x560"


class MenuWindow(tk.CTk):
    """Plain menu shell. Deliberately dumb: it only knows the two interface functions."""

    def __init__(self):
        _tag = "[MenuWindow.__init__]"
        super().__init__()
        logging.debug(f"{_tag} root created")

        self.title('menu test')
        self.geometry(MENU_SIZE)
        self.minsize(280, 180)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # holds either the menu shell or the embedded app, never both
        self.slot = tk.CTkFrame(master=self, fg_color="transparent")
        self.slot.grid(row=0, column=0, sticky='nsew')
        self.slot.grid_rowconfigure(0, weight=1)
        self.slot.grid_columnconfigure(0, weight=1)

        # at most one embedded app at a time
        self.app_frame = None

        self.body = tk.CTkFrame(master=self.slot, corner_radius=12)
        self.body.grid(row=0, column=0, sticky='nsew', padx=12, pady=12)
        # row 4 is an empty spacer, only it absorbs the extra height; giving weight
        # to a button row would stretch the button itself
        self.body.grid_rowconfigure(4, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.title_label = tk.CTkLabel(
            master=self.body,
            text='menu',
            font=tk.CTkFont(size=20, weight='bold'),
            anchor='w',
        )
        self.title_label.grid(row=0, column=0, sticky='w', padx=12, pady=(12, 8))

        self.state_label = tk.CTkLabel(
            master=self.body,
            text='no app open',
            font=tk.CTkFont(size=12),
            anchor='w',
        )
        self.state_label.grid(row=1, column=0, sticky='w', padx=12, pady=(0, 6))

        # door 1: brand new process
        self.open_process_btn = tk.CTkButton(
            master=self.body,
            text='open food app (new process)',
            height=40,
            corner_radius=10,
            font=tk.CTkFont(size=14, weight='bold'),
            command=self._on_open_process_clicked,
        )
        self.open_process_btn.grid(row=2, column=0, sticky='ew', padx=12, pady=(0, 6))

        # door 2: frame mounted right here
        self.open_frame_btn = tk.CTkButton(
            master=self.body,
            text='open food app (embedded frame)',
            height=40,
            corner_radius=10,
            font=tk.CTkFont(size=14, weight='bold'),
            command=self._on_open_frame_clicked,
        )
        self.open_frame_btn.grid(row=3, column=0, sticky='ew', padx=12, pady=(0, 12))

        self.spacer = tk.CTkFrame(master=self.body, fg_color="transparent", height=1)
        self.spacer.grid(row=4, column=0, sticky='nsew')

        logging.info(f"{_tag} menu ready, size={MENU_SIZE}")

    # ---------- door 1: subprocess ----------

    def _on_open_process_clicked(self) -> None:
        _tag = "[menu.open_process]"
        logging.info(f"{_tag} button clicked, calling open_food_app()")
        # single call, single responsibility; non blocking so the menu stays alive
        process = open_food_app()
        if process is None:
            logging.error(f"{_tag} open_food_app() returned None, window was not launched")
            self.state_label.configure(text='launch failed, see console')
            return
        logging.info(f"{_tag} food app launched, pid={process.pid}")
        self.state_label.configure(text=f'separate process pid {process.pid}')

    # ---------- door 2: embedded frame ----------

    def _on_open_frame_clicked(self) -> None:
        _tag = "[menu.open_frame]"
        logging.info(f"{_tag} button clicked")

        if self.app_frame is not None:
            logging.warning(f"{_tag} an app frame is already mounted, ignoring click")
            self.state_label.configure(text='app frame already mounted')
            return

        logging.debug(f"{_tag} asking init.py for a ready made frame")
        # the caller owns the layout: we hand over our slot and quit semantics
        frame = create_food_app_frame(master=self.slot, on_quit=self._on_embedded_quit)

        if frame is None:
            logging.error(f"{_tag} create_food_app_frame() returned None")
            self.state_label.configure(text='frame build failed, see console')
            return

        self.app_frame = frame
        # menu shell steps aside, the app takes the whole window
        self.body.grid_remove()
        self.app_frame.grid(row=0, column=0, sticky='nsew')
        self.geometry(EMBEDDED_SIZE)
        logging.info(f"{_tag} frame mounted, window resized to {EMBEDDED_SIZE}")

    def _on_embedded_quit(self) -> None:
        """The frame handed quitting back to us; we decide it means 'back to menu'."""
        _tag = "[menu.embedded_quit]"
        if self.app_frame is None:
            logging.warning(f"{_tag} quit on an unmounted frame, nothing to do")
            return
        # this runs inside the frame's own button callback; destroying that widget
        # right now would pull the rug out from under the event dispatch
        logging.info(f"{_tag} quit requested, deferred teardown scheduled")
        self.after_idle(self._teardown_embedded_frame)

    def _teardown_embedded_frame(self) -> None:
        _tag = "[menu.teardown]"
        if self.app_frame is None:
            logging.warning(f"{_tag} teardown on an unmounted frame, nothing to do")
            return
        logging.info(f"{_tag} destroying the embedded frame")
        self.app_frame.destroy()
        self.app_frame = None
        self.body.grid()
        self.geometry(MENU_SIZE)
        self.state_label.configure(text='no app open')
        logging.info(f"{_tag} back to menu, size={MENU_SIZE}")


def main() -> None:
    logging.info("[menu_test.main] starting menu")
    window = MenuWindow()
    window.mainloop()
    logging.info("[menu_test.main] menu closed")


if __name__ == "__main__":
    main()

import tkinter as tk
import ctypes
import sys
import json
from tkinter import filedialog, messagebox
from pathlib import Path

BG = '#171b23'
PANEL = '#222936'
KEY = '#303b4b'
ACTIVE = '#5bc6a6'
FG = '#e8f3ed'
MUTED = '#a7b9b4'

MAP = {'7': 'ABC', '8': 'DEF', '9': 'GHI', '4': 'JKL', '5': 'MNO', '6': 'PQRS', '1': 'TUV', '2': 'WXYZ', '3': '.,?!'}

class KeyboardApp:
    def __init__(self, root):
        self.root = root
        root.title('10Keyboard | Ring 0.8.0')
        # Distinguish 10Keyboard from generic Python.
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                'ColorsOfFractals.10Keyboard'
            )

        # Native Windows icon for title bar and taskbar.
        icon_path = Path(__file__).resolve().parent / 'assets' / '10Keyboard.ico'

        if icon_path.is_file():
            root.iconbitmap(default=str(icon_path))

        root.geometry('940x620')
        root.minsize(720, 460)
        root.configure(bg=BG)
        self.filepath = None
        self.pending = None
        self.last_key = None
        self.index = 0
        self.timeout = 1000
        self.timer = None
        self.pressed = set()
        self.buttons = {}
        self.mode = 'MULTI-TAP'
        self.uppercase = True
        self.t9_digits = ''
        self.t9_start = None
        self.t9_matches = []
        self.t9_index = 0
        words = '''HELLO WORLD DUDE THIS WORKS GOOD YES LIKE LOL
        THE AND YOU ARE FOR WITH HAVE THAT FROM YOUR NOT BUT
        ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN
        I WE HE SHE IT THEY THEM ME MY OUR THEIR TO OF IN ON
        AT AS IS WAS BE BEEN DO DID DOES CAN COULD WOULD
        SHOULD WILL JUST REALLY VERY COOL FUN NICE AWESOME
        KEYBOARD PHONE TEXT TYPE TYPING WORD WORDS LETTER
        LETTERS SPACE DELETE ENTER TEST TESTING PYTHON
        COMPUTER NUMPAD TIME TIMER MODE PREDICTIVE MESSAGE
        LOVE GREAT HAPPY HOW WHAT WHEN WHERE WHY WHO THERE
        HERE HOME WORK PLAY GAME MUSIC SONG APP CODE MAKE
        MADE MORE LESS MUCH LITTLE BIG SMALL FAST SLOW
        QUICK BROWN FOX JUMPS OVER LAZY DOG CAT FRIEND
        FRIENDS GOODBYE THANK THANKS PLEASE OK OKAY
        TODAY TOMORROW NIGHT MORNING EVENING NEW OLD
        RETRO CLASSIC NOSTALGIA SIMPLE EASY HARD FIRST
        SECOND THIRD AGAIN NEXT BACK RIGHT LEFT UP DOWN
        OPEN SAVE COPY FILE NOTE NOTES NOTEPAD YES NO
        MAYBE SOMETHING ANYTHING EVERYTHING NOTHING
        ABOUT AFTER BEFORE BECAUSE IF THEN SO OR AN A
        SEE SAY SAID KNOW THINK THING THINGS LOOK LOOKS
        FEEL FEELS GO GOING COME COMING GET GOT WANT
        NEED USE USING USED SOME MANY ONLY ALSO ALL
        PEOPLE PERSON MAN WOMAN DAY DAYS YEAR YEARS
        NOW LATER NEVER ALWAYS SOMETIMES REALLY
        AMAZING BEAUTIFUL PERFECT FINE TRUE FALSE
        HAHA HAHAHA LMAO'''.split()
        # Extend the original dictionary with words.txt.
        # Keep the built-in vocabulary as a fallback.
        dictionary_path = Path(__file__).resolve().with_name('words.txt')

        if dictionary_path.is_file():
            extra_words = dictionary_path.read_text(
                encoding='utf-8-sig'
            ).upper().split()
            words = list(dict.fromkeys(words + extra_words))

        self.t9_words = {}
        for word in words:
            digits = ''.join(next((k for k, v in MAP.items()
                                   if c in v), '') for c in word)
            if len(digits) == len(word):
                self.t9_words.setdefault(digits, []).append(word)
        self.build()
        self.init_themes()
        self.editor.bind('<KeyPress>', self.on_press)
        self.editor.bind(
            '<KeyPress>',
            self.handle_numpad_controls,
            add='+'
        )
        self.editor.bind('<KeyRelease>', self.on_release)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.editor.focus_set()

        # Windows physical numpad shortcuts.
        # Confirmed by hardware survey:
        # Divide = VK 111, Multiply = VK 106.
        self.root.bind_all(
            '<KeyPress>',
            self.handle_numpad_controls,
            add='+'
        )



    def build(self):
        top = tk.Frame(self.root, bg=BG, padx=20, pady=14)
        top.pack(fill='x')
        tk.Label(top, text='10Keyboard', bg=BG, fg=FG, font=('Segoe UI', 23, 'bold')).pack(side='left')
        tk.Label(top, text='  •  RETRO MULTI-TAP TYPEWRITER', bg=BG, fg=ACTIVE, font=('Consolas', 10)).pack(side='left')
        for label, fn in [('New', self.new), ('Open', self.open_file), ('Save', self.save), ('Save As', self.save_as), ('Copy', self.copy_all)]:
            tk.Button(top, text=label, command=fn, bg=PANEL, fg=FG, activebackground=KEY, activeforeground=FG, relief='flat', padx=10, pady=6).pack(side='right', padx=3)

        controls = tk.Frame(self.root, bg=BG, padx=20, pady=3)
        controls.pack(fill='x')
        self.mode_button = tk.Button(
            controls, text='MODE: MULTI-TAP',
            command=self.toggle_mode, bg=KEY, fg=FG,
            activebackground=ACTIVE, relief='flat', padx=15, pady=7)
        self.mode_button.pack(side='left', padx=(0, 8))
        self.case_button = tk.Button(
            controls, text='ABC', command=self.toggle_case,
            bg=KEY, fg=ACTIVE, activebackground=ACTIVE,
            relief='flat', padx=18, pady=7)
        self.case_button.pack(side='left')
        self.suggestion = tk.Label(
            controls, text='', bg=BG, fg=ACTIVE,
            font=('Consolas', 10))
        self.suggestion.pack(side='left', padx=15)

        body = tk.PanedWindow(self.root, orient='horizontal', bg=BG, sashwidth=7, sashrelief='flat', bd=0)
        body.pack(fill='both', expand=True, padx=16, pady=(0, 12))
        left = tk.Frame(body, bg=PANEL)
        right = tk.Frame(body, bg=BG, width=320)
        body.add(left, minsize=330, stretch='always')
        body.add(right, minsize=280)
        tk.Label(left, text='NOTEPAD.TXT', bg=PANEL, fg=ACTIVE, font=('Consolas', 10, 'bold'), anchor='w', padx=14, pady=12).pack(fill='x')
        self.editor = tk.Text(left, bg=PANEL, fg=FG, insertbackground=ACTIVE, selectbackground='#366b65', font=('Consolas', 14), relief='flat', padx=16, pady=8, undo=True, wrap='word')
        self.editor.pack(fill='both', expand=True)
        self.editor.bind('<<Modified>>', self.on_modified)
        self.status = tk.Label(left, text='0 characters  •  Untitled', bg=PANEL, fg=MUTED, anchor='w', padx=14, pady=8, font=('Consolas', 9))
        self.status.pack(fill='x')
        # Scrollable right-hand control column.
        self.right_canvas = tk.Canvas(
            right,
            bg=BG,
            bd=0,
            highlightthickness=0,
            relief='flat'
        )

        self.right_scrollbar = tk.Canvas(
            right,
            width=13,
            bg=BG,
            bd=0,
            relief='flat',
            highlightthickness=0,
            cursor='hand2'
        )
        self.scroll_fraction = (0.0, 1.0)
        self.scroll_hover = False
        self.scroll_drag_y = None

        self.right_scrollbar.bind(
            '<Configure>', self.draw_chromatic_scrollbar
        )
        self.right_scrollbar.bind(
            '<Enter>', self.scrollbar_enter
        )
        self.right_scrollbar.bind(
            '<Leave>', self.scrollbar_leave
        )
        self.right_scrollbar.bind(
            '<Button-1>', self.scrollbar_click
        )
        self.right_scrollbar.bind(
            '<B1-Motion>', self.scrollbar_drag
        )
        self.right_scrollbar.bind(
            '<ButtonRelease-1>', self.scrollbar_release
        )
        self.right_scrollbar.pack(side='right', fill='y')

        self.right_canvas.pack(
            side='left', fill='both', expand=True
        )
        self.right_canvas.configure(
            yscrollcommand=self.update_chromatic_scrollbar
        )

        self.right_content = tk.Frame(
            self.right_canvas, bg=BG
        )

        self.right_window = self.right_canvas.create_window(
            (0, 0),
            window=self.right_content,
            anchor='nw'
        )

        self.right_content.bind(
            '<Configure>', self.update_right_scrollregion
        )
        self.right_canvas.bind(
            '<Configure>', self.resize_right_content
        )

        tk.Label(self.right_content, text='DIGITAL 10-KEY', bg=BG, fg=ACTIVE, font=('Consolas', 12, 'bold')).pack(anchor='w', padx=12, pady=(4, 10))
        pad = tk.Frame(self.right_content, bg=BG)
        pad.pack(fill='x', padx=10)
        rows = [('7','8','9'), ('4','5','6'), ('1','2','3'), ('0','.','+')]
        for r, row in enumerate(rows):
            pad.grid_rowconfigure(r, weight=1)
            for c, key in enumerate(row):
                pad.grid_columnconfigure(c, weight=1)
                sub = MAP.get(key, {'0':'SPACE', '.':'DELETE', '+':'COPY *'}[key] if key in ('0','.','+') else '')
                b = tk.Button(pad, text=f'{key}\n{sub}', command=lambda k=key: self.copy_all() if k == '+' else self.tap(k), font=('Consolas', 13, 'bold'), bg=KEY, fg=FG, activebackground=ACTIVE, activeforeground=BG, relief='flat', bd=0, height=3, cursor='hand2')
                b.grid(row=r, column=c, padx=3, pady=3, sticky='nsew')
                self.buttons[key] = b
        self.preview = tk.Label(self.right_content, text='READY  •  NUM LOCK ON', bg=BG, fg=ACTIVE, font=('Consolas', 11, 'bold'), pady=12)
        self.preview.pack(fill='x')
        # Compact guide generated from the live keymap.
        guide_lines = [
            'HOW TO TYPE',
            '---------------------',
            ''
        ]

        for row in ('789', '456', '123'):
            guide_lines.append(
                '    '.join(
                    f'{key} {MAP[key]}'
                    for key in row
                )
            )

        guide_lines.extend([
            '',
            'MULTI-TAP',
            '---------------------',
            '7     A',
            '77    B',
            '777   C',
            '',
            'Tap repeatedly to cycle.',
            'Wait 1 second to finish.',
            '',
            'CONTROLS',
            '---------------------',
            '0       Space',
            '.       Delete',
            '+       Copy all text',
            'Enter   New line',
            '/       Multi-Tap / T9',
            '*       ABC / abc',
            '',
            'Normal typing also works.'
        ])

        guide = '\n'.join(guide_lines)
        self.multitap_guide = guide
        self.guide_frame = tk.Frame(self.right_content, bg=PANEL)
        self.guide_frame.pack(
            fill='x', padx=10, pady=(2, 12)
        )

        self.guide = tk.Text(
            self.guide_frame,
            bg=PANEL,
            fg=MUTED,
            font=('Consolas', 10),
            relief='flat',
            bd=0,
            padx=16,
            pady=15,
            wrap='word',
            cursor='arrow',
            highlightthickness=0,
            height=17
        )
        self.guide.pack(fill='x')
        self.set_guide_text(guide)

        self.root.bind_all(
            '<MouseWheel>',
            self.scroll_right_column,
            add='+'
        )



    def update_chromatic_scrollbar(self, first, last):
        self.scroll_fraction = (float(first), float(last))
        self.draw_chromatic_scrollbar()

    def draw_chromatic_scrollbar(self, event=None):
        if not hasattr(self, 'right_scrollbar'):
            return

        canvas = self.right_scrollbar
        canvas.delete('all')

        t = getattr(self, 'palette', None)
        if not t:
            return

        w = max(canvas.winfo_width(), 13)
        h = max(canvas.winfo_height(), 1)

        canvas.create_rectangle(
            0, 0, w, h,
            fill=t['bg'], outline=''
        )

        first, last = self.scroll_fraction
        visible = max(0.0, min(1.0, last - first))

        if visible >= 0.999:
            return

        thumb_h = min(h, max(32, h * visible))
        travel = max(0, h - thumb_h)
        scrollable = max(0.00001, 1.0 - visible)
        position = min(1.0, max(0.0, first / scrollable))
        top = travel * position

        canvas.create_rectangle(
            3, top, w - 3, top + thumb_h,
            fill=t['active'], outline=''
        )

        if self.scroll_hover and thumb_h > 12:
            canvas.create_rectangle(
                5, top + 4, w - 5, top + thumb_h - 4,
                fill=t['fg'], outline=''
            )

    def scrollbar_enter(self, event):
        self.scroll_hover = True
        self.draw_chromatic_scrollbar()

    def scrollbar_leave(self, event):
        self.scroll_hover = False
        self.draw_chromatic_scrollbar()

    def scrollbar_click(self, event):
        first, last = self.scroll_fraction
        visible = last - first

        if visible >= 0.999:
            return

        h = max(self.right_scrollbar.winfo_height(), 1)
        thumb_h = min(h, max(32, h * visible))
        travel = max(h - thumb_h, 1)
        scrollable = max(0.00001, 1.0 - visible)

        thumb_top = (first / scrollable) * travel

        if thumb_top <= event.y <= thumb_top + thumb_h:
            self.scroll_drag_y = event.y - thumb_top
        else:
            self.scroll_drag_y = thumb_h / 2
            self.scrollbar_drag(event)

    def scrollbar_drag(self, event):
        if self.scroll_drag_y is None:
            return

        first, last = self.scroll_fraction
        visible = last - first

        h = max(self.right_scrollbar.winfo_height(), 1)
        thumb_h = min(h, max(32, h * visible))
        travel = max(h - thumb_h, 1)

        pos = max(
            0.0,
            min(1.0, (event.y - self.scroll_drag_y) / travel)
        )

        self.right_canvas.yview_moveto(
            pos * max(0.0, 1.0 - visible)
        )

    def scrollbar_release(self, event):
        self.scroll_drag_y = None

    def update_right_scrollregion(self, event=None):
        self.right_canvas.configure(
            scrollregion=self.right_canvas.bbox('all')
        )

    def resize_right_content(self, event):
        self.right_canvas.itemconfigure(
            self.right_window, width=event.width
        )

    def scroll_right_column(self, event):
        widget = self.root.winfo_containing(
            event.x_root, event.y_root
        )

        current = widget
        inside = False

        while current is not None:
            if current is self.right_canvas or current is self.right_content:
                inside = True
                break
            current = getattr(current, 'master', None)

        if not inside:
            return

        if event.delta:
            steps = -int(event.delta / 120)
            if steps == 0:
                steps = -1 if event.delta > 0 else 1

            self.right_canvas.yview_scroll(steps, 'units')

        return 'break'

    def style_titlebar(self, background, foreground):
        if sys.platform != 'win32':
            return

        try:
            self.root.update_idletasks()

            # Tk's widget HWND may be a child of the decorated window.
            # GetParent retrieves the native window wrapper.
            user32 = ctypes.windll.user32
            user32.GetParent.argtypes = [ctypes.c_void_p]
            user32.GetParent.restype = ctypes.c_void_p

            hwnd = user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()

            def colorref(value):
                value = value.lstrip('#')
                r, g, b = bytes.fromhex(value)
                return r | (g << 8) | (b << 16)

            dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute
            dwm.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint,
                ctypes.c_void_p,
                ctypes.c_uint
            ]
            dwm.restype = ctypes.c_long

            bg = ctypes.c_uint32(colorref(background))
            fg = ctypes.c_uint32(colorref(foreground))

            # Windows 11 DWM caption and text colors.
            result_bg = dwm(
                hwnd, 35, ctypes.byref(bg), ctypes.sizeof(bg)
            )
            result_fg = dwm(
                hwnd, 36, ctypes.byref(fg), ctypes.sizeof(fg)
            )

            if result_bg != 0 or result_fg != 0:
                print(
                    '[TITLEBAR] DWM returned:',
                    hex(result_bg & 0xffffffff),
                    hex(result_fg & 0xffffffff)
                )

        except (AttributeError, OSError, ValueError) as exc:
            print('[TITLEBAR] Styling unavailable:', exc)

    def init_themes(self):
        self.themes = {
            'Cyberdeck': {
                'bg':'#0b111c', 'panel':'#142431',
                'key':'#203848', 'active':'#17e7cb',
                'fg':'#e7fff9', 'muted':'#83b8b5'
            },
            'Nokia LCD': {
                'bg':'#b6c6a1', 'panel':'#cbd8b7',
                'key':'#82976e', 'active':'#435c37',
                'fg':'#253b24', 'muted':'#536b47'
            },
            'Synthwave 89': {
                'bg':'#170d29', 'panel':'#291b43',
                'key':'#49315d', 'active':'#ff4ab8',
                'fg':'#f7e7ff', 'muted':'#a99acb'
            },
            'Vintage Typewriter': {
                'bg':'#d8c7ac', 'panel':'#f0e6d4',
                'key':'#bca184', 'active':'#a46d46',
                'fg':'#453326', 'muted':'#806a55'
            },
            'Obsidian Minimal': {
                'bg':'#090a0e', 'panel':'#171a22',
                'key':'#292d38', 'active':'#c9d5e5',
                'fg':'#f0f2f6', 'muted':'#969eae'
            }
        }

        self.settings_path = (
            Path(__file__).resolve().parent / '10keyboard_settings.json'
        )
        saved = 'Cyberdeck'
        try:
            data = json.loads(self.settings_path.read_text(
                encoding='utf-8'))
            saved = data.get('theme', saved)
        except (OSError, ValueError, TypeError):
            pass

        if saved not in self.themes:
            saved = 'Cyberdeck'

        self.theme_name = tk.StringVar(value=saved)
        host = self.mode_button.master

        self.theme_menu = tk.OptionMenu(
            host, self.theme_name, *self.themes.keys(),
            command=self.apply_theme
        )
        self.theme_menu.pack(side='right', padx=8)
        self.apply_theme(saved)

    def apply_theme(self, name):
        if name not in self.themes:
            return

        t = self.themes[name]
        self.palette = t
        if hasattr(self, 'guide_frame'):
            self.guide_frame.configure(bg=t['panel'])
            self.guide.configure(
                bg=t['panel'],
                fg=t['muted']
            )
            self.right_canvas.configure(bg=t['bg'])
            self.right_content.configure(bg=t['bg'])
            self.right_scrollbar.configure(bg=t['bg'])
            self.draw_chromatic_scrollbar()
        self.style_titlebar(t['bg'], t['fg'])

        # Restyle existing widgets by their original palette role.
        old_colors = {
            BG: 'bg', PANEL: 'panel',
            KEY: 'key', ACTIVE: 'active',
            FG: 'fg', MUTED: 'muted'
        }

        def paint(widget):
            kind = widget.winfo_class()

            for option in ('bg', 'fg'):
                try:
                    current = str(widget.cget(option))
                    role = old_colors.get(current)

                    # Also recognize colors from a previous theme.
                    if role is None:
                        for theme in self.themes.values():
                            for r, color in theme.items():
                                if current == color:
                                    role = r
                                    break
                            if role:
                                break

                    if role:
                        widget.configure(**{option: t[role]})
                except (tk.TclError, KeyError):
                    pass

            if kind == 'Text':
                widget.configure(
                    bg=t['panel'], fg=t['fg'],
                    insertbackground=t['active'],
                    selectbackground=t['key'],
                    selectforeground=t['fg']
                )
            elif kind == 'Button':
                widget.configure(
                    activebackground=t['active'],
                    activeforeground=t['bg'],
                    highlightthickness=0
                )

            for child in widget.winfo_children():
                paint(child)

        paint(self.root)
        self.right_canvas.configure(bg=t['bg'])
        self.right_content.configure(bg=t['bg'])
        self.right_scrollbar.configure(bg=t['bg'])
        self.draw_chromatic_scrollbar()

        # Apply exact roles to important interactive controls.
        self.root.configure(bg=t['bg'])
        self.editor.configure(
            bg=t['panel'], fg=t['fg'],
            insertbackground=t['active']
        )

        for key, button in self.buttons.items():
            button.configure(
                bg=t['active'] if key in self.pressed else t['key'],
                fg=t['bg'] if key in self.pressed else t['fg']
            )

        self.mode_button.configure(bg=t['key'], fg=t['fg'])
        self.case_button.configure(bg=t['key'], fg=t['active'])
        self.theme_menu.configure(
            bg=t['key'], fg=t['fg'],
            activebackground=t['active'],
            activeforeground=t['bg'],
            highlightthickness=0, relief='flat'
        )
        self.theme_menu['menu'].configure(
            bg=t['panel'], fg=t['fg'],
            activebackground=t['active'],
            activeforeground=t['bg']
        )

        try:
            self.settings_path.write_text(
                json.dumps({'theme': name}, indent=2),
                encoding='utf-8'
            )
        except OSError as exc:
            print('[THEME] Settings not saved:', exc)

    def commit(self):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None
        self.pending = None
        self.last_key = None
        self.preview.config(text='READY  •  NUM LOCK ON')

    def handle_numpad_controls(self, event):
        if event.keycode == 111 and event.keysym == 'slash':
            self.toggle_mode()
            return 'break'

        if event.keycode == 106 and event.keysym == 'asterisk':
            self.toggle_case()
            return 'break'

    def toggle_mode(self):
        self.finish_input()
        self.mode = 'T9' if self.mode == 'MULTI-TAP' else 'MULTI-TAP'
        self.mode_button.config(text='MODE: ' + self.mode)
        self.refresh_guide()
        self.editor.focus_set()

    def toggle_case(self):
        self.finish_input()
        self.uppercase = not self.uppercase
        self.case_button.config(text='ABC' if self.uppercase else 'abc')
        for key, button in self.buttons.items():
            sub = MAP.get(key, {'0':'SPACE', '.':'DELETE', '+':'COPY *'}.get(key, ''))
            if key in MAP and not self.uppercase:
                sub = sub.lower()
            button.config(text=f'{key}\n{sub}')
        self.editor.focus_set()

    def finish_input(self):
        if self.mode == 'T9':
            self.accept_t9(False)
        else:
            self.commit()

    def set_guide_text(self, value):
        self.guide.configure(state='normal')
        self.guide.delete('1.0', 'end')
        self.guide.insert('1.0', value)
        self.guide.configure(state='disabled')
        self.guide.yview_moveto(0)

    def refresh_guide(self):
        if self.mode == 'T9':
            self.set_guide_text((
                'T9 PREDICTIVE TEXT\n\n'
                'Press each letter key once.\n'
                'Example: HELLO = 98445\n\n'
                '+   Copy all text\n'
                '0   Accept word + space\n'
                '.   Delete last digit\n'
                '3   Punctuation\n'
                'Enter   Accept + new line\n\n'
                'ABC / abc changes letter case.'))
        else:
            self.set_guide_text(self.multitap_guide)

    def accept_t9(self, space=False):
        self.t9_digits = ''
        self.t9_start = None
        self.t9_matches = []
        self.t9_index = 0
        self.suggestion.config(text='')
        if space:
            self.editor.insert('insert', ' ')
        self.preview.config(text='READY')

    def update_t9(self):
        digits = self.t9_digits
        matches = self.t9_words.get(digits, [])
        self.t9_matches = matches
        self.t9_index %= max(len(matches), 1)
        word = (matches[self.t9_index] if matches else digits)
        word = word if self.uppercase else word.lower()
        if self.t9_start is None:
            self.t9_start = self.editor.index('insert')
        else:
            self.editor.delete(self.t9_start, 'insert')
        self.editor.insert('insert', word)
        self.suggestion.config(
            text=f'{digits} -> {word}  ({self.t9_index+1}/{len(matches)})'
            if matches else f'{digits} -> no dictionary match')
        self.preview.config(text='T9  ' + digits)

    def tap_t9(self, key):
        if key in MAP and MAP[key][0].isalpha():
            self.t9_digits += key
            self.t9_index = 0
            self.update_t9()
        elif key == '+':
            if self.t9_matches:
                self.t9_index = (self.t9_index + 1) % len(self.t9_matches)
                self.update_t9()
        elif key == '0':
            self.accept_t9(True)
        elif key == '.':
            if self.t9_digits:
                self.t9_digits = self.t9_digits[:-1]
                if self.t9_start is not None:
                    self.editor.delete(self.t9_start, 'insert')
                    self.editor.mark_set('insert', self.t9_start)
                self.t9_start = None
                if self.t9_digits:
                    self.update_t9()
                else:
                    self.accept_t9(False)
            else:
                self.editor.delete('insert-1c', 'insert')
        elif key == '3':
            self.accept_t9(False)
            self.editor.insert('insert', '.')
        elif key == 'Enter':
            self.accept_t9(False)
            self.editor.insert('insert', '\n')
        self.update_status()

    def tap(self, key):
        if key == '+':
            self.copy_all()
            return
        self.editor.focus_set()
        if self.mode == 'T9':
            self.tap_t9(key)
            return
        if key in MAP:
            if self.timer:
                self.root.after_cancel(self.timer)
                self.timer = None
            letters = MAP[key]
            if not self.uppercase:
                letters = letters.lower()
            if self.pending is not None and self.last_key == key:
                self.index = (self.index + 1) % len(letters)
                start, end = self.pending
                self.editor.delete(start, end)
                self.editor.insert(start, letters[self.index])
                self.pending = (start, self.editor.index('insert'))
            else:
                self.commit()
                self.index = 0
                start = self.editor.index('insert')
                self.editor.insert('insert', letters[0])
                self.pending = (start, self.editor.index('insert'))
                self.last_key = key
            self.preview.config(text=f'{key}  →  {letters[self.index]}    [{letters}]')
            self.timer = self.root.after(self.timeout, self.commit)
        elif key == '0':
            self.commit()
            self.editor.insert('insert', ' ')
        elif key == '.':
            self.commit()
            try:
                self.editor.delete('sel.first', 'sel.last')
            except tk.TclError:
                self.editor.delete('insert-1c', 'insert')
        elif key == '+':
            self.commit()
        elif key == 'Enter':
            self.commit()
            self.editor.insert('insert', '\n')
        self.update_status()

    def key_from_event(self, event):
        # Windows Tk uses distinct numpad keysyms when Num Lock is enabled.
        if event.keysym.startswith('KP_'):
            suffix = event.keysym[3:]
            if suffix in MAP or suffix == '0': return suffix
            return {'Decimal':'.', 'Delete':'.', 'Add':'+', 'Enter':'Enter', 'Separator':'Enter'}.get(suffix)
        # Windows reports VK_NUMPAD0..9 as virtual-key codes 96..105.
        # Some Tk builds identify these as plain digits rather than KP_ digits.
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':
            code = event.keycode
            if 96 <= code <= 105:
                return str(code - 96)
            if code == 110:
                return '.'
            if code == 107:
                return '+'
        return None

    def on_press(self, event):
        key = self.key_from_event(event)
        if key is None:
            self.finish_input()
            return
        # Ignore OS auto-repeat while key is held down.
        if key in self.pressed:
            return 'break'
        self.pressed.add(key)
        if key in self.buttons:
            self.buttons[key].config(bg=self.palette['active'], fg=self.palette['bg'])
        self.tap(key)
        self.preview.config(text=self.preview.cget('text') + f'  |  {event.keysym} / {event.keycode}')
        return 'break'

    def on_release(self, event):
        key = self.key_from_event(event)
        if key is not None:
            self.pressed.discard(key)
            if key in self.buttons:
                self.buttons[key].config(bg=self.palette['key'], fg=self.palette['fg'])
            return 'break'

    def on_modified(self, event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self.update_status()

    def update_status(self):
        chars = len(self.editor.get('1.0', 'end-1c'))
        self.status.config(text=f'{chars} characters  •  {Path(self.filepath).name if self.filepath else "Untitled"}')

    def new(self):
        self.finish_input()
        if self.editor.get('1.0','end-1c') and not messagebox.askyesno('New document', 'Clear the current notepad? Save your work first if needed.'):
            return
        self.editor.delete('1.0','end')
        self.filepath = None
        self.update_status()

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[('Text files','*.txt'),('All files','*.*')])
        if path:
            try:
                data = Path(path).read_text(encoding='utf-8-sig')
            except Exception as exc:
                messagebox.showerror('Open failed', str(exc))
                return
            self.finish_input()
            self.editor.delete('1.0','end')
            self.editor.insert('1.0',data)
            self.filepath = path
            self.update_status()

    def save(self):
        if not self.filepath:
            return self.save_as()
        try:
            Path(self.filepath).write_text(self.editor.get('1.0','end-1c'), encoding='utf-8')
        except Exception as exc:
            messagebox.showerror('Save failed', str(exc))
        self.update_status()

    def save_as(self):
        path = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text files','*.txt')])
        if path:
            self.filepath = path
            self.save()

    def copy_all(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.editor.get('1.0','end-1c'))
        self.preview.config(text='COPIED TO CLIPBOARD')



    def close(self):
        existing = getattr(self, '_exit_dialog', None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return

        t = self.palette
        dialog = tk.Toplevel(self.root)
        self._exit_dialog = dialog

        dialog.title('Exit 10Keyboard')
        dialog.configure(bg=t['bg'])
        dialog.resizable(False, False)
        dialog.transient(self.root)

        frame = tk.Frame(
            dialog, bg=t['panel'], padx=28, pady=24
        )
        frame.pack(fill='both', expand=True, padx=2, pady=2)

        tk.Label(
            frame, text='EXIT 10KEYBOARD?',
            bg=t['panel'], fg=t['active'],
            font=('Consolas', 15, 'bold')
        ).pack(anchor='w')

        tk.Label(
            frame,
            text='Close 10Keyboard? Save your work first if needed.',
            bg=t['panel'], fg=t['fg'],
            font=('Consolas', 10),
            wraplength=340, justify='left'
        ).pack(anchor='w', pady=(14, 24))

        actions = tk.Frame(frame, bg=t['panel'])
        actions.pack(fill='x')

        def cancel():
            dialog.destroy()
            self._exit_dialog = None
            self.editor.focus_set()

        def exit_app():
            self.root.destroy()

        for label, command, bg, fg in (
            ('CANCEL', cancel, t['key'], t['fg']),
            ('EXIT', exit_app, t['active'], t['bg'])
        ):
            tk.Button(
                actions, text=label, command=command,
                bg=bg, fg=fg,
                activebackground=t['active'],
                activeforeground=t['bg'],
                relief='flat', bd=0,
                padx=22, pady=10,
                font=('Consolas', 10, 'bold'),
                cursor='hand2'
            ).pack(side='right', padx=(8, 0))

        dialog.protocol('WM_DELETE_WINDOW', cancel)
        dialog.bind('<Escape>', lambda event: cancel())
        dialog.bind('<Return>', lambda event: exit_app())

        width, height = 430, 205
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width()-width)//2
        y = self.root.winfo_rooty() + (self.root.winfo_height()-height)//2
        dialog.geometry(f'{width}x{height}+{max(0,x)}+{max(0,y)}')

        # Apply DWM colors to the dialog's own native window.
        if sys.platform == 'win32':
            try:
                dialog.update_idletasks()
                user32 = ctypes.windll.user32
                user32.GetParent.argtypes = [ctypes.c_void_p]
                user32.GetParent.restype = ctypes.c_void_p
                hwnd = user32.GetParent(dialog.winfo_id())

                def colorref(value):
                    r, g, b = bytes.fromhex(value.lstrip('#'))
                    return r | (g << 8) | (b << 16)

                dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute
                dwm.argtypes = [
                    ctypes.c_void_p, ctypes.c_uint,
                    ctypes.c_void_p, ctypes.c_uint
                ]
                dwm.restype = ctypes.c_long

                for attr, color in ((35, t['bg']), (36, t['fg'])):
                    value = ctypes.c_uint32(colorref(color))
                    result = dwm(
                        hwnd, attr,
                        ctypes.byref(value), ctypes.sizeof(value)
                    )
                    if result:
                        print('[DIALOG DWM]', attr, hex(result & 0xffffffff))
            except (AttributeError, OSError, ValueError) as exc:
                print('[DIALOG DWM]', exc)

        dialog.lift()
        dialog.grab_set()
        dialog.focus_set()


if __name__ == '__main__':
    root = tk.Tk()
    KeyboardApp(root)
    root.mainloop()

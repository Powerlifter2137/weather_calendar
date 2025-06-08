from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import requests
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from tkcalendar import Calendar

DB_FILE = Path("weather_calendar.db")
OPENWEATHER_API_KEY = "20924b2526831a0f5e3779e09bddf633"


class WeatherCalendarApp:
    """Główne okno aplikacji."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Aplikacja Pogodowa z Kalendarzem (multi‑kalendarze)")
        self.root.geometry("1050x650")

        # Style
        style = ttk.Style()
        style.configure("Weather.TLabelframe", background="#e0f7fa")
        style.configure("WeatherHeader.TLabel", background="#e0f7fa", font=("Helvetica", 16, "bold"))
        style.configure("WeatherInfo.TLabel", background="#e0f7fa", font=("Helvetica", 12))

        # Stan
        self.current_user: dict | None = None
        self._cal_map: dict[str, int] = {}

        self._init_db()
        self._create_login_screen()

    def _init_db(self) -> None:
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS calendars (
                id INTEGER PRIMARY KEY,
                owner_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                visibility TEXT NOT NULL CHECK(visibility IN ('private','public')),
                FOREIGN KEY(owner_id) REFERENCES users(id)
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_shares (
                calendar_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY(calendar_id,user_id),
                FOREIGN KEY(calendar_id) REFERENCES calendars(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                calendar_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(calendar_id) REFERENCES calendars(id)
            )
            """
        )
        try:
            self.cursor.execute("ALTER TABLE events ADD COLUMN calendar_id INTEGER")
        except sqlite3.OperationalError:
            pass  # kolumna już istnieje
        self.conn.commit()

    def _create_login_screen(self) -> None:
        self._clear_root()
        frame = ttk.Frame(self.root, padding=20)
        frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ttk.Label(frame, text="Aplikacja Pogodowa z Kalendarzem", font=("Helvetica", 16)).grid(
            row=0, column=0, columnspan=2, pady=10
        )
        # login
        ttk.Label(frame, text="Nazwa użytkownika:").grid(row=1, column=0, sticky=tk.W)
        self.username_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.username_var, width=28).grid(row=1, column=1, pady=5)
        # haslo
        ttk.Label(frame, text="Hasło:").grid(row=2, column=0, sticky=tk.W)
        self.password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.password_var, show="*", width=28).grid(row=2, column=1, pady=5)

        btns = ttk.Frame(frame)
        btns.grid(row=3, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="Zaloguj", width=12, command=self._login).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Zarejestruj", width=12, command=self._register).pack(side=tk.LEFT, padx=4)

    def _register(self) -> None:
        u, p = self.username_var.get().strip(), self.password_var.get().strip()
        if not u or not p:
            messagebox.showerror("Błąd", "Wszystkie pola są wymagane!")
            return
        try:
            self.cursor.execute("INSERT INTO users(username,password) VALUES(?,?)", (u, p))
            self.conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Błąd", "Użytkownik już istnieje!")
            return
        self._login()

    def _login(self) -> None:
        u, p = self.username_var.get().strip(), self.password_var.get().strip()
        if not u or not p:
            messagebox.showerror("Błąd", "Wszystkie pola są wymagane!")
            return
        self.cursor.execute("SELECT id,username FROM users WHERE username=? AND password=?", (u, p))
        row = self.cursor.fetchone()
        if not row:
            messagebox.showerror("Błąd", "Nieprawidłowa nazwa użytkownika lub hasło!")
            return
        self.current_user = {"id": row[0], "username": row[1]}
        self._ensure_default_calendar(row[0])
        self._create_main_ui()

    def _ensure_default_calendar(self, uid: int) -> None:
        self.cursor.execute("SELECT 1 FROM calendars WHERE owner_id=?", (uid,))
        if not self.cursor.fetchone():
            self.cursor.execute(
                "INSERT INTO calendars(owner_id,name,visibility) VALUES(?,?,?)",
                (uid, "Prywatny", "private"),
            )
            self.conn.commit()

    def _accessible_calendars(self) -> list[tuple[int, str]]:
        uid = self.current_user["id"]
        self.cursor.execute(
            """
            SELECT id,name FROM calendars WHERE visibility='public' OR owner_id=?
            UNION
            SELECT c.id,c.name FROM calendars c JOIN calendar_shares s ON c.id=s.calendar_id WHERE s.user_id=?
            ORDER BY name COLLATE NOCASE
            """,
            (uid, uid),
        )
        return self.cursor.fetchall()

    def _refresh_cal_menu(self) -> None:
        cals = self._accessible_calendars()
        if not cals:
            self._cal_map = {}
            self.cal_menu["values"] = ["Brak kalendarzy"]
            self.cal_menu.current(0)
            return
        self._cal_map = {name: cid for cid, name in cals}
        self.cal_menu["values"] = list(self._cal_map.keys())
        if self.cal_menu.get() not in self._cal_map:
            self.cal_menu.current(0)

    def _create_main_ui(self) -> None:
        self._clear_root()
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # Menu górne
        top = ttk.Frame(self.root, padding=6)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(top, text=f"Zalogowano jako: {self.current_user['username']}").pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Moje kalendarze", command=self._open_cal_manager).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Wyloguj", command=self._create_login_screen).pack(side=tk.RIGHT, padx=4)

        # Pogoda
        w_frame = ttk.LabelFrame(self.root, text="Pogoda", padding=10, style="Weather.TLabelframe")
        w_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        w_frame.grid_rowconfigure(1, weight=1)

        city_fr = ttk.Frame(w_frame)
        city_fr.grid(row=0, column=0, sticky="ew")
        city_fr.columnconfigure(1, weight=1)
        ttk.Label(city_fr, text="Miasto:", style="WeatherInfo.TLabel").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.city_var = tk.StringVar(value="Warszawa")
        ttk.Entry(city_fr, textvariable=self.city_var).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(city_fr, text="Sprawdź", command=self._fetch_weather).grid(row=0, column=2, padx=2)

        self.weather_info = ttk.Frame(w_frame, style="Weather.TLabelframe")
        self.weather_info.grid(row=1, column=0, sticky="nsew", pady=6)

        # Kalendarz
        c_frame = ttk.LabelFrame(self.root, text="Kalendarz", padding=8)
        c_frame.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        c_frame.grid_rowconfigure(3, weight=1)

        # kalendarz widget
        self.calendar = Calendar(c_frame, selectmode="day", date_pattern="yyyy-mm-dd")
        self.calendar.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=4)
        self.calendar.bind("<<CalendarSelected>>", lambda _e: self._update_events())

        # dodawanie wydarzenia
        ttk.Label(c_frame, text="Wydarzenie:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.ev_var = tk.StringVar()
        ttk.Entry(c_frame, textvariable=self.ev_var).grid(row=1, column=1, sticky="ew", pady=2)
        self.cal_menu = ttk.Combobox(c_frame, state="readonly", width=18)
        self.cal_menu.grid(row=1, column=2, sticky=tk.E, padx=4)
        self.cal_menu.bind("<<ComboboxSelected>>", lambda _e: self._update_events())

        ttk.Button(c_frame, text="Dodaj", command=self._add_event).grid(row=2, column=2, sticky=tk.E, pady=2)
        self._refresh_cal_menu()

        # lista wydarzeń
        self.events_frame = ttk.LabelFrame(c_frame, text="", padding=6)
        self.events_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=6)
        self._update_events()

        self._fetch_weather()

    def _fetch_weather(self) -> None:
        city = self.city_var.get().strip()
        if not city:
            messagebox.showerror("Błąd", "Wprowadź nazwę miasta!")
            return
        for w in self.weather_info.winfo_children():
            w.destroy()
        ttk.Label(self.weather_info, text="Pobieranie danych pogodowych…", style="WeatherInfo.TLabel").pack(pady=8)
        self.root.update_idletasks()

        def worker():
            try:
                url = (
                    f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pl"
                )
                data = requests.get(url, timeout=10).json()
            except Exception as exc:
                self.root.after(0, lambda: self._show_weather_error(str(exc)))
                return
            self.root.after(0, lambda: self._render_weather(data))

        threading.Thread(target=worker, daemon=True).start()

    def _render_weather(self, data: dict) -> None:
        for w in self.weather_info.winfo_children():
            w.destroy()
        if data.get("cod") != 200:
            ttk.Label(
                self.weather_info,
                text=f"Błąd: {data.get('message','Nieznany błąd')}",
                style="WeatherInfo.TLabel",
            ).pack(pady=8)
            return
        main = data["main"]
        weather = data["weather"][0]
        wind = data["wind"]
        ttk.Label(
            self.weather_info,
            text=f"{data['name']}, {data['sys']['country']}",
            style="WeatherHeader.TLabel",
        ).pack(pady=4)
        ttk.Label(
            self.weather_info,
            text=f"Temperatura: {main['temp']}°C (odczuwalna: {main['feels_like']}°C)",
            style="WeatherInfo.TLabel",
        ).pack()
        ttk.Label(
            self.weather_info,
            text=f"Opis: {weather['description'].capitalize()}",
            style="WeatherInfo.TLabel",
        ).pack()
        ttk.Label(
            self.weather_info,
            text=f"Wilgotność: {main['humidity']}%  |  Ciśnienie: {main['pressure']} hPa",
            style="WeatherInfo.TLabel",
        ).pack()
        ttk.Label(
            self.weather_info,
            text=f"Wiatr: {wind['speed']} m/s",
            style="WeatherInfo.TLabel",
        ).pack()
        ttk.Label(
            self.weather_info,
            text=f"Ostatnia aktualizacja: {datetime.now().strftime('%H:%M:%S')}",
            style="WeatherInfo.TLabel",
        ).pack(pady=4)

    def _show_weather_error(self, msg: str) -> None:
        for w in self.weather_info.winfo_children():
            w.destroy()
        ttk.Label(self.weather_info, text=f"Błąd pobierania danych: {msg}", style="WeatherInfo.TLabel").pack(pady=8)

    def _add_event(self) -> None:
        desc = self.ev_var.get().strip()
        if not desc:
            messagebox.showerror("Błąd", "Wprowadź opis wydarzenia!")
            return
        cal_name = self.cal_menu.get()
        cal_id = self._cal_map.get(cal_name)
        if not cal_id:
            messagebox.showerror("Błąd", "Nie wybrano poprawnego kalendarza!")
            return
        date_str = self.calendar.get_date()
        self.cursor.execute(
            "INSERT INTO events(user_id,date,description,calendar_id) VALUES(?,?,?,?)",
            (self.current_user["id"], date_str, desc, cal_id),
        )
        self.conn.commit()
        self.ev_var.set("")
        self._update_events()

    def _update_events(self) -> None:
        date_str = self.calendar.get_date()
        for w in self.events_frame.winfo_children():
            w.destroy()
        self.events_frame["text"] = f"Wydarzenia: {date_str}"

        cids = [cid for cid in self._cal_map.values()]
        if not cids:
            ttk.Label(self.events_frame, text="Brak dostępnych kalendarzy.").pack()
            return
        placeholders = ",".join("?" * len(cids))
        sql = f"""
            SELECT e.id,e.description,e.user_id,u.username,c.name
            FROM events e JOIN users u ON e.user_id=u.id JOIN calendars c ON e.calendar_id=c.id
            WHERE e.date=? AND e.calendar_id IN ({placeholders})
            ORDER BY c.name COLLATE NOCASE,e.id
        """
        self.cursor.execute(sql, (date_str, *cids))
        rows = self.cursor.fetchall()
        if not rows:
            ttk.Label(self.events_frame, text="Brak wydarzeń.").pack()
            return
        for eid, desc, uid, uname, cname in rows:
            row = ttk.Frame(self.events_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=f"[{cname}] ({uname}) {desc}").pack(side=tk.LEFT, padx=4)
            if uid == self.current_user["id"]:
                ttk.Button(row, text="✎", width=3, command=lambda e=eid, d=desc: self._edit_event(e, d)).pack(side=tk.RIGHT)
                ttk.Button(row, text="🗑", width=3, command=lambda e=eid: self._delete_event(e)).pack(side=tk.RIGHT, padx=2)

    def _edit_event(self, eid: int, old: str) -> None:
        new_desc = simpledialog.askstring("Edycja wydarzenia", "Nowy opis:", initialvalue=old, parent=self.root)
        if new_desc:
            self.cursor.execute("UPDATE events SET description=? WHERE id=?", (new_desc.strip(), eid))
            self.conn.commit()
            self._update_events()

    def _delete_event(self, eid: int) -> None:
        if messagebox.askyesno("Usuń wydarzenie", "Czy na pewno chcesz usunąć to wydarzenie?", parent=self.root):
            self.cursor.execute("DELETE FROM events WHERE id=?", (eid,))
            self.conn.commit()
            self._update_events()


    def _open_cal_manager(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Moje kalendarze")
        win.geometry("420x460")
        win.transient(self.root)
        win.grab_set()

        ttk.Label(win, text="Twoje kalendarze", font=("Helvetica", 14, "bold"), padding=6).pack()

        list_frame = ttk.Frame(win)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8)
        canvas = tk.Canvas(list_frame)
        scr = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scr.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_list():
            for w in inner.winfo_children():
                w.destroy()
            self.cursor.execute(
                "SELECT id,name,visibility FROM calendars WHERE owner_id=? ORDER BY name COLLATE NOCASE",
                (self.current_user["id"],),
            )
            rows = self.cursor.fetchall()
            if not rows:
                ttk.Label(inner, text="(brak kalendarzy)").pack()
            for cid, name, vis in rows:
                row = ttk.Frame(inner, padding=2)
                row.pack(fill=tk.X)
                ttk.Label(row, text=name).pack(side=tk.LEFT, padx=2)
                ttk.Label(row, text="[publiczny]" if vis == "public" else "[prywatny]").pack(side=tk.LEFT)
                ttk.Button(row, text="Widoczność", width=10, command=lambda c=cid, v=vis: toggle_vis(c, v)).pack(side=tk.RIGHT, padx=2)
                ttk.Button(row, text="Udostępnij", width=10, command=lambda c=cid: share(c)).pack(side=tk.RIGHT, padx=2)
                ttk.Button(row, text="Usuń", width=6, command=lambda c=cid: delete_cal(c)).pack(side=tk.RIGHT, padx=2)

        def toggle_vis(cid: int, current: str):
            new = "private" if current == "public" else "public"
            self.cursor.execute("UPDATE calendars SET visibility=? WHERE id=?", (new, cid))
            self.conn.commit()
            refresh_list()
            self._refresh_cal_menu()
            self._update_events()

        def delete_cal(cid: int):
            if messagebox.askyesno("Usuń kalendarz", "Usunąć kalendarz wraz z wydarzeniami?", parent=win):
                self.cursor.execute("DELETE FROM events WHERE calendar_id=?", (cid,))
                self.cursor.execute("DELETE FROM calendar_shares WHERE calendar_id=?", (cid,))
                self.cursor.execute("DELETE FROM calendars WHERE id=?", (cid,))
                self.conn.commit()
                refresh_list()
                self._refresh_cal_menu()
                self._update_events()

        def share(cid: int):
            target = simpledialog.askstring("Udostępnij", "Nazwa użytkownika do udostępnienia:", parent=win)
            if not target:
                return
            self.cursor.execute("SELECT id FROM users WHERE username=?", (target,))
            row = self.cursor.fetchone()
            if not row:
                messagebox.showerror("Błąd", "Taki użytkownik nie istnieje!", parent=win)
                return
            try:
                self.cursor.execute("INSERT INTO calendar_shares(calendar_id,user_id) VALUES(?,?)", (cid, row[0]))
                self.conn.commit()
                messagebox.showinfo("Sukces", "Kalendarz udostępniono.", parent=win)
            except sqlite3.IntegrityError:
                messagebox.showinfo("Info", "Już udostępniony temu użytkownikowi.", parent=win)

        refresh_list()

        # nowy kalendarz
        new_fr = ttk.LabelFrame(win, text="Nowy kalendarz", padding=6)
        new_fr.pack(fill=tk.X, padx=8, pady=4)
        name_var = tk.StringVar()
        ttk.Entry(new_fr, textvariable=name_var, width=20).grid(row=0, column=0, padx=4)
        v_var = tk.StringVar(value="private")
        ttk.Radiobutton(new_fr, text="Prywatny", variable=v_var, value="private").grid(row=0, column=1)
        ttk.Radiobutton(new_fr, text="Publiczny", variable=v_var, value="public").grid(row=0, column=2)
        ttk.Button(new_fr, text="Utwórz", command=lambda: create_cal()).grid(row=0, column=3, padx=4)

        def create_cal():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Błąd", "Podaj nazwę!", parent=win)
                return
            self.cursor.execute(
                "INSERT INTO calendars(owner_id,name,visibility) VALUES(?,?,?)",
                (self.current_user["id"], name, v_var.get()),
            )
            self.conn.commit()
            name_var.set("")
            refresh_list()
            self._refresh_cal_menu()

        win.protocol("WM_DELETE_WINDOW", lambda: (win.destroy(), self._refresh_cal_menu(), self._update_events()))

    def _clear_root(self) -> None:
        for w in self.root.winfo_children():
            w.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherCalendarApp(root)
    root.mainloop()

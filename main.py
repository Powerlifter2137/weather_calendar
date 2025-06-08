import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import requests
import json
from datetime import datetime
from tkcalendar import Calendar
import threading

class WeatherCalendarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Aplikacja Pogodowa z Kalendarzem")
        self.root.geometry("1000x600")

        # Stylizacja sekcji pogody
        self.style = ttk.Style()
        self.style.configure('Weather.TLabelframe', background='#e0f7fa')
        self.style.configure('WeatherHeader.TLabel', background='#e0f7fa', font=('Helvetica', 16, 'bold'))
        self.style.configure('WeatherInfo.TLabel', background='#e0f7fa', font=('Helvetica', 12))

        self.init_database()
        self.current_user = None
        self.create_login_screen()

    def init_database(self):
        self.conn = sqlite3.connect('weather_calendar.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        self.conn.commit()

    def create_login_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        login_frame = ttk.Frame(self.root, padding=20)
        login_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        ttk.Label(login_frame, text="Aplikacja Pogodowa z Kalendarzem", font=("Helvetica", 16)).grid(row=0, column=0, columnspan=2, pady=10)
        ttk.Label(login_frame, text="Nazwa użytkownika:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.username_var, width=30).grid(row=1, column=1, pady=5)
        ttk.Label(login_frame, text="Hasło:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.password_var, show="*", width=30).grid(row=2, column=1, pady=5)
        button_frame = ttk.Frame(login_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Zaloguj", command=self.login).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Zarejestruj", command=self.register).pack(side=tk.LEFT, padx=5)

    def register(self):
        username = self.username_var.get()
        password = self.password_var.get()
        if not username or not password:
            messagebox.showerror("Błąd", "Wszystkie pola są wymagane!")
            return
        try:
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            messagebox.showinfo("Sukces", "Konto zostało utworzone!")
            self.login()
        except sqlite3.IntegrityError:
            messagebox.showerror("Błąd", "Użytkownik już istnieje!")

    def login(self):
        username = self.username_var.get()
        password = self.password_var.get()
        if not username or not password:
            messagebox.showerror("Błąd", "Wszystkie pola są wymagane!")
            return
        self.cursor.execute("SELECT id, username FROM users WHERE username=? AND password=?", (username, password))
        user = self.cursor.fetchone()
        if user:
            self.current_user = {"id": user[0], "username": user[1]}
            self.create_main_app()
        else:
            messagebox.showerror("Błąd", "Nieprawidłowa nazwa użytkownika lub hasło!")

    def create_main_app(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        menu_frame = ttk.Frame(self.root, padding=5)
        menu_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(menu_frame, text=f"Zalogowano jako: {self.current_user['username']}").pack(side=tk.LEFT, padx=5)
        ttk.Button(menu_frame, text="Wyloguj", command=self.create_login_screen).pack(side=tk.RIGHT, padx=5)
        # Pogoda
        weather_frame = ttk.LabelFrame(self.root, text="Pogoda", padding=10, style='Weather.TLabelframe')
        weather_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        city_frame = ttk.Frame(weather_frame)
        city_frame.pack(fill=tk.X, pady=5)
        ttk.Label(city_frame, text="Miasto:", style='WeatherInfo.TLabel').pack(side=tk.LEFT, padx=5)
        self.city_var = tk.StringVar(value="Warszawa")
        ttk.Entry(city_frame, textvariable=self.city_var).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(city_frame, text="Sprawdź", command=self.fetch_weather).pack(side=tk.LEFT, padx=5)
        self.weather_info_frame = ttk.Frame(weather_frame)
        self.weather_info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        # Kalendarz i wydarzenia
        calendar_frame = ttk.LabelFrame(self.root, text="Kalendarz", padding=10)
        calendar_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.cal = Calendar(calendar_frame, selectmode='day', date_pattern='yyyy-mm-dd')
        self.cal.pack(fill=tk.BOTH, expand=True, pady=5)
        # Dodawanie wydarzenia
        add_frame = ttk.Frame(calendar_frame)
        add_frame.pack(fill=tk.X, pady=5)
        ttk.Label(add_frame, text="Wydarzenie:").pack(side=tk.LEFT, padx=5)
        self.event_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.event_var).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(add_frame, text="Dodaj wydarzenie", command=self.add_event).pack(side=tk.LEFT, padx=5)
        # Dzisiejsze wydarzenia
        self.today_events_frame = ttk.LabelFrame(calendar_frame, text="Dzisiejsze wydarzenia", padding=10)
        self.today_events_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.update_today_events()
        self.fetch_weather()

    def update_today_events(self):
        today = datetime.now().strftime('%Y-%m-%d')
        for widget in self.today_events_frame.winfo_children():
            widget.destroy()
        self.cursor.execute("""
            SELECT events.id, events.description, events.user_id, users.username
            FROM events
            JOIN users ON events.user_id = users.id
            WHERE date=?
        """, (today,))
        events = self.cursor.fetchall()
        if not events:
            ttk.Label(self.today_events_frame, text="Brak wydarzeń na dziś.").pack()
            return
        for idx, (event_id, desc, user_id, username) in enumerate(events, start=1):
            frame = ttk.Frame(self.today_events_frame)
            frame.pack(fill=tk.X, pady=2)
            label = ttk.Label(frame, text=f"({username}) {idx}. {desc}")
            label.pack(side=tk.LEFT, padx=5)
            if user_id == self.current_user['id']:
                def edit_event(eid=event_id, old_desc=desc):
                    new_desc = simpledialog.askstring("Edycja wydarzenia", "Nowy opis:", initialvalue=old_desc)
                    if new_desc:
                        self.cursor.execute("UPDATE events SET description=? WHERE id=?", (new_desc, eid))
                        self.conn.commit()
                        self.update_today_events()
                def delete_event(eid=event_id):
                    if messagebox.askyesno("Usuń wydarzenie", "Czy na pewno chcesz usunąć to wydarzenie?" ):
                        self.cursor.execute("DELETE FROM events WHERE id=?", (eid,))
                        self.conn.commit()
                        self.update_today_events()
                ttk.Button(frame, text="Edytuj", command=edit_event).pack(side=tk.RIGHT, padx=2)
                ttk.Button(frame, text="Usuń", command=delete_event).pack(side=tk.RIGHT, padx=2)

    def fetch_weather(self):
        city = self.city_var.get()
        if not city:
            messagebox.showerror("Błąd", "Wprowadź nazwę miasta!")
            return
        for widget in self.weather_info_frame.winfo_children():
            widget.destroy()
        ttk.Label(self.weather_info_frame, text="Pobieranie danych pogodowych...", style='WeatherInfo.TLabel').pack(pady=10)
        self.root.update()
        def get_weather():
            try:
                api_key = "20924b2526831a0f5e3779e09bddf633"
                url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=pl"
                response = requests.get(url)
                weather_data = json.loads(response.text)
                self.root.after(0, lambda: self.update_weather_ui(weather_data))
            except Exception as e:
                self.root.after(0, lambda: self.show_weather_error(str(e)))
        threading.Thread(target=get_weather, daemon=True).start()

    def update_weather_ui(self, data):
        for widget in self.weather_info_frame.winfo_children():
            widget.destroy()
        if data.get("cod") != 200:
            ttk.Label(self.weather_info_frame, text=f"Błąd: {data.get('message', 'Nieznany błąd')}", style='WeatherInfo.TLabel').pack(pady=10)
            return
        city_name = data["name"]
        country = data["sys"]["country"]
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        description = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        pressure = data["main"]["pressure"]
        wind_speed = data["wind"]["speed"]
        ttk.Label(self.weather_info_frame, text=f"{city_name}, {country}", style='WeatherHeader.TLabel').pack(pady=5)
        ttk.Label(self.weather_info_frame, text=f"Temperatura: {temp}°C (odczuwalna: {feels_like}°C)", style='WeatherInfo.TLabel').pack(pady=2)
        ttk.Label(self.weather_info_frame, text=f"Opis: {description.capitalize()}", style='WeatherInfo.TLabel').pack(pady=2)
        ttk.Label(self.weather_info_frame, text=f"Wilgotność: {humidity}%", style='WeatherInfo.TLabel').pack(pady=2)
        ttk.Label(self.weather_info_frame, text=f"Ciśnienie: {pressure} hPa", style='WeatherInfo.TLabel').pack(pady=2)
        ttk.Label(self.weather_info_frame, text=f"Prędkość wiatru: {wind_speed} m/s", style='WeatherInfo.TLabel').pack(pady=2)
        update_time = datetime.now().strftime('%H:%M:%S')
        ttk.Label(self.weather_info_frame, text=f"Ostatnia aktualizacja: {update_time}", style='WeatherInfo.TLabel').pack(pady=10)

    def show_weather_error(self, error_message):
        for widget in self.weather_info_frame.winfo_children():
            widget.destroy()
        ttk.Label(self.weather_info_frame, text=f"Błąd pobierania danych: {error_message}", style='WeatherInfo.TLabel').pack(pady=10)

    def add_event(self):
        selected_date = self.cal.get_date()
        event_description = self.event_var.get()
        if not event_description:
            messagebox.showerror("Błąd", "Wprowadź opis wydarzenia!")
            return
        try:
            self.cursor.execute("INSERT INTO events (user_id, date, description) VALUES (?, ?, ?)",
                                (self.current_user['id'], selected_date, event_description))
            self.conn.commit()
            messagebox.showinfo("Sukces", "Wydarzenie zostało dodane!")
            self.event_var.set("")
            self.update_today_events()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się dodać wydarzenia: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherCalendarApp(root)
    root.mainloop()

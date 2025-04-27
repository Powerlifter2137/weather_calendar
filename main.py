import tkinter as tk
from tkinter import ttk, messagebox
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
        
        # Inicjalizacja bazy danych
        self.init_database()
        
        # Dane użytkownika
        self.current_user = None
        
        # Utworzenie ekranu logowania
        self.create_login_screen()
        
    def init_database(self):
        # Połączenie z bazą danych
        self.conn = sqlite3.connect('weather_calendar.db')
        self.cursor = self.conn.cursor()
        
        # Utworzenie tabeli użytkowników
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        ''')
        
        # Utworzenie tabeli wydarzeń
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
        # Czyszczenie okna
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Ramka logowania
        login_frame = ttk.Frame(self.root, padding=20)
        login_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Etykiety i pola
        ttk.Label(login_frame, text="Aplikacja Pogodowa z Kalendarzem", font=("Helvetica", 16)).grid(row=0, column=0, columnspan=2, pady=10)
        
        ttk.Label(login_frame, text="Nazwa użytkownika:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.username_var, width=30).grid(row=1, column=1, pady=5)
        
        ttk.Label(login_frame, text="Hasło:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.password_var, show="*", width=30).grid(row=2, column=1, pady=5)
        
        # Przyciski
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
        # Czyszczenie okna
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Konfiguracja głównego układu
        self.root.grid_columnconfigure(0, weight=1)  # Pogoda
        self.root.grid_columnconfigure(1, weight=1)  # Kalendarz
        self.root.grid_rowconfigure(0, weight=0)     # Pasek menu
        self.root.grid_rowconfigure(1, weight=1)     # Główna zawartość
        
        # Pasek menu
        menu_frame = ttk.Frame(self.root, padding=5)
        menu_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        ttk.Label(menu_frame, text=f"Zalogowano jako: {self.current_user['username']}").pack(side=tk.LEFT, padx=5)
        ttk.Button(menu_frame, text="Wyloguj", command=self.create_login_screen).pack(side=tk.RIGHT, padx=5)
        
        # Panel pogody
        weather_frame = ttk.LabelFrame(self.root, text="Pogoda", padding=10)
        weather_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Pole wyboru miasta
        city_frame = ttk.Frame(weather_frame)
        city_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(city_frame, text="Miasto:").pack(side=tk.LEFT, padx=5)
        self.city_var = tk.StringVar(value="Warszawa")
        city_entry = ttk.Entry(city_frame, textvariable=self.city_var)
        city_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(city_frame, text="Sprawdź", command=self.fetch_weather).pack(side=tk.LEFT, padx=5)
        
        # Dane pogodowe
        self.weather_info_frame = ttk.Frame(weather_frame)
        self.weather_info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Panel kalendarza
        calendar_frame = ttk.LabelFrame(self.root, text="Kalendarz", padding=10)
        calendar_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        
        # Kalendarz
        self.cal = Calendar(calendar_frame, selectmode='day', date_pattern='yyyy-mm-dd')
        self.cal.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Panel wydarzeń
        event_frame = ttk.Frame(calendar_frame)
        event_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(event_frame, text="Wydarzenie:").pack(side=tk.LEFT, padx=5)
        self.event_var = tk.StringVar()
        event_entry = ttk.Entry(event_frame, textvariable=self.event_var)
        event_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        button_frame = ttk.Frame(calendar_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Dodaj wydarzenie", command=self.add_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Pokaż wydarzenia", command=self.show_events).pack(side=tk.LEFT, padx=5)
        
        # Automatyczne pobranie pogody dla domyślnego miasta
        self.fetch_weather()
    
    def fetch_weather(self):
        city = self.city_var.get()
        if not city:
            messagebox.showerror("Błąd", "Wprowadź nazwę miasta!")
            return
        
        # Czyszczenie ramki informacji o pogodzie
        for widget in self.weather_info_frame.winfo_children():
            widget.destroy()
        
        # Wskaźnik ładowania
        ttk.Label(self.weather_info_frame, text="Pobieranie danych pogodowych...").pack(pady=10)
        self.root.update()
        
        # Funkcja pobierania pogody w osobnym wątku
        def get_weather():
            try:
                # API key z OpenWeatherMap (musisz się zarejestrować, aby go uzyskać)
                api_key = "YOUR_API_KEY"  # Zamień na swój API key
                url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=pl"
                
                response = requests.get(url)
                weather_data = json.loads(response.text)
                
                # Aktualizacja UI w głównym wątku
                self.root.after(0, lambda: self.update_weather_ui(weather_data))
                
            except Exception as e:
                # Aktualizacja UI w przypadku błędu
                self.root.after(0, lambda: self.show_weather_error(str(e)))
        
        # Uruchomienie wątku
        threading.Thread(target=get_weather, daemon=True).start()
    
    def update_weather_ui(self, data):
        # Czyszczenie ramki informacji o pogodzie
        for widget in self.weather_info_frame.winfo_children():
            widget.destroy()
            
        if data.get("cod") != 200:
            error_msg = data.get("message", "Nieznany błąd")
            ttk.Label(self.weather_info_frame, text=f"Błąd: {error_msg}").pack(pady=10)
            return
            
        # Wyświetlanie danych pogodowych
        city_name = data["name"]
        country = data["sys"]["country"]
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        description = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        pressure = data["main"]["pressure"]
        wind_speed = data["wind"]["speed"]
        
        # Nagłówek
        ttk.Label(self.weather_info_frame, text=f"{city_name}, {country}", font=("Helvetica", 16, "bold")).pack(pady=5)
        
        # Temperatura i opis
        ttk.Label(self.weather_info_frame, text=f"Temperatura: {temp}°C (odczuwalna: {feels_like}°C)").pack(pady=2)
        ttk.Label(self.weather_info_frame, text=f"Opis: {description.capitalize()}").pack(pady=2)
        
        # Dodatkowe informacje
        ttk.Label(self.weather_info_frame, text=f"Wilgotność: {humidity}%").pack(pady=2)
        ttk.Label(self.weather_info_frame, text=f"Ciśnienie: {pressure} hPa").pack(pady=2)
        ttk.Label(self.weather_info_frame, text=f"Prędkość wiatru: {wind_speed} m/s").pack(pady=2)
        
        # Czas aktualizacji
        update_time = datetime.now().strftime("%H:%M:%S")
        ttk.Label(self.weather_info_frame, text=f"Ostatnia aktualizacja: {update_time}").pack(pady=10)
    
    def show_weather_error(self, error_message):
        # Czyszczenie ramki informacji o pogodzie
        for widget in self.weather_info_frame.winfo_children():
            widget.destroy()
            
        ttk.Label(self.weather_info_frame, text=f"Błąd pobierania danych: {error_message}").pack(pady=10)
    
    def add_event(self):
        selected_date = self.cal.get_date()
        event_description = self.event_var.get()
        
        if not event_description:
            messagebox.showerror("Błąd", "Wprowadź opis wydarzenia!")
            return
        
        try:
            self.cursor.execute("INSERT INTO events (user_id, date, description) VALUES (?, ?, ?)", 
                            (self.current_user["id"], selected_date, event_description))
            self.conn.commit()
            messagebox.showinfo("Sukces", "Wydarzenie zostało dodane!")
            self.event_var.set("")  # Czyszczenie pola
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się dodać wydarzenia: {str(e)}")
    
    def show_events(self):
        selected_date = self.cal.get_date()
        
        try:
            self.cursor.execute("SELECT description FROM events WHERE user_id=? AND date=?", 
                            (self.current_user["id"], selected_date))
            events = self.cursor.fetchall()
            
            if not events:
                messagebox.showinfo("Wydarzenia", f"Brak wydarzeń na {selected_date}")
                return
            
            # Tworzenie okna z listą wydarzeń
            events_window = tk.Toplevel(self.root)
            events_window.title(f"Wydarzenia na {selected_date}")
            events_window.geometry("400x300")
            
            # Lista wydarzeń
            ttk.Label(events_window, text=f"Wydarzenia na {selected_date}:", font=("Helvetica", 12, "bold")).pack(pady=10)
            
            events_frame = ttk.Frame(events_window, padding=10)
            events_frame.pack(fill=tk.BOTH, expand=True)
            
            for i, event in enumerate(events, 1):
                event_frame = ttk.Frame(events_frame)
                event_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(event_frame, text=f"{i}. {event[0]}").pack(side=tk.LEFT)
                
            ttk.Button(events_window, text="Zamknij", command=events_window.destroy).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się pobrać wydarzeń: {str(e)}")

# Uruchomienie aplikacji
if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherCalendarApp(root)
    root.mainloop()

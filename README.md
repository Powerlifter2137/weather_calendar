# Aplikacja Pogodowa z Kalendarzem

**Aplikacja desktopowa** napisana w Pythonie przy użyciu bibliotek **Tkinter** oraz **tkcalendar**, służąca do:

- **Wyświetlania prognozy pogody** dla dowolnego miasta (API OpenWeatherMap).  
- **Zarządzania wydarzeniami** w kalendarzu: dodawanie, edycja, usuwanie wpisów.  
- Pokazywania listy **dzisiejszych wydarzeń** wraz z informacją o autorze.

---

## Funkcjonalności

1. **Logowanie i rejestracja** użytkowników  
   - Dane przechowywane w lokalnej bazie SQLite (`weather_calendar.db`).

2. **Sekcja Pogody**  
   - Wprowadź nazwę miasta i pobierz bieżące warunki pogodowe (temperatura, wilgotność, wiatr itp.).

3. **Kalendarz**  
   - Wybór daty za pomocą widgetu `Calendar`.  
   - Dodawanie wydarzeń na dowolny dzień.  
   - Wyświetlanie wszystkich wydarzeń zaplanowanych na **dzisiaj** w formacie:  
     ```text
     (nazwa_użytkownika) 1. Opis wydarzenia
     (inny_user)         2. Kolejne wydarzenie
     ```

4. **Edycja i usuwanie**  
   - Możliwość edycji i usunięcia tylko **własnych** wydarzeń po potwierdzeniu.

---

## Instalacja i uruchomienie

1. Zainstaluj wymagane biblioteki:
   ```bash
   pip install tkcalendar requests
2. W foderze projektu wykonaj plik startowy poleceniem python main.py
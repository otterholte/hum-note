"""Humnote (Hum to MIDI) — opens the app as its own Windows program.

Starts the local helper (saving + low-delay 'hear myself'), then opens the page in a Chrome app window
(no tabs or address bar) with its own profile, so it keeps its own mic permission and window size.
When the window closes, the helper stops too.
"""
import os, subprocess, sys, threading, time, urllib.request, winreg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import server  # noqa: E402
import taskbar_id  # noqa: E402

URL = f"http://127.0.0.1:{server.PORT}/"
PROFILE = os.path.join(os.environ.get("LOCALAPPDATA", HERE), "HumToMidi", "app-profile")


def find_chrome():
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as k:
                p = winreg.QueryValue(k, None)
                if p and os.path.exists(p):
                    return p
        except OSError:
            pass
    for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")):
        p = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
        if os.path.exists(p):
            return p
    return None


def main():
    srv = server.make_server()
    if srv:
        server.LIVE.warm()  # the audio engine gets its own process, started now so Listen is instant
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    for _ in range(50):  # wait until the helper answers
        try:
            urllib.request.urlopen(URL + "api/ping", timeout=0.3); break
        except Exception:
            time.sleep(0.1)
    chrome = find_chrome()
    if not chrome:
        os.startfile(URL); return
    os.makedirs(PROFILE, exist_ok=True)
    p = subprocess.Popen([chrome, f"--app={URL}", f"--user-data-dir={PROFILE}", "--window-size=1280,900",
                          "--no-first-run", "--no-default-browser-check", "--disable-features=Translate"])
    # own taskbar identity (icon + pinning) instead of being grouped with Chrome
    relaunch = f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{os.path.abspath(__file__)}"'
    threading.Thread(target=taskbar_id.keep_tagged, args=(relaunch, os.path.join(HERE, "icon.ico"), lambda: p.poll() is None), daemon=True).start()
    p.wait()
    if srv:
        server.MON.stop()
        server.LIVE.close()
        srv.shutdown()


if __name__ == "__main__":
    main()

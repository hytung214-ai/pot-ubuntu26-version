#!/usr/bin/python3
"""Drive the real release app with WebKitWebDriver in an isolated X11 session.

Run with scripts/local-env.sh sourced. Requires Ubuntu's webkitgtk-webdriver,
Xvfb, Python gi/dbus/Pillow (locally extracted executables may be used).
"""
import argparse
import base64
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Driver:
    def __init__(self, base, timeout=90):
        self.base = base
        self.session = None
        self.timeout = timeout

    def request(self, method, path, data=None):
        req = urllib.request.Request(self.base + path,
                                     data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Content-Type": "application/json"}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                value = json.load(response)["value"]
        except urllib.error.HTTPError as error:
            raise RuntimeError(error.read().decode()) from error
        if isinstance(value, dict) and "error" in value and "message" in value:
            raise RuntimeError(value)
        return value

    def cmd(self, method, path, data=None):
        return self.request(method, f"/session/{self.session}" + path, data)

    def js(self, code):
        return self.cmd("POST", "/execute/sync", {"script": code, "args": []})

    def async_js(self, code):
        script = "const done=arguments[arguments.length-1];(async()=>{" + code + "})().then(value=>done({ok:true,value}),error=>done({ok:false,error:String(error)}));"
        return self.cmd("POST", "/execute/async", {"script": script, "args": []})


INVOKE = """
window.potInvoke=(cmd,args={})=>new Promise((resolve,reject)=>{
 const ids=crypto.getRandomValues(new Uint32Array(2));
 window['_'+ids[0]]=value=>{delete window['_'+ids[0]];delete window['_'+ids[1]];resolve(value)};
 window['_'+ids[1]]=error=>{delete window['_'+ids[0]];delete window['_'+ids[1]];reject(error)};
 window.__TAURI_IPC__({cmd,callback:ids[0],error:ids[1],...args});
});
"""

# This policy belongs only to the disposable test bus. Kernel AppArmor queries
# require writes to /sys/kernel/security, which the outer Codex sandbox denies.
TEST_BUS_CONFIG = """<busconfig>
  <type>session</type><listen>unix:tmpdir=/tmp</listen><auth>EXTERNAL</auth>
  <apparmor mode="disabled"/>
  <policy context="default">
    <allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/>
  </policy>
</busconfig>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, default=ROOT / "src-tauri/target/release/pot")
    parser.add_argument("--driver", type=Path, default=ROOT / "work/webdriver/usr/bin/WebKitWebDriver")
    parser.add_argument("--xvfb", type=Path, default=ROOT / "work/gui/usr/bin/Xvfb")
    args = parser.parse_args()
    directory = ROOT / "work/runtime-test"
    directory.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(TAURI_AUTOMATION="true", GDK_BACKEND="x11", XDG_SESSION_TYPE="x11")
    env["GSETTINGS_BACKEND"] = "memory"
    env["GIO_USE_VFS"] = "local"
    env["NO_AT_BRIDGE"] = "1"
    runtime = directory / "run"
    runtime.mkdir(mode=0o700, exist_ok=True)
    env["XDG_RUNTIME_DIR"] = str(runtime)
    env.pop("WAYLAND_DISPLAY", None)
    env["LD_LIBRARY_PATH"] = str(ROOT / "work/gui/usr/lib/x86_64-linux-gnu") + ":" + env.get("LD_LIBRARY_PATH", "")
    for variable, subdir in [("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache"), ("XDG_DATA_HOME", "data")]:
        folder = directory / subdir
        folder.mkdir(exist_ok=True)
        env[variable] = str(folder)
    # Launch config explicitly; the preseed prevents updater requests and isolates
    # the HTTP port without touching an existing user's Pot settings.
    app_port = port()
    config = Path(env["XDG_CONFIG_HOME"]) / "com.pot-app.desktop/config.json"
    config.parent.mkdir(exist_ok=True)
    config.write_text(json.dumps({"check_update": False, "server_port": app_port}))
    children = []
    reports = {}
    driver = None
    logs = []
    try:
        bus_config = directory / "private-bus.conf"
        bus_config.write_text(TEST_BUS_CONFIG)
        dbus = subprocess.Popen(["/usr/bin/dbus-daemon", "--config-file=" + str(bus_config), "--nofork", "--print-address=1"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        children.append(dbus)
        env["DBUS_SESSION_BUS_ADDRESS"] = dbus.stdout.readline().strip()
        display_num = next(i for i in range(91, 120) if not Path(f"/tmp/.X11-unix/X{i}").exists())
        env["DISPLAY"] = f":{display_num}"
        log = open(directory / "xvfb.log", "w"); logs.append(log)
        xvfb = subprocess.Popen([str(args.xvfb), env["DISPLAY"], "-screen", "0", "1280x900x24", "-nolisten", "tcp", "-extension", "GLX"],
                                env=env, stdout=log, stderr=subprocess.STDOUT)
        children.append(xvfb)
        for _ in range(50):
            if Path(f"/tmp/.X11-unix/X{display_num}").exists(): break
            if xvfb.poll() is not None: raise RuntimeError("Xvfb failed: " + (directory / "xvfb.log").read_text())
            time.sleep(.1)
        watcher = ROOT / "scripts/tray-test-watcher.py"
        if watcher.exists():
            log = open(directory / "tray-watcher.log", "w"); logs.append(log)
            children.append(subprocess.Popen(["/usr/bin/python3", str(watcher)], env=env, stdout=log, stderr=subprocess.STDOUT))
        driver_port = port()
        log = open(directory / "webdriver.log", "w"); logs.append(log)
        process = subprocess.Popen([str(args.driver), f"--port={driver_port}"], env=env, stdout=log, stderr=subprocess.STDOUT)
        children.append(process)
        driver = Driver(f"http://127.0.0.1:{driver_port}")
        for _ in range(50):
            try: driver.request("GET", "/status"); break
            except (OSError, RuntimeError): time.sleep(.1)

        def show_config():
            for _ in range(300):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{app_port}/config", timeout=1).close()
                    return
                except OSError: time.sleep(.1)
        threading.Thread(target=show_config, daemon=True).start()
        session = driver.request("POST", "/session", {"capabilities": {"alwaysMatch": {
            "webkitgtk:browserOptions": {"binary": str(args.binary.resolve())}}}})
        driver.session = session["sessionId"]
        driver.cmd("POST", "/timeouts", {"script": 60000})
        config_handle = None
        for _ in range(100):
            handles = driver.cmd("GET", "/window/handles")
            for handle in handles:
                driver.cmd("POST", "/window", {"handle": handle})
                if driver.js("return window.__TAURI_METADATA__?.__currentWindow?.label") == "config":
                    config_handle = handle
                    break
            if config_handle: break
            time.sleep(.1)
        if not config_handle:
            raise RuntimeError("Config window did not appear")
        for _ in range(100):
            text = driver.js("return document.body.innerText")
            if len(text) > 30: break
            time.sleep(.1)
        reports["ui"] = {"title": driver.cmd("GET", "/title"), "text": text[:1500]}
        print("UI:", reports["ui"], flush=True)
        driver.js(INVOKE + "return true")
        reports["ipc"] = driver.async_js("return await potInvoke('font_list');")
        if reports["ipc"].get("ok"):
            reports["ipc"]["font_count"] = len(reports["ipc"].pop("value"))
        print("IPC:", reports["ipc"], flush=True)
        reports["clipboard"] = driver.async_js("""
          await potInvoke('tauri',{__tauriModule:'Clipboard',message:{cmd:'writeText',data:'Pot Ubuntu 26.04 剪贴板测试'}});
          return await potInvoke('tauri',{__tauriModule:'Clipboard',message:{cmd:'readText',data:null}});
        """)
        print("Clipboard:", reports["clipboard"], flush=True)
        # Execute Pot's unchanged Bing implementation, backed by real Tauri HTTP.
        source = (ROOT / "src/services/translate/bing/index.jsx").read_text()
        source = source[source.index("export async function translate"):source.index("export * from")]
        source = source.replace("export async function", "async function", 1)
        http = """
          const client=await potInvoke('tauri',{__tauriModule:'Http',message:{cmd:'createClient',options:{}}});
          const fetch=async(url,options)=>{
            const json=!options.responseType||options.responseType===1;
            const response=await potInvoke('tauri',{__tauriModule:'Http',message:{cmd:'httpRequest',client,
              options:{...options,url,timeout:30,responseType:json?2:options.responseType}}});
            window.potLastHTTP={url,status:response.status};
            response.ok=response.status>=200&&response.status<300;
            if(json&&typeof response.data==='string'){
              try{response.data=JSON.parse(response.data)}catch(error){if(response.ok)throw error}
            }
            return response;
          };
        """
        reports["translation_bing"] = driver.async_js(http + source + "return await translate('Hello world','en','zh-Hans');")
        reports["translation_bing"]["last_http"] = driver.js("return window.potLastHTTP")
        print("Translation:", reports["translation_bing"], flush=True)
        source = (ROOT / "src/services/translate/google/index.jsx").read_text()
        source = source[source.index("export async function translate"):source.index("export * from")]
        source = source.replace("export async function", "async function", 1)
        reports["translation_google"] = driver.async_js(http + source + "return await translate('Hello world','en','zh-CN',{config:{}});")
        reports["translation_google"]["last_http"] = driver.js("return window.potLastHTTP")
        print("Google translation:", reports["translation_google"], flush=True)
        source = (ROOT / "src/services/translate/deepl/index.jsx").read_text()
        source = source[source.index("export async function translate"):source.index("export * from")]
        source = source.replace("export async function", "async function", 1)
        body = "const Body={text:payload=>({type:'Text',payload}),json:payload=>({type:'Json',payload})};"
        reports["translation_deepl"] = driver.async_js(http + body + source + "return await translate('Hello world','en','zh',{config:{type:'free'}});")
        reports["translation_deepl"]["last_http"] = driver.js("return window.potLastHTTP")
        print("DeepL translation:", reports["translation_deepl"], flush=True)
        reports["screenshot"] = driver.async_js("return await potInvoke('screenshot',{x:0,y:0});")
        image_dir = Path(env["XDG_CACHE_HOME"]) / "com.pot-app.desktop"
        image_dir.mkdir(parents=True, exist_ok=True)
        from PIL import Image, ImageDraw, ImageFont
        screenshot_file = image_dir / "pot_screenshot.png"
        if screenshot_file.exists():
            with Image.open(screenshot_file) as captured:
                reports["screenshot"]["dimensions"] = list(captured.size)
        image = Image.new("RGB", (1000, 180), "white")
        ImageDraw.Draw(image).text((30, 40), "Pot Ubuntu translation test 123", fill="black",
                                  font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48))
        image.save(image_dir / "pot_screenshot_cut.png")
        reports["ocr"] = driver.async_js("return await potInvoke('system_ocr',{lang:'eng'});")
        print("OCR:", reports["ocr"], flush=True)
        reports["tray_update"] = driver.async_js("return await potInvoke('update_tray',{language:'en',copyMode:'disable'});")
        import dbus
        bus = dbus.bus.BusConnection(env["DBUS_SESSION_BUS_ADDRESS"])
        watcher_proxy = bus.get_object("org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher")
        items = dbus.Interface(watcher_proxy, "org.freedesktop.DBus.Properties").Get(
            "org.kde.StatusNotifierWatcher", "RegisteredStatusNotifierItems")
        reports["tray_items"] = [str(item) for item in items]
        if items:
            service, path = str(items[-1]).split("/", 1)
            tray = bus.get_object(service, "/" + path)
            properties = dbus.Interface(tray, "org.freedesktop.DBus.Properties").GetAll("org.kde.StatusNotifierItem")
            reports["tray_status"] = {key: str(properties.get(key, "")) for key in ["Status", "Title", "IconName", "Menu"]}
            menu = dbus.Interface(bus.get_object(service, str(properties["Menu"])), "com.canonical.dbusmenu")
            _, layout = menu.GetLayout(0, -1, dbus.Array([], signature="s"))
            entries = []
            def visit(node):
                entries.append((int(node[0]), str(node[1].get("label", ""))))
                for child in node[2]: visit(child)
            visit(layout)
            reports["tray_menu_labels"] = [label for _, label in entries if label]
            input_id = next(identifier for identifier, label in entries if label == "Input Translate")
            menu.Event(dbus.Int32(input_id), "clicked", dbus.Int32(0), dbus.UInt32(0))
            time.sleep(.5)
            reports["tray_action_windows"] = []
            for handle in driver.cmd("GET", "/window/handles"):
                driver.cmd("POST", "/window", {"handle": handle})
                label = driver.js("return window.__TAURI_METADATA__?.__currentWindow?.label")
                reports["tray_action_windows"].append(label)
                if label == "translate": driver.cmd("DELETE", "/window")
            driver.cmd("POST", "/window", {"handle": config_handle})
        print("Tray:", reports.get("tray_status", reports["tray_items"]), flush=True)
        reports["shortcut_register"] = driver.async_js("return await potInvoke('register_shortcut_by_frontend',{name:'hotkey_input_translate',shortcut:'Ctrl+Alt+Shift+F9'});")
        print("Shortcut registration:", reports["shortcut_register"], flush=True)
        library = ctypes.CDLL(str(ROOT / "work/sysroot/usr/lib/x86_64-linux-gnu/libxdo.so.3"))
        library.xdo_new.argtypes = [ctypes.c_char_p]; library.xdo_new.restype = ctypes.c_void_p
        library.xdo_send_keysequence_window.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_char_p, ctypes.c_uint]
        library.xdo_free.argtypes = [ctypes.c_void_p]
        xdo = library.xdo_new(env["DISPLAY"].encode())
        try: library.xdo_send_keysequence_window(xdo, 0, b"ctrl+alt+shift+F9", 10000)
        finally: library.xdo_free(xdo)
        time.sleep(1)
        reports["windows_after_shortcut"] = driver.cmd("GET", "/window/handles")
        reports["window_labels_after_shortcut"] = []
        for handle in reports["windows_after_shortcut"]:
            driver.cmd("POST", "/window", {"handle": handle})
            reports["window_labels_after_shortcut"].append(driver.js("return window.__TAURI_METADATA__?.__currentWindow?.label"))
        print("Windows after shortcut:", reports["window_labels_after_shortcut"], flush=True)
        driver.cmd("POST", "/window", {"handle": config_handle})
        screenshot = driver.cmd("GET", "/screenshot")
        (directory / "config.png").write_bytes(base64.b64decode(screenshot))
        reports["checks"] = {
            "ui": len(text) > 30,
            "ipc": reports["ipc"].get("ok", False),
            "clipboard": reports["clipboard"].get("value") == "Pot Ubuntu 26.04 剪贴板测试",
            "translation": any(reports[provider].get("ok") and reports[provider].get("value")
                               for provider in ["translation_bing", "translation_google", "translation_deepl"]),
            "ocr": "translation test 123" in reports["ocr"].get("value", ""),
            "screenshot": reports["screenshot"].get("dimensions") == [1280, 900],
            "tray_registration": bool(reports["tray_items"]),
            "tray_menu_action": "translate" in reports.get("tray_action_windows", []),
            "shortcut": "translate" in reports["window_labels_after_shortcut"],
        }
        print("Checks:", json.dumps(reports["checks"]), flush=True)
        if not all(reports["checks"].values()):
            raise RuntimeError("Some runtime checks failed; inspect results.json")
    except Exception as error:
        reports["error"] = str(error)
        print("ERROR:", error, flush=True)
        raise
    finally:
        (directory / "results.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2))
        if driver and driver.session:
            driver.timeout = 3
            try:
                driver.js("window.potInvoke&&potInvoke('tauri',{__tauriModule:'Process',message:{cmd:'exit',exitCode:0}});return true")
            except Exception: pass
            try: driver.cmd("DELETE", "")
            except Exception: pass
        for child in reversed(children):
            child.terminate()
        for child in children:
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: child.kill()
        for log in logs: log.close()


if __name__ == "__main__":
    main()

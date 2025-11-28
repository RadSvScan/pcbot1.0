import requests
import time
import base64
import os

# токен только из GitHub Secrets
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("ERROR: TOKEN отсутствует. Добавь его в GitHub → Settings → Secrets → TOKEN")
    exit()

API = f"https://api.telegram.org/bot{TOKEN}/"
FILE_API = f"https://api.telegram.org/file/bot{TOKEN}/"

auto_mode = None
always_file = False


def get_updates(offset=None):
    try:
        return requests.get(API + "getUpdates", params={"timeout": 20, "offset": offset}).json()
    except:
        return {}


def send_message(chat_id, text):
    requests.post(API + "sendMessage", data={"chat_id": chat_id, "text": text})


def send_file(chat_id, data):
    requests.post(API + "sendDocument",
                  data={"chat_id": chat_id},
                  files={"document": ("result.txt", data)})


def download_file(file_id):
    info = requests.get(API + "getFile", params={"file_id": file_id}).json()
    file_path = info["result"]["file_path"]
    return requests.get(FILE_API + file_path).content


def to_hex(b): return b.hex()
def to_bin(b): return "".join(f"{byte:08b}" for byte in b)
def to_b64(b): return base64.b64encode(b).decode()

def convert(data, mode):
    if mode == "hex": return to_hex(data)
    if mode == "bin": return to_bin(data)
    if mode == "base64": return to_b64(data)
    return None


def extract_mode(text):
    t = text.lower()
    if t.endswith("{hex}"): return "hex", text[:-5].rstrip()
    if t.endswith("{bin}"): return "bin", text[:-5].rstrip()
    if t.endswith("{base64}"): return "base64", text[:-7].rstrip()
    return None, text


# ---------- стартовый текст ----------
HELP_TEXT = """
<b>Datapc converter</b>

Бот умеет:
• текст + {hex} → hex  
• текст + {bin} → binary  
• текст + {base64} → base64  
• любое сообщение + /file → ответ в .txt файле  

Команды:
/help – помощь  
/hex – авто HEX режим  
/bin – авто BIN режим  
/base64 – авто BASE64 режим  
/standart – ручной режим {тип}  
/filemode – всегда отправлять .txt  
/nofilemode – отправлять обычным текстом
Для файлов (например фото) в описании напишите /file 
"""


print("Бот запущен…")

last = 0

while True:
    updates = get_updates(last)

    if updates.get("result"):
        for upd in updates["result"]:
            last = upd["update_id"] + 1
            msg = upd.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")

            if text.startswith("/"):
                cmd = text.lower()

                if cmd in ["/help", "/start"]:
                    send_message(chat_id, HELP_TEXT)
                    continue

                if cmd == "/hex":
                    auto_mode = "hex"
                    send_message(chat_id, "HEX режим включён.")
                    continue

                if cmd == "/bin":
                    auto_mode = "bin"
                    send_message(chat_id, "BIN режим включён.")
                    continue

                if cmd == "/base64":
                    auto_mode = "base64"
                    send_message(chat_id, "BASE64 режим включён.")
                    continue

                if cmd == "/standart":
                    auto_mode = None
                    send_message(chat_id, "Обычный режим. Используй {hex}/{bin}/{base64}")
                    continue

                if cmd == "/filemode":
                    always_file = True
                    send_message(chat_id, "Всегда отправлять результат в .txt")
                    continue

                if cmd == "/nofilemode":
                    always_file = False
                    send_message(chat_id, "Отправлять в чат без файла")
                    continue

            # текст
            if "text" in msg:
                mode, clean_text = extract_mode(text)

                if not mode:
                    mode = auto_mode

                if not mode:
                    continue

                data = clean_text.encode()
                result = convert(data, mode)

                if always_file or "/file" in text.lower() or len(result) > 3500:
                    send_file(chat_id, result.encode())
                else:
                    send_message(chat_id, result)
                continue

            # файлы
            file_id = None

            if "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]

            elif "document" in msg:
                file_id = msg["document"]["file_id"]

            if file_id:
                data = download_file(file_id)

                mode = auto_mode
                caption = msg.get("caption", "")

                manual, _ = extract_mode(caption)
                if manual:
                    mode = manual

                if not mode:
                    continue

                result = convert(data, mode)

                force_file = ("/file" in caption.lower()) or always_file or len(result) > 3500

                if force_file:
                    send_file(chat_id, result.encode())
                else:
                    send_message(chat_id, result)

                continue

    time.sleep(0.2)

# =============================================================================
#  hcig_intro.py  --  "Talk to the Widget"
#  Hardware Cyber Interest Group (HCIG)  --  INTRO MEETING firmware
#
#  Board   : ESP32-C3  (mini / SuperMini / DevKitM-1)
#  Runtime : MicroPython  (esp32-c3 build)
#
#  The friendly first-contact firmware. You flash it yourself, open a serial
#  terminal to the board, and it talks back:
#
#    * whatever you type is echoed to the screen
#    * say  hello  and the board answers            -> flag #1 (you communicated!)
#    * press the physical BOOT button on the board  -> flag #2 (hardware input!)
#    * spam a long line and overrun its tiny buffer -> flag #3 (buffer overflow)
#    * log in with the hardcoded, base64'd password  -> flag #4 (weak creds)
#
#  The "buffer overflow" is a friendly simulation, not real memory corruption
#  (MicroPython is memory-safe) -- but it demonstrates the idea: push more data
#  than a fixed-size buffer expects and something leaks out.
# =============================================================================

import sys
import time
import machine

try:
    import uselect as select
except ImportError:
    import select

try:
    import ubinascii as _bin
except ImportError:
    import binascii as _bin


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
# The onboard BOOT button. GPIO9 is the boot/strapping pin on nearly every
# ESP32-C3 dev board, and doubles as a user button at runtime. It reads HIGH
# when released and LOW when pressed (so we use an internal pull-up).
BUTTON_PIN = 9

# The board pretends it has a 32-byte input buffer. Type a single line longer
# than this and it "overflows."
BUF_SIZE = 32

# Flag strings, kept out of the file in plain text. Each is unscrambled at boot.
_pad = bytes(((i * 0x4d) + 0x1b) & 0xff for i in range(6))

def _dec(s):
    raw = _bin.a2b_base64(s)
    return bytes(raw[i] ^ _pad[i % len(_pad)] for i in range(len(raw))).decode()

FLAG_COMMS    = _dec("TzzgeSf5dwTaXS3zehrRfw==")               # say hello
FLAG_BUTTON   = _dec("TzzgeTasbjfFdzz0fgzqbzbDeR3Bdn/yZg==")   # press the BOOT button
FLAG_OVERFLOW = _dec("TzzgeQbxRArAZCn5aQHbZRD1bxU=")           # overflow the buffer
FLAG_LOGIN    = _dec("TzzgeTj5dwfDZyf9aQzWbSv5fwvHZyvvZg==")   # log in as admin

ADMIN_USER = "admin"
ADMIN_PASS = _bin.a2b_base64("aWxvdmVoYXJkd2FyZQ==").decode()


button = machine.Pin(BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)


# ---------------------------------------------------------------------------
# Serial I/O over the USB console (non-blocking single-char reads)
# ---------------------------------------------------------------------------
_poll = select.poll()
_poll.register(sys.stdin, select.POLLIN)


def getch():
    if _poll.poll(0):
        return sys.stdin.read(1)
    return None


def out(s):
    sys.stdout.write(s)


BANNER = (
    "\r\n"
    "  ____                       _   __        ___     _            _   \r\n"
    " / ___| _ __ ___   __ _ _ __| |_ \\ \\      / (_) __| | __ _  ___| |_ \r\n"
    " \\___ \\| '_ ` _ \\ / _` | '__| __| \\ \\ /\\ / /| |/ _` |/ _` |/ _ \\ __|\r\n"
    "  ___) | | | | | | (_| | |  | |_   \\ V  V / | | (_| | (_| |  __/ |_ \r\n"
    " |____/|_| |_| |_|\\__,_|_|   \\__|   \\_/\\_/  |_|\\__,_|\\__, |\\___|\\__|\r\n"
    "                    SmartWidget 3000                 |___/  v1.0.3  \r\n"
    "\r\n"
    "You're talking to a real microcontroller over a wire. It echoes what you\r\n"
    "type. Type 'help' to see the commands. There are flags hidden in here.\r\n"
)


def show_help():
    out("\r\n"
        "commands:\r\n"
        "  help     show this help\r\n"
        "  hello    say hi to the board\r\n"
        "  button   what's that little button do?\r\n"
        "  login    sign in to the admin panel\r\n"
        "  about    what this device is\r\n"
        "\r\n"
        "one more thing: the input buffer is only {} bytes.\r\n".format(BUF_SIZE))


def handle_line(line):
    cmd = line.strip().lower()
    if cmd == "help":
        show_help()
    elif cmd == "hello":
        out("\r\nThe widget hears you. You're talking to real hardware now.\r\n"
            "  flag: " + FLAG_COMMS + "\r\n")
    elif cmd == "button":
        out("\r\nThere's a small button on the board labeled BOOT (or 0).\r\n"
            "Give it a press and watch this screen...\r\n")
    elif cmd == "login" or cmd.startswith("login "):
        parts = line.strip().split(None, 1)
        pw = parts[1].strip().lower() if len(parts) > 1 else ""
        if not pw:
            out("\r\nusage: login <password>\r\n")
        elif pw == ADMIN_PASS.lower():
            out("\r\naccess granted. signed in as admin.\r\n"
                "  flag: " + FLAG_LOGIN + "\r\n")
        else:
            out("\r\naccess denied.\r\n"
                "(the admin password is hardcoded in the firmware, and only\r\n"
                " lightly scrambled. read the firmware and unscramble it.)\r\n")
    elif cmd == "about":
        out("\r\nSmartWidget 3000, an ESP32-C3 running MicroPython.\r\n"
            "You flashed this firmware yourself. This text and that button\r\n"
            "are wired to code you put on the chip a few minutes ago.\r\n")
    elif cmd == "":
        pass
    else:
        out("\r\nunknown command: '" + line.strip() + "'  (try 'help')\r\n")


def overflow():
    out("\r\n\r\n"
        "*** !! INPUT BUFFER OVERFLOW !! ***\r\n"
        "you pushed more than " + str(BUF_SIZE) + " bytes into a "
        + str(BUF_SIZE) + "-byte buffer.\r\n"
        "the write ran off the end and ran over the memory next to it,\r\n"
        "and here's what spilled out:\r\n"
        "  flag: " + FLAG_OVERFLOW + "\r\n"
        "\r\n(on a real, memory-unsafe device this is how attackers take\r\n"
        " control. here it just hands you a flag.)\r\n")


def button_pressed_flag():
    out("\r\n\r\n"
        ">>> button press detected on GPIO" + str(BUTTON_PIN) + " <<<\r\n"
        "that wasn't the keyboard. the chip read a real voltage change on a pin\r\n"
        "when you pushed the button. this is hardware input.\r\n"
        "  flag: " + FLAG_BUTTON + "\r\n")


def main():
    out(BANNER)
    out("\r\nwidget> ")

    buf = ""
    prev_btn = button.value()      # 1 = released (pulled up)
    while True:
        # --- physical button: fire on a press (HIGH -> LOW edge) ---
        cur_btn = button.value()
        if prev_btn == 1 and cur_btn == 0:
            button_pressed_flag()
            out("widget> ")
            time.sleep_ms(50)      # crude debounce
        prev_btn = cur_btn

        # --- serial input ---
        c = getch()
        if c is None:
            time.sleep_ms(5)
            continue

        if c == "\r" or c == "\n":
            out("\r\n")
            handle_line(buf)
            buf = ""
            out("widget> ")
        elif c == "\x7f" or c == "\x08":   # backspace / delete
            if buf:
                buf = buf[:-1]
                out("\x08 \x08")
        else:
            buf += c
            out(c)                          # echo the character
            if len(buf) > BUF_SIZE:
                overflow()
                buf = ""
                out("widget> ")


main()

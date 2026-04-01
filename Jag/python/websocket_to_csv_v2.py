import websocket
import threading
import sys
import time
from datetime import datetime

# --- OS-Specific Keyboard Listener ---
if sys.platform == "win32":
    import msvcrt
    def read_char():
        return msvcrt.getch().decode('utf-8', errors='ignore') 
else:
    import termios
    import tty
    def read_char():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)  
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

# --- Global Variables ---
csv_filename = "output.csv"
out_file = None
start_time = None

# --- WebSocket Callbacks ---
def on_message(ws, message):
    global start_time, out_file
    
    if out_file and not out_file.closed:
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Formats the time to 6 decimal places and appends the raw Pico string
        out_file.write(f"{elapsed:.6f},{message}\n")
        out_file.flush() 

def on_open(ws):
    global start_time
    print(f"Connected! Listening for messages...\n{'-'*40}")
    start_time = datetime.now()

def on_close(ws, close_status_code, close_msg):
    print("\nConnection closed safely.")
    if out_file and not out_file.closed:
        out_file.close()
        print(f"Data successfully saved to {csv_filename}")

def on_error(ws, error):
    print(f"\n[Error] {error}")

# --- Background Keyboard Thread ---
def spacebar_listen(ws):
    print(">> Press SPACEBAR at any time to stop recording <<\n")
    while True:
        ch = read_char()
        if ch == ' ':
            print("\n[!] Spacebar pressed. Halting data collection...")
            ws.close() 
            break

# --- Main Execution ---
if __name__ == "__main__":
    if len(sys.argv) == 2:
        csv_filename = sys.argv[1]  
        
    try:
        out_file = open(csv_filename, 'w+')
    except Exception as e:
        print(f"Failed to open {csv_filename}: {e}")
        sys.exit(1)

    uri = "ws://192.168.4.1:81"

    websocket.enableTrace(False)

    ws = websocket.WebSocketApp(uri,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    kb_thread = threading.Thread(target=spacebar_listen, args=(ws,))
    kb_thread.daemon = True
    kb_thread.start()

    try:
        ws.run_forever() 
    except KeyboardInterrupt:
        print("\nDisconnected via KeyboardInterrupt.")
        ws.close()
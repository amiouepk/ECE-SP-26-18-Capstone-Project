import websocket
import threading
import sys
import time
import array as arr
#import select
from datetime import datetime

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


csv_filename = "output.csv"
out_file = None
start_time = None
label = None
label_next = False
default_label = 'none'

ch = ''

custom = False
custom_opts = [] * 10
custom_opts_len = 10


def on_message(ws, message):
    global start_time, out_file, label_next
    #print("Connecting to websocket")
    if out_file and not out_file.closed:
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Formats the time to 6 decimal places and appends the raw Pico string

        if label_next:
            #print("Detected in socket thread")
            message = message + f',{label}'
            #label_next = False
        else:
            message = message + f',{default_label}'
            
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

# def set_label_next():
#     global label_next
#     if label_next:
#         label_next = False
#     else:
#         label_next = True

# --- Background Keyboard Thread ---
def spacebar_listen(ws):
    global label_next, label, ch
    print(">> Press SPACEBAR at any time to label <<\n")

    if custom == False:
        while True:
            ch = read_char()
            if ch == '1':
                label = 'rock'
                label_next = True
            elif ch == '2':
                label = 'paper'
                label_next = True
            elif ch == '3':
                label = 'scissors'
                label_next = True
            elif ch == ' ':
                label_next = False

            # if ch == '1':
            #     label = ''
            
            #     #print("\n[!] Labeled")
                

            #     #ws.close() 

    i = 0
    while True:
        ch = read_char()
        
        while i < custom_opts_len:
            if ch == custom_opts[i]:
                label = custom_opt[i]
                label_next = True

        i = 0
            
        

def custom_opt_copy (argv, j, arg_len):

    lim = j + 10
        
    i = 0
    while j < lim:
        custom_opts[i] = argv[j]
        j += 1

    custom_opts_len = i + 1
    
    return j

# --- Main Execution ---
if __name__ == "__main__":

    arg_len = len(sys.argv)


    if arg_len >= 3:
        if sys.argv[1] == '-c':
            if sys.argv[2].endswith('.csv') == True:
                print('Error: Need custome named gestures with custom option')
                sys.exit(2)
            else:
                j = custom_opt_copy(sys.argv, 2)
                if sys.argv[j] == '-o':
                    csv_filename = sys.argv[j + 1]
        else:
            print("Error: You must use -c command to use custom gestures")
            sys.exit(2)

                
                
            custom = True
            #if sys.argv[]

    if arg_len == 2:
        csv_filename = sys.argv[1]
    
    
    try:
        out_file = open(csv_filename, 'w+')
    except Exception as e:
        print(f"Failed to open {csv_filename}: {e}")
        out_file.close()
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.exit(1)
    

    uri = "ws://192.168.4.1:81"

    websocket.enableTrace(False)

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    #tty.setraw(fd)

    print("Connecting to websocket")
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
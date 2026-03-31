import websocket
import time
import sys

# Global variables for frequency math
msg_count = 0
start_time = 0

def on_message(ws, message):
    global msg_count, start_time
    
    # Optional: Uncomment to see the raw data 
    print(f">> {message}")
    
    msg_count += 1
    current_time = time.time()
    elapsed_time = current_time - start_time
    
    # Calculate frequency every 1 second
    if elapsed_time >= 1.0:
        frequency = msg_count / elapsed_time
        print(f"[!] Data Frequency: {frequency:.2f} Hz")
        
        msg_count = 0
        start_time = current_time

def on_error(ws, error):
    print(f"\n[Error] {error}")

def on_close(ws, close_status_code, close_msg):
    print("\nConnection closed.")

def on_open(ws):
    global start_time
    print("Connected! Listening for messages...\n" + "-"*40)
    start_time = time.time()

if __name__ == "__main__":
    uri = sys.argv[1] if len(sys.argv) > 1 else "ws://192.168.4.1:81/"
    print(f"Connecting to {uri}...")
    
    # Suppress verbose trace logs
    websocket.enableTrace(False)
    
    ws = websocket.WebSocketApp(uri,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\nDisconnected.")
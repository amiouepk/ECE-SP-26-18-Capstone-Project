import websocket
import sys
import time

msg_count = 0
start_time = time.perf_counter()

def on_message(ws, message):
    global msg_count, start_time
    msg_count += 1
    
    # We use \r to keep the terminal clean, but change to print(message) 
    # if you want to see every raw data line.
    sys.stdout.write(f"\r[DATA] Last message: {message[:40]}... | Count: {msg_count}")
    sys.stdout.flush()
    
    current_time = time.perf_counter()
    if current_time - start_time >= 1.0:
        freq = msg_count / (current_time - start_time)
        print(f"\n--- Frequency: {freq:.2f} Hz ---", flush=True)
        msg_count = 0
        start_time = current_time

def on_error(ws, error):
    print(f"\n[!] ERROR: {error}")

def on_close(ws, status, msg):
    print(f"\n### CLOSED: {status} {msg} ###")
    print("Retrying in 2 seconds...")
    time.sleep(2)

def on_open(ws):
    print("\n### CONNECTED TO SERVER ###", flush=True)

if __name__ == "__main__":
    # Change this to port 80 if 81 continues to fail
    uri = sys.argv[1] if len(sys.argv) > 1 else "ws://192.168.4.1:81"
    
    ws_app = websocket.WebSocketApp(
        uri,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    print(f"Connecting to {uri}...")
    
    # FIX: ping_interval (10) is now > ping_timeout (5)
    # reconnect=5 tells the library to try again automatically if the server isn't up yet
    ws_app.run_forever(ping_interval=10, ping_timeout=5)
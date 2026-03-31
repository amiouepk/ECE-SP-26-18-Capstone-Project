import asyncio
import websockets
import sys
import time

async def listen(uri):
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected! Listening for messages...\n{'-'*40}")
            
            # --- Frequency Calculation Variables ---
            msg_count = 0
            start_time = time.time()
            
            async for message in ws:
                # Optional: Comment out the line below if the data is so fast it floods your terminal
                # print(f">> {message}")
                
                # Increment our message counter
                msg_count += 1
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Every 1 second, calculate and print the frequency
                if elapsed_time >= 1.0:
                    frequency = msg_count / elapsed_time
                    print(f"\n[!] Data Frequency: {frequency:.2f} Hz\n")
                    
                    # Reset counters for the next interval
                    msg_count = 0
                    start_time = current_time

    except websockets.exceptions.ConnectionClosedOK:
        print("Connection closed.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: {e}")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the server running at {uri}?")

if __name__ == "__main__":
    uri = sys.argv[1] if len(sys.argv) > 1 else "ws://192.168.4.1:81"
    try:
        asyncio.run(listen(uri))
    except KeyboardInterrupt:
        print("\nDisconnected.")
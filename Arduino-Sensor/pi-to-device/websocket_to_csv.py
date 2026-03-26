import asyncio
import websockets
import sys
import data
import contextlib
import atexit
import numpy as np
from datetime import datetime

if sys.platform == "win32":
    import msvcrt

    def read_char():
        # msvcrt.getch() returns bytes, decode to string
        return msvcrt.getch().decode('utf-8', errors='ignore') 
else:
    import termios
    import tty

    def read_char():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)  # Use cbreak instead of raw
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

filename = "default_output.txt"
csv_filename = "output.csv"



async def listen(uri):

    #model, scaler, label_encoder, device = load_model()
    features = 39

    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected! Listening for messages...\n{'-'*40}")

            start_time = datetime.now()

            with open(csv_filename, 'w+') as out_file:


                async for message in ws:
                    
                    print(message)
                    
                    out_file.write(f"{(datetime.now() - start_time).total_seconds()},{message}\n")



    except websockets.exceptions.ConnectionClosedOK:
        print("Connection closed.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: {e}")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the server running at {uri}?")

async def spacebar_listen():
    loop = asyncio.get_running_loop()

    try:
        while True:
            result = await loop.run_in_executor(None, read_char)
            #result = await loop.run_in_executor(None, sys.stdin.read, 1)
            if result == ' ':
                print("Space has been pressed")
                #break
    except asyncio.CancelledError:
        raise
    #print("Spacebar Pressed")

async def main():
    
    uri = "ws://192.168.4.1:81"

    ws_task = asyncio.create_task(listen(uri))
    spacebar_task = asyncio.create_task(spacebar_listen())
    
    done, pending = await asyncio.wait([ws_task, spacebar_task], return_when = asyncio.FIRST_COMPLETED)
    
    for task in pending:
        task.cancel()






if __name__ == "__main__":
    
    if len(sys.argv) == 2:
        csv_filename = sys.argv[1]  
    
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDisconnected.")
        exit()
    
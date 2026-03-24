import asyncio
import websockets
import sys
import formatter          # make sure these exist
import data
import contextlib
import atexit
import csv_formatter
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

async def listen(uri):
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected! Listening for messages...\n{'-'*40}")
            num_sensors = 6
            out_file = open(filename, 'w+')

            start_time = datetime.now()
            relative_time = None    

            async for message in ws:
                print(f">> {message}")


                sens_data = formatter.file_reading(message)

                if sens_data is not None:
                    out_file.write(f"Time:  {(datetime.now() - start_time).total_seconds()}\n{sens_data}\n")
                print(sens_data)

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

    # try:
    #     asyncio.run(listen(uri))
    # except


async def clean_shutdown(event):
    print("clean shutdown funciton")



if __name__ == "__main__":
    
    if len(sys.argv) == 2:
        filename = sys.argv[1]  
    
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDisconnected.")
        exit()
    
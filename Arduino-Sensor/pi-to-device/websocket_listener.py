import asyncio
import websockets
import sys
import main
import data
import datetime

async def listen(uri):
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected! Listening for messages...\n{'-'*40}")
            num_sensors = 6
            out_file = open('sensor_data.txt', 'w+')

            start_time = datetime.now()
            


            async for message in ws:
                print(f">> {message}")
                #print("hu")
                sens_data = main.file_reading(message)
                if sens_data is not None:
                    out_file.write(f"{datetime.now()}{sens_data}\n")

                
                print(sens_data)

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
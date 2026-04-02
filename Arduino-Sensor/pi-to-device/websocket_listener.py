import asyncio
import websockets
import sys
import data
import contextlib
import atexit
import numpy as np
import torch
from datetime import datetime
import torch
import torch.nn as nn
import numpy as np
import __main__ #???is needed???


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

filename = "default_output.csv"
#csv_filename = "output.csv"

def error_message ():
    print("Options: ")
    print("-l for live reading from glove too model")
    print("-w to only write data to glove")
    print("1st arg: script, 2nd arg: option, 3rd arg: filename")

class SensorClassifier(nn.Module):
    def __init__(self, input_size, num_classes):
        super(SensorClassifier, self).__init__()
        # Layer 1
        self.layer1 = nn.Linear(input_size, 64)
        self.relu1 = nn.ReLU()
        # Layer 2
        self.layer2 = nn.Linear(64, 32)
        self.relu2 = nn.ReLU()
        # Output Layer
        self.output_layer = nn.Linear(32, num_classes)

    def forward(self, x):
        out = self.layer1(x)
        out = self.relu1(out)
        out = self.layer2(out)
        out = self.relu2(out)
        out = self.output_layer(out)
        return out

__main__.SensorClassifier = SensorClassifier


def load_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading models to {device}...")

    model = torch.load("../../ML/model.pth", map_location=device, weights_only=False)
    model.to(device)
    model.eval()

    scaler = torch.load("../../ML/scaler.pt", weights_only=False)
    label_encoder = torch.load("../../ML/encoder.pt", weights_only=False)

    return model, scaler, label_encoder, device

async def live_listen(uri):

    import torch
    import torch.nn as nn
    import numpy as np
    import __main__ #???is needed???

    model, scaler, label_encoder, device = load_model()
    features = 39

    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected! Listening for messages...\n{'-'*40}")

            start_time = datetime.now()

            with open(filename, 'w+') as out_file:


                async for message in ws:
                    #print(f">> {message}")

                    #full_data = f"{(datetime.now() - start_time).total_seconds()},{message}\n"

                    try:
                        values = [float(x) for x in message.split(',')]
                    except ValueError:
                        print("Skipping malformed message")
                        continue
                    
                    if len(values) != features:
                        print(f"Warning: expected {features} values, got {len(values)}. Skipping.")
                        continue


                    input_array = np.array(values, dtype=np.float32).reshape(1, -1)
                    scaled_input = scaler.transform(input_array)

                    input_tensor = torch.FloatTensor(scaled_input).to(device)

                    with torch.no_grad():
                        outputs = model(input_tensor)
                        pred_idx = torch.argmax(outputs, dim=1).item()

                    predicted_label = label_encoder.inverse_transform([pred_idx])[0]

                    print(f"Prediction: {predicted_label}")

              
                    out_file.write(f"{(datetime.now() - start_time).total_seconds()},{message},{predicted_label}\n")



    except websockets.exceptions.ConnectionClosedOK:
        print("Connection closed.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: {e}")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the server running at {uri}?")

async def write_listen(uri):
    #model, scaler, label_encoder, device = load_model()
    #features = 39

    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected! Listening for messages...\n{'-'*40}")

            start_time = datetime.now()

            with open(filename, 'w+') as out_file:


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

    if sys.argv[1] == '-l':
        print("Live option selected")
        ws_task = asyncio.create_task(live_listen(uri))
    elif sys.argv[1] == '-w':
        print("Write option selected")
        ws_task = asyncio.create_task(write_listen(uri))
    else:
        error_message()
    
    

    
    
    spacebar_task = asyncio.create_task(spacebar_listen())
    
    done, pending = await asyncio.wait([ws_task, spacebar_task], return_when = asyncio.FIRST_COMPLETED)
    
    for task in pending:
        task.cancel()



async def clean_shutdown(event):
    print("clean shutdown funciton")

def write():
    pass

if __name__ == "__main__":
    
    arg_len = len(sys.argv)

    if arg_len != 3:
        error_message()
        exit()

    if not sys.argv[2].endswith('.csv'):
        filename = sys.argv[2] + '.csv'
    else:
        filename = sys.argv[2]


    

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDisconnected.")
        exit()

   
    
        
    
    
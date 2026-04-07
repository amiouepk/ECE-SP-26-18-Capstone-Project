import websocket
import sys
import numpy as np
import torch
from datetime import datetime
import torch
import torch.nn as nn
import numpy as np
import __main__ #???is needed???


model = None
scaler = None
label_encoder = None
features = 48



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
    global model, scaler, label_encoder, device

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading models to {device}...")

    model = torch.load("../../ML/model.pth", map_location=device, weights_only=False)
    model.to(device)
    model.eval()

    scaler = torch.load("../../ML/scaler.pt", weights_only=False)
    label_encoder = torch.load("../../ML/encoder.pt", weights_only=False)

    #return model, scaler, label_encoder, device

def on_message(ws, message):
    global start_time, out_file, label_next
    #print("Connecting to websocket")

    #
    # CHANGE LOGIC HERE AS NEEDED
    #
    if out_file and not out_file.closed:
        elapsed = (datetime.now() - start_time).total_seconds()
        
        try:
            values = [float(x) for x in message.split(',')]
        except ValueError:
            print("Skipping malformed message")
            
        
        if len(values) != features:
            print(f"Warning: expected {features} values, got {len(values)}. Skipping.")



        input_array = np.array(values, dtype=np.float32).reshape(1, -1)
        scaled_input = scaler.transform(input_array)

        input_tensor = torch.FloatTensor(scaled_input).to(device)

        with torch.no_grad():
            outputs = model(input_tensor)
            pred_idx = torch.argmax(outputs, dim=1).item()

        predicted_label = label_encoder.inverse_transform([pred_idx])[0]

        print(f"Prediction: {predicted_label}")

        
            
        out_file.write(f"{elapsed:.6f},{message}\n")
        out_file.flush() 

def on_open(ws):
    global start_time
    print(f"Connected! Listening for messages...\n{'-'*40}")
    start_time = datetime.now()

def on_close(ws, close_status_code, close_msg):
    print("\nConnection closed safely.")
        

def on_error(ws, error):
    print(f"\n[Error] {error}")




# --- Main Execution ---
if __name__ == "__main__":

    arg_len = len(sys.argv)
    

    model, 

    uri = "ws://192.168.4.1:81"

    websocket.enableTrace(False)


    print("Connecting to websocket")
    ws = websocket.WebSocketApp(uri,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    try:
        ws.run_forever() 
    except KeyboardInterrupt:
        print("\nDisconnected via KeyboardInterrupt.")
        ws.close()
    
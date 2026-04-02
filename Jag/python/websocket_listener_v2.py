import websocket
import time
import sys
import numpy as np
import torch
#from datetime import datetime
import torch
import torch.nn as nn
import numpy as np
import __main__ #???is needed???

# Global variables for frequency math
msg_count = 0
start_time = 0

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

def on_message(ws, message):
    global msg_count, start_time
    
    #print("number 1")
    model, scaler, label_encoder, device = load_model()
    features = 48
    #rint("number 2")
    # Optional: Uncomment to see the raw data 
    print(f">> {message}")
    
    msg_count += 1
    current_time = time.time()
    elapsed_time = current_time - start_time
    
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


    out_file.write(f"{(datetime.now() - start_time).total_seconds()},{message},{predicted_label}\n")

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

    #print("gyg")

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
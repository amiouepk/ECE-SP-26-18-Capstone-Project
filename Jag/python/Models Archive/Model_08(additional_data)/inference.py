import websocket
from collections import deque
import numpy as np


# These are the indices of Accel and Mag data, skipping all 'Gyr' columns
# Total expected features: 36
KEEP_INDICES = [
    # BNO0
    0, 1, 2, 3, 7, 8, 9,
    # BNO1
    10, 11, 12, 13, 17, 18, 19,
    # BNO2
    20, 21, 22, 23, 27, 28, 29,
    # BNO3
    30, 31, 32, 33, 37, 38, 39,
    # MPU0
    40, 41, 42, 43, 
    # MPU1
    47, 48, 49, 50
]

PICO_URI = "ws://192.168.4.1:81"
CONFIDENCE_THRESHOLD = 0.62 
GESTURE_MAP = {
        0: "A",
        1: "B",
        2: "X",
        3: "Y",
        4: "none",
        5: "paper",
        6: "pinch close",
        7: "pinch open",
        8: "point left",
        9: "point right",
        10: "rock",
        11: "scissors"
    }
WINDOW_SIZE = 5

def run_live_inference_windowed(model):
    # 1. Initialize sliding window buffer
    # Each entry will be the 36 filtered features
    window_buffer = deque(maxlen=WINDOW_SIZE)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    try:
        ws = websocket.create_connection(PICO_URI, timeout=5)
        print(f"--- Connected to Glove at {PICO_URI} ---")
        print(f"--- Using Window Size: {WINDOW_SIZE} ---")
        ws.recv() # Skip Header

        while True:
            raw_message = ws.recv()
            if not raw_message: continue

            try:
                # 2. Parse and Filter
                full_data = [float(x) for x in raw_message.split(',')]
                filtered_sample = [full_data[i] for i in KEEP_INDICES]

                input_tensor = torch.tensor(filtered_sample, dtype=torch.float32).unsqueeze(0).to(device)
                
                # 6. Inference
                with torch.inference_mode():
                    logits = model(input_tensor)
                    probs = torch.softmax(logits, dim=1)
                    max_conf, pred_idx = torch.max(probs, dim=1)
                
                confidence = max_conf.item()
                
                # 7. Display
                if confidence > CONFIDENCE_THRESHOLD:
                    gesture = GESTURE_MAP[pred_idx.item()]
                    
                else:
                    gesture = "None"
                print(f"Detected: {gesture:10} | Conf: {confidence:.2f}", end="\r")
            except (ValueError, IndexError):
                continue

    except KeyboardInterrupt:
        print("\nStopping Live Inference...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        if 'ws' in locals(): ws.close()


import torch
import json
from torch import nn

#HyperParameters
EPOCHS = 600
SEED = 40

STD = 0.02
COPY = 5
HIDDEN = 0 # No consistent hidden layers in other models
DROPOUT = 0.1

# Set BATCH_SIZE to the full training dataset size for now
# BATCH_SIZE = len(X_train)
LR = 1e-3

N_FOLDS = 5

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# def run_model():
    # 1. Re-define the class (PyTorch needs the architecture definition)
class RPSModel(nn.Module):
    def __init__(self, input_features, output_features):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_features, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(32, output_features)
        )

    def forward(self, x):
        return self.net(x)

# 2. Load Metadata
with open("model_metadata.json", "r") as f:
    meta = json.load(f)

# 3. Instantiate and Load Weights
loaded_model = RPSModel(input_features=meta["input_features"], 
                        output_features=meta["output_classes"]).to(device)
loaded_model.load_state_dict(torch.load("model.pth"))
loaded_model.eval()

print("Model successfully reconstructed!")
    
# run_model()

run_live_inference_windowed(loaded_model)

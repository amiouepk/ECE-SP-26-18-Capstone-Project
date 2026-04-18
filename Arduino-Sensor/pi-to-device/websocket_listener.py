import websocket
import sys
import pyautogui as pag


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
CONFIDENCE_THRESHOLD = 0.82 
GESTURE_MAP = {0: "A", 1: "B", 2: "X", 3: "Y", 4: "None", 5: "paper", 6: "rock", 7: "scissors"}


def no_action():
    pass

def open_notepad():

    pass

def super_menu():
    pag.hotkey('shift', )
    pass

def print_screen():
    pag.hotkey('shift', 'print')
    pass

ACTION_MAP = {0: no_action, 1: open_notepad, 2: super_menu, 3: print_screen}


def run_live_inference_hardcoded(model):
    # Model check
    # expected_features = model_4.state_dict()['fc1.weight'].shape[1]
    # if len(KEEP_INDICES) != expected_features:
    #     print(f"Error: Mask size ({len(KEEP_INDICES)}) != Model inputs ({expected_features})")
    #     return

    try:
        ws = websocket.create_connection(PICO_URI, timeout=5)
        print(f"--- Connected to Glove at {PICO_URI} ---")
        ws.recv() # Skip Header
        model.eval()

        while True:
            raw_message = ws.recv()
            if not raw_message: continue

            try:
                # 1. Parse all 54 incoming floats
                full_data = [float(x) for x in raw_message.split(',')]
                
                # 2. Extract only the Accel/Mag indices
                filtered_data = [full_data[i] for i in KEEP_INDICES]
                
                # 3. Predict
                input_tensor = torch.tensor(filtered_data, dtype=torch.float32).unsqueeze(0).to(device)
                
                with torch.inference_mode():
                    logits = model(input_tensor)
                    probs = torch.softmax(logits, dim=1)
                    max_conf, pred_idx = torch.max(probs, dim=1)
                
                confidence = max_conf.item()
                
                # 4. Display Result
                if confidence > CONFIDENCE_THRESHOLD:
                    gesture = GESTURE_MAP[pred_idx.item()]
                    ACTION_MAP[pred_idx.item()]()

                    print(f"Detected: {gesture:10} | Confidence: {confidence:.2f}", end="\r")
                    
                else:
                    print(f"Detected: {'None':10} | Confidence: {confidence:.2f}", end="\r")

            except (ValueError, IndexError):
                continue

    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"\nConnection Error: {e}")
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
        self.linear_layer_stack = nn.Sequential(
            nn.Linear(in_features=input_features, out_features=32),
            nn.ReLU(),
            nn.Dropout(p=DROPOUT),

            nn.Linear(in_features=32, out_features=16),
            nn.ReLU(),
            nn.Dropout(p=DROPOUT),

            nn.Linear(in_features=16, out_features=output_features)
        )

    # 3. Define a forward method containing the forward pass computation
    def forward(self, x):
        return self.linear_layer_stack(x)    # ... (paste your RPSModel class code here) ...

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

run_live_inference_hardcoded(loaded_model)

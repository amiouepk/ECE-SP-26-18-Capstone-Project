import websocket
from collections import deque
import numpy as np
import pyautogui as pag
import threading
import time
import subprocess
import dbus

pag.PAUSE = 0

KEEP_INDICES = [
    0, 1, 2, 3, 7, 8, 9,
    10, 11, 12, 13, 17, 18, 19,
    20, 21, 22, 23, 27, 28, 29,
    30, 31, 32, 33, 37, 38, 39,
    40, 41, 42, 43,
    47, 48, 49, 50
]

PICO_URI = "ws://192.168.4.1:81"
CONFIDENCE_THRESHOLD = 0.82
GESTURE_MAP = {0: "None", 1: "Maximize", 2: "Minimize", 3: "Scissors"}
WINDOW_SIZE = 5
ACTION_COOLDOWN = 2.0

last_action_time = 0
last_action_gesture = None
tracked_window_id = None


def no_action():
    pass


def minimize_window():
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object('org.kde.KWin', '/KWin')
        kwin = dbus.Interface(proxy, 'org.kde.KWin')
        method = kwin.get_dbus_method('showDesktop')
        method(True)
    except Exception as e:
        print(f"[DBG] Min error: {e}")


def maximize_window():
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object('org.kde.KWin', '/KWin')
        kwin = dbus.Interface(proxy, 'org.kde.KWin')
        method = kwin.get_dbus_method('showDesktop')
        method(False)
    except Exception as e:
        print(f"[DBG] Max error: {e}")


def print_screen():
    print("[DBG] Taking screenshot!")
    pag.hotkey('shift', 'print')


ACTIONS = [no_action, maximize_window, minimize_window, print_screen]


def run_live_inference_windowed(model):
    global last_action_time, last_action_gesture
    
    window_buffer = deque(maxlen=WINDOW_SIZE)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    try:
        ws = websocket.create_connection(PICO_URI, timeout=5)
        print(f"--- Connected to Glove at {PICO_URI} ---")
        print(f"--- Using Window Size: {WINDOW_SIZE} ---")
        ws.recv()

        while True:
            raw_message = ws.recv()
            if not raw_message: continue

            try:
                full_data = [float(x) for x in raw_message.split(',')]
                filtered_sample = [full_data[i] for i in KEEP_INDICES]
                
                window_buffer.append(filtered_sample)

                if len(window_buffer) < WINDOW_SIZE:
                    continue

                data_window = np.array(window_buffer)
                means = np.mean(data_window, axis=0)
                variances = np.var(data_window, axis=0)

                combined_input = np.concatenate([means, variances])
                
                input_tensor = torch.tensor(combined_input, dtype=torch.float32).unsqueeze(0).to(device)
                
                with torch.inference_mode():
                    logits = model(input_tensor)
                    probs = torch.softmax(logits, dim=1)
                    max_conf, pred_idx = torch.max(probs, dim=1)
                
                confidence = max_conf.item()
                gesture_idx = pred_idx.item()
                
                if confidence > CONFIDENCE_THRESHOLD:
                    gesture = GESTURE_MAP[gesture_idx]
                    print(f"Detected: {gesture:10} | Conf: {confidence:.2f}", end="\r")
                    
                    current_time = time.time()
                    if gesture_idx != last_action_gesture or current_time - last_action_time > ACTION_COOLDOWN:
                        last_action_gesture = gesture_idx
                        last_action_time = current_time
                        threading.Thread(target=ACTIONS[gesture_idx], daemon=True).start()
                else:
                    print(f"Detected: {'None':10} | Conf: {confidence:.2f}", end="\r")

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

EPOCHS = 600
SEED = 40

STD = 0.02
COPY = 5
HIDDEN = 0
DROPOUT = 0.1

LR = 1e-3

N_FOLDS = 5

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")


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

    def forward(self, x):
        return self.linear_layer_stack(x)


with open("model_metadata.json", "r") as f:
    meta = json.load(f)

loaded_model = RPSModel(input_features=meta["input_features"], 
                        output_features=meta["output_classes"]).to(device)
loaded_model.load_state_dict(torch.load("model.pth"))
loaded_model.eval()

print("Model successfully reconstructed!")

run_live_inference_windowed(loaded_model)
import websocket
from collections import deque
import numpy as np
import pyautogui as pag
import threading
import time

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
GESTURE_MAP = {0: "None", 1: "Point Left", 2: "Point Right"}
WINDOW_SIZE = 5
ACTION_COOLDOWN = 1.5

last_action_time = 0
last_action_gesture = None


def no_action():
    pass


def point_left():
    try:
        pag.press('left')
    except Exception as e:
        print(f"[DBG] Left error: {e}")


def point_right():
    try:
        pag.press('right')
    except Exception as e:
        print(f"[DBG] Right error: {e}")


def run_live_inference(model):
    global last_action_time, last_action_gesture
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    try:
        ws = websocket.create_connection(PICO_URI, timeout=5)
        print(f"--- Connected to Glove at {PICO_URI} ---")
        ws.recv()

        while True:
            raw_message = ws.recv()
            if not raw_message: continue

            try:
                full_data = [float(x) for x in raw_message.split(',')]
                filtered_sample = [full_data[i] for i in KEEP_INDICES]
                
                input_tensor = torch.tensor(filtered_sample, dtype=torch.float32).unsqueeze(0).to(device)
                
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
                        if gesture_idx == 1:
                            threading.Thread(target=point_left, daemon=True).start()
                        elif gesture_idx == 2:
                            threading.Thread(target=point_right, daemon=True).start()
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

DROPOUT = 0.1

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


loaded_model = RPSModel(input_features=36, output_features=3).to(device)
loaded_model.eval()

print("Model loaded (36 features, 3 classes)")
print("Using left/right for presentation navigation")

if __name__ == "__main__":
    run_live_inference(loaded_model)
import websocket
from collections import deque
import numpy as np
import pyautogui as pag
import threading
import time
import torch
from torch import nn

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
CONFIDENCE_THRESHOLD = 0.7
GESTURE_MAP = {0: "None", 1: "Point Left", 2: "Point Right"}
WINDOW_SIZE = 5
CONSENSUS_REQUIRED = 3
ACTION_COOLDOWN = 1.5
DISPLAY_WIDTH = 50

gesture_buffer = deque(maxlen=WINDOW_SIZE)
consensus_count = 0
last_action_time = 0
last_action_gesture = None
stable_gesture = None


def no_action():
    pass


def point_left():
    try:
        pag.press('left')
    except Exception as e:
        print(f"\n[DBG] Left error: {e}")


def point_right():
    try:
        pag.press('right')
    except Exception as e:
        print(f"\n[DBG] Right error: {e}")


def run_live_inference_windowed(model):
    global last_action_time, last_action_gesture, stable_gesture

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
                    gesture_buffer.append(gesture_idx)
                    
                    if len(gesture_buffer) >= WINDOW_SIZE:
                        counts = [gesture_buffer.count(i) for i in range(3)]
                        max_count = max(counts)
                        if max_count >= CONSENSUS_REQUIRED:
                            stable_gesture = counts.index(max_count)
                        else:
                            stable_gesture = None
                    
                    msg = f"Detected: {gesture:12} | Conf: {confidence:.2f}"
                    print(f"\r{msg:<{DISPLAY_WIDTH}}", end="", flush=True)
                    
                    current_time = time.time()
                    if stable_gesture is not None and (stable_gesture != last_action_gesture or current_time - last_action_time > ACTION_COOLDOWN):
                        last_action_gesture = stable_gesture
                        last_action_time = current_time
                        if stable_gesture == 1:
                            threading.Thread(target=point_left, daemon=True).start()
                        elif stable_gesture == 2:
                            threading.Thread(target=point_right, daemon=True).start()
                else:
                    gesture_buffer.clear()
                    stable_gesture = None
                    msg = f"Detected: {'None':12} | Conf: {confidence:.2f}"
                    print(f"\r{msg:<{DISPLAY_WIDTH}}", end="", flush=True)

            except (ValueError, IndexError):
                continue

    except KeyboardInterrupt:
        print(f"\r{'':<{DISPLAY_WIDTH}}")
        print("Stopping Live Inference...")
    except Exception as e:
        print(f"\r{'':<{DISPLAY_WIDTH}}")
        print(f"Error: {e}")
    finally:
        if 'ws' in locals(): ws.close()


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


device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

loaded_model = RPSModel(input_features=36, output_features=3).to(device)
loaded_model.load_state_dict(torch.load("model.pth", map_location=device))
loaded_model.eval()

print("Model loaded (36 features, 3 classes)")
print("Using left/right for presentation navigation")

if __name__ == "__main__":
    run_live_inference_windowed(loaded_model)
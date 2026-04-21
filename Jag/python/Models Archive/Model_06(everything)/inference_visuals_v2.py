import websocket
import torch
import json
import numpy as np
import pygame
import time
from collections import deque
from torch import nn

# --- Pygame Configuration ---
WIDTH, HEIGHT = 1000, 700
LEFT_PANE = 400
BG_COLOR = (20, 20, 25)
TEXT_COLOR = (240, 240, 240)
BAR_COLOR_ACC = (0, 180, 255)
BAR_COLOR_MAG = (180, 100, 255)
CONF_COLOR = (0, 255, 120)
PERSISTENCE_DURATION = 1.0  # Seconds to hold the last valid gesture

SENSOR_LAYOUT = [
    ("Back of Hand", 0, 7, BAR_COLOR_ACC),
    ("Thumb", 7, 7, BAR_COLOR_ACC),
    ("Index", 14, 7, BAR_COLOR_ACC),
    ("Middle", 21, 7, BAR_COLOR_ACC),
    ("Ring", 28, 4, BAR_COLOR_MAG),
    ("Pinky", 32, 4, BAR_COLOR_MAG)
]

class RPSModel(nn.Module):
    def __init__(self, input_features, output_features):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_features, 256), nn.BatchNorm1d(256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64), nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 32), nn.BatchNorm1d(32), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(32, output_features)
        )
    def forward(self, x): return self.net(x)

def draw_hud(screen, font, small_font, gesture, confidence, data_vector, is_holding):
    screen.fill(BG_COLOR)
    
    # --- Left Pane: Inference ---
    pygame.draw.rect(screen, (30, 30, 40), (0, 0, LEFT_PANE, HEIGHT))
    
    title_surf = small_font.render("DETECTED GESTURE", True, (150, 150, 150))
    screen.blit(title_surf, (40, 200))
    
    # If we are holding an old value, maybe dim the color slightly
    display_color = CONF_COLOR if not is_holding else (180, 180, 100)
    
    if gesture and gesture.lower() != "none":
        gesture_surf = font.render(gesture.upper(), True, display_color)
        screen.blit(gesture_surf, (40, 240))
        
        # Confidence Bar
        conf_width = int(320 * confidence)
        pygame.draw.rect(screen, (50, 50, 60), (40, 350, 320, 20))
        pygame.draw.rect(screen, display_color, (40, 350, conf_width, 20))
        
        status_text = "HOLDING..." if is_holding else "LIVE"
        conf_text = small_font.render(f"Confidence: {int(confidence*100)}% [{status_text}]", True, TEXT_COLOR)
        screen.blit(conf_text, (40, 380))
    else:
        # Clear/Waiting state
        waiting_surf = font.render("...", True, (80, 80, 80))
        screen.blit(waiting_surf, (40, 240))

    # --- Right Pane: Sensor Data ---
    x_offset = LEFT_PANE + 40
    y_offset = 50
    for label, start, count, color in SENSOR_LAYOUT:
        lbl_surf = small_font.render(label, True, (200, 200, 200))
        screen.blit(lbl_surf, (x_offset, y_offset))
        y_offset += 25
        for i in range(count):
            val = data_vector[start + i] if len(data_vector) > (start + i) else 0
            bar_len = np.clip(abs(val) * 5, 0, 150) 
            pygame.draw.rect(screen, (40, 40, 50), (x_offset, y_offset, 150, 12))
            pygame.draw.rect(screen, color, (x_offset, y_offset, bar_len, 12))
            y_offset += 18
        y_offset += 20
        if y_offset > HEIGHT - 100:
            x_offset += 250
            y_offset = 50

    pygame.display.flip()

def run_live_inference_visual(model, meta):
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    font = pygame.font.SysFont("Arial", 60, bold=True)
    small_font = pygame.font.SysFont("Arial", 18)
    
    window_buffer = deque(maxlen=5)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    # --- Persistence Variables ---
    last_valid_gesture = None
    last_valid_conf = 0.0
    last_seen_time = 0

    try:
        ws = websocket.create_connection("ws://192.168.4.1:81", timeout=5)
        ws.recv() 

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False

            raw_message = ws.recv()
            if not raw_message: continue

            try:
                full_data = [float(x) for x in raw_message.split(',')]
                # Explicit index filter
                current_data = [full_data[i] for i in [0, 1, 2, 3, 7, 8, 9, 10, 11, 12, 13, 17, 18, 19, 20, 21, 22, 23, 27, 28, 29, 30, 31, 32, 33, 37, 38, 39, 40, 41, 42, 43, 47, 48, 49, 50]]
                
                window_buffer.append(current_data)
                if len(window_buffer) < 5: continue

                data_window = np.array(window_buffer)
                means = np.mean(data_window, axis=0)
                input_tensor = torch.tensor(means, dtype=torch.float32).unsqueeze(0).to(device)

                with torch.inference_mode():
                    logits = model(input_tensor)
                    probs = torch.softmax(logits, dim=1)
                    max_conf, pred_idx = torch.max(probs, dim=1)
                
                conf = max_conf.item()
                GESTURE_MAP = {0:"A", 1:"B", 2:"X", 3:"Y", 4:"none", 5:"paper", 6:"pinch close", 7:"pinch open", 8:"point left", 9:"point right", 10:"rock", 11:"scissors"}
                gesture_name = GESTURE_MAP[pred_idx.item()]

                # --- Logic for Filtering "None" and Adding Persistence ---
                current_time = time.time()
                is_holding = False

                # If the current prediction is a real gesture and meets threshold
                if gesture_name.lower() != "none" and conf > 0.62:
                    last_valid_gesture = gesture_name
                    last_valid_conf = conf
                    last_seen_time = current_time
                else:
                    # If current is "none" or low confidence, check if we should still "hold" the last one
                    if last_valid_gesture and (current_time - last_seen_time < PERSISTENCE_DURATION):
                        is_holding = True
                    else:
                        last_valid_gesture = None # Timer expired or no previous gesture

                draw_hud(screen, font, small_font, last_valid_gesture, last_valid_conf, current_data, is_holding)

            except Exception as e:
                continue
    finally:
        pygame.quit()
        if 'ws' in locals(): ws.close()

# Load and execution logic remains same
with open("model_metadata.json", "r") as f:
    meta = json.load(f)
loaded_model = RPSModel(input_features=meta["input_features"], output_features=meta["output_classes"])
loaded_model.load_state_dict(torch.load("model.pth", map_location=torch.device('cpu')))
run_live_inference_visual(loaded_model, meta)
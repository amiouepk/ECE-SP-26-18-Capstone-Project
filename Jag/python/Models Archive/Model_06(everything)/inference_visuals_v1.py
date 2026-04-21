import websocket
import torch
import json
import numpy as np
import pygame
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

# Define groupings for the 36 KEEP_INDICES
# Format: (Label, start_idx_in_filtered_sample, count, color)
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

def draw_hud(screen, font, small_font, gesture, confidence, data_vector):
    screen.fill(BG_COLOR)
    
    # --- Left Pane: Inference ---
    pygame.draw.rect(screen, (30, 30, 40), (0, 0, LEFT_PANE, HEIGHT))
    
    # Gesture Text
    title_surf = small_font.render("DETECTED GESTURE", True, (150, 150, 150))
    screen.blit(title_surf, (40, 200))
    
    gesture_surf = font.render(gesture.upper(), True, CONF_COLOR if confidence > 0.62 else (255, 100, 100))
    screen.blit(gesture_surf, (40, 240))
    
    # Confidence Bar
    conf_width = int(320 * confidence)
    pygame.draw.rect(screen, (50, 50, 60), (40, 350, 320, 20))
    pygame.draw.rect(screen, CONF_COLOR, (40, 350, conf_width, 20))
    conf_text = small_font.render(f"Confidence: {int(confidence*100)}%", True, TEXT_COLOR)
    screen.blit(conf_text, (40, 380))

    # --- Right Pane: Sensor Data ---
    x_offset = LEFT_PANE + 40
    y_offset = 50
    
    for label, start, count, color in SENSOR_LAYOUT:
        # Draw Label
        lbl_surf = small_font.render(label, True, (200, 200, 200))
        screen.blit(lbl_surf, (x_offset, y_offset))
        y_offset += 25
        
        for i in range(count):
            val = data_vector[start + i] if len(data_vector) > (start + i) else 0
            # Scale value for visualization (assuming IMU range around -20 to 20)
            bar_len = np.clip(abs(val) * 5, 0, 150) 
            
            # Draw individual sensor bar
            pygame.draw.rect(screen, (40, 40, 50), (x_offset, y_offset, 150, 12))
            pygame.draw.rect(screen, color, (x_offset, y_offset, bar_len, 12))
            y_offset += 18
        
        y_offset += 20 # Space between groups
        if y_offset > HEIGHT - 100: # Wrap to second column if needed
            x_offset += 250
            y_offset = 50

    pygame.display.flip()

def run_live_inference_visual(model, meta):
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Glove Sensor HUD")
    font = pygame.font.SysFont("Arial", 60, bold=True)
    small_font = pygame.font.SysFont("Arial", 18)
    
    window_buffer = deque(maxlen=5)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    try:
        ws = websocket.create_connection("ws://192.168.4.1:81", timeout=5)
        ws.recv() # Skip Header

        running = True
        current_gesture = "None"
        current_conf = 0.0
        current_data = [0] * 36

        while running:
            # Handle Pygame Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False

            raw_message = ws.recv()
            if not raw_message: continue

            try:
                full_data = [float(x) for x in raw_message.split(',')]
                current_data = [full_data[i] for i in [0, 1, 2, 3, 7, 8, 9, 10, 11, 12, 13, 17, 18, 19, 20, 21, 22, 23, 27, 28, 29, 30, 31, 32, 33, 37, 38, 39, 40, 41, 42, 43, 47, 48, 49, 50]]
                
                window_buffer.append(current_data)
                if len(window_buffer) < 5: continue

                # Note: Using 'means' for inference as it's more stable
                data_window = np.array(window_buffer)
                means = np.mean(data_window, axis=0)
                
                # Check your model input size (36 or 72)
                # If your model needs 36 features, use 'means'. 
                # If it needs 72 (Mean + Var), concatenate them.
                input_tensor = torch.tensor(means, dtype=torch.float32).unsqueeze(0).to(device)

                with torch.inference_mode():
                    logits = model(input_tensor)
                    probs = torch.softmax(logits, dim=1)
                    max_conf, pred_idx = torch.max(probs, dim=1)
                
                current_conf = max_conf.item()
                GESTURE_MAP = {0:"A", 1:"B", 2:"X", 3:"Y", 4:"none", 5:"paper", 6:"pinch close", 7:"pinch open", 8:"point left", 9:"point right", 10:"rock", 11:"scissors"}
                
                current_gesture = GESTURE_MAP[pred_idx.item()] if current_conf > 0.62 else "None"
                
                # Update Visualization
                draw_hud(screen, font, small_font, current_gesture, current_conf, current_data)

            except Exception as e:
                print(f"Data Error: {e}")
                continue

    finally:
        pygame.quit()
        if 'ws' in locals(): ws.close()

# --- Load and Run ---
with open("model_metadata.json", "r") as f:
    meta = json.load(f)

loaded_model = RPSModel(input_features=meta["input_features"], output_features=meta["output_classes"])
loaded_model.load_state_dict(torch.load("model.pth", map_location=torch.device('cpu')))

run_live_inference_visual(loaded_model, meta)
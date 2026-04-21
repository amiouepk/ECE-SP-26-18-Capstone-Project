import websocket
import torch
import json
import numpy as np
import pygame
import time
from collections import deque
from torch import nn

# --- 1. CONFIGURATION & HYPERPARAMETERS ---
PICO_URI = "ws://192.168.4.1:81"
WINDOW_SIZE = 5
CONFIDENCE_THRESHOLD = 0.62
PERSISTENCE_DURATION = 1.0 

# Indices for Accel/Mag (36 total)
KEEP_INDICES = [
    0, 1, 2, 3, 7, 8, 9, 10, 11, 12, 13, 17, 18, 19, 20, 21, 22, 23, 
    27, 28, 29, 30, 31, 32, 33, 37, 38, 39, 40, 41, 42, 43, 47, 48, 49, 50
]

GESTURE_MAP = {
    0: "A", 1: "B", 2: "X", 3: "Y", 4: "None", 5: "Paper", 
    6: "Pinch Close", 7: "Pinch Open", 8: "Point Left", 
    9: "Point Right", 10: "Rock", 11: "Scissors"
}

# Visualization Layout (Label, Start Index in 36-vec, Total Count, Color)
SENSOR_LAYOUT = [
    ("Back of Hand", 0, 7, (0, 180, 255)),
    ("Thumb", 7, 7, (0, 180, 255)),
    ("Index", 14, 7, (0, 180, 255)),
    ("Middle", 21, 7, (0, 180, 255)),
    ("Ring", 28, 4, (180, 100, 255)),
    ("Pinky", 32, 4, (180, 100, 255))
]

# --- 2. MODEL ARCHITECTURE ---
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

# --- 3. UI RENDERING ---
def draw_hud(screen, font, small_font, gesture, confidence, data_vector, is_holding):
    screen.fill((20, 20, 25)) # Background
    
    # Left Pane
    pygame.draw.rect(screen, (30, 30, 40), (0, 0, 400, 700))
    
    title_color = (150, 150, 150)
    screen.blit(small_font.render("DETECTED GESTURE", True, title_color), (40, 200))
    
    display_color = (0, 255, 120) if not is_holding else (180, 180, 100)
    
    if gesture and gesture.lower() != "none":
        gesture_surf = font.render(gesture.upper(), True, display_color)
        screen.blit(gesture_surf, (40, 240))
        
        # Confidence Bar
        pygame.draw.rect(screen, (50, 50, 60), (40, 350, 320, 20))
        pygame.draw.rect(screen, display_color, (40, 350, int(320 * confidence), 20))
        
        status = "[HOLDING]" if is_holding else "[LIVE]"
        conf_text = small_font.render(f"Confidence: {int(confidence*100)}% {status}", True, (240, 240, 240))
        screen.blit(conf_text, (40, 380))
    else:
        screen.blit(font.render("...", True, (80, 80, 80)), (40, 240))

    # Right Pane: Sensor Data (Skipping 4th point of each sensor)
    x_offset, y_offset = 440, 50
    for label, start, count, color in SENSOR_LAYOUT:
        screen.blit(small_font.render(label, True, (200, 200, 200)), (x_offset, y_offset))
        y_offset += 25
        
        for i in range(count):
            if i == 3: continue # Remove the 4th graph
            
            val = data_vector[start + i] if (start + i) < len(data_vector) else 0
            bar_len = np.clip(abs(val) * 5, 0, 150) 
            
            pygame.draw.rect(screen, (40, 40, 50), (x_offset, y_offset, 150, 12))
            pygame.draw.rect(screen, color, (x_offset, y_offset, bar_len, 12))
            y_offset += 18
        
        y_offset += 20
        if y_offset > 600:
            x_offset += 250
            y_offset = 50
            
    pygame.display.flip()

# --- 4. MAIN RUN LOOP ---
def main():
    # Load Metadata & Model
    try:
        with open("model_metadata.json", "r") as f:
            meta = json.load(f)
        model = RPSModel(meta["input_features"], meta["output_classes"])
        model.load_state_dict(torch.load("model.pth", map_location='cpu'))
        model.eval()
        print("Model Loaded Successfully")
    except Exception as e:
        print(f"Initialization Error: {e}")
        return

    pygame.init()
    screen = pygame.display.set_mode((1000, 700))
    pygame.display.set_caption("Glove Inference HUD")
    font = pygame.font.SysFont("Arial", 50, bold=True)
    small_font = pygame.font.SysFont("Arial", 18)

    window_buffer = deque(maxlen=WINDOW_SIZE)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Persistence State
    last_valid_gesture, last_valid_conf, last_seen_time = None, 0.0, 0

    try:
        ws = websocket.create_connection(PICO_URI, timeout=5)
        ws.recv() # Skip Header
        print("Connected to WebSocket")

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False

            raw_message = ws.recv()
            if not raw_message: continue

            try:
                full_data = [float(x) for x in raw_message.split(',')]
                filtered_sample = [full_data[i] for i in KEEP_INDICES]
                
                window_buffer.append(filtered_sample)
                if len(window_buffer) < WINDOW_SIZE: continue

                # Inference on means
                input_data = np.mean(np.array(window_buffer), axis=0)
                input_tensor = torch.tensor(input_data, dtype=torch.float32).unsqueeze(0).to(device)

                with torch.inference_mode():
                    logits = model(input_tensor)
                    probs = torch.softmax(logits, dim=1)
                    conf, pred_idx = torch.max(probs, dim=1)

                gesture_name = GESTURE_MAP.get(pred_idx.item(), "None")
                curr_conf = conf.item()
                now = time.time()

                # Persistence Logic
                is_holding = False
                if gesture_name.lower() != "none" and curr_conf > CONFIDENCE_THRESHOLD:
                    last_valid_gesture = gesture_name
                    last_valid_conf = curr_conf
                    last_seen_time = now
                elif last_valid_gesture and (now - last_seen_time < PERSISTENCE_DURATION):
                    is_holding = True
                else:
                    last_valid_gesture = None

                draw_hud(screen, font, small_font, last_valid_gesture, last_valid_conf, filtered_sample, is_holding)

            except Exception as e:
                print(f"Loop Error: {e}")
                continue

    except Exception as e:
        print(f"Connection Error: {e}")
    finally:
        pygame.quit()
        if 'ws' in locals(): ws.close()

if __name__ == "__main__":
    main()
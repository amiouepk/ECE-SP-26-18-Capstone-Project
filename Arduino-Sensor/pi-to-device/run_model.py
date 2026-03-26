import torch
import torch.nn as nn
import numpy as np
import __main__

# ==========================================
# 1. PASTE YOUR MODEL CLASS HERE
# ==========================================
# (Copy this exact block from your training script/notebook)
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
# ==========================================
# 2. THE "__MAIN__" FIX
# ==========================================
# This tells Python: "When the unpickler looks for SensorClassifier 
# in the main script, point it to the class defined right above."
__main__.SensorClassifier = SensorClassifier

# ==========================================
# 3. YOUR EXISTING FUNCTIONS
# ==========================================
def load_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading models to {device}...")

    # Load model
    model = torch.load("model.pth", map_location=device, weights_only=False)
    model.to(device)
    model.eval()

    # Load pre-processing objects
    scaler = torch.load("scaler.pt", weights_only=False)
    label_encoder = torch.load("encoder.pt", weights_only=False)

    return model, scaler, label_encoder, device

def predict_message(model, scaler, label_encoder, device, message):
    try:
        raw_values = [float(x) for x in message.strip().split(',')]
        input_array = np.array(raw_values).reshape(1, -1)
        scaled_array = scaler.transform(input_array)
        input_tensor = torch.tensor(scaled_array, dtype=torch.float32).to(device)

        with torch.no_grad():
            output = model(input_tensor)
            _, predicted_idx = torch.max(output, 1)
            prediction_label = label_encoder.inverse_transform([predicted_idx.cpu().numpy()[0]])[0]
            return prediction_label

    except ValueError as ve:
        print(f"Data parsing error: {ve}")
        return None
    except Exception as e:
        print(f"Inference error: {e}")
        return None
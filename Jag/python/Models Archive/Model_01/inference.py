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

def run_model():
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
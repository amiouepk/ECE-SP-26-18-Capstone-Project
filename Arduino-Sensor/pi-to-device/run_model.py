import torch
from torchvision import transforms
import torchvision.models as models
import cv2


def load_model():

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


    model = torch.load("../ML/model.pth", map_location=device,weights_only=False)
    model.to(device)
    model.eval()

    scaler = torch.load("../ML/scaler.pt", weights_only=False)
    encoder = torch.load("../ML/encoder.pt", weights_only=False)
    label_encoder = torch.load("../ML/encoder.pt", weights_only=False)

    return model, scaler, label_encoder, device

def input_model(model, message):


    with torch.no_grad():


    return


if __name__ == "__main__":




    pass
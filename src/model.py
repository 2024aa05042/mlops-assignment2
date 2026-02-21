import torch.nn as nn
import torchvision.models as models


def create_model(num_classes=2, pretrained=True):
    """Create a standard CNN backbone (ResNet18) for binary classification."""
    model = models.resnet18(pretrained=pretrained)
    in_feats = model.fc.in_features
    model.fc = nn.Linear(in_feats, num_classes)
    return model

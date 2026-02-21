import torch

from src.model import create_model


def test_create_model_forward_pass():
    # create model with 2 classes, without downloading pretrained weights
    model = create_model(num_classes=2, pretrained=False)
    model.eval()

    x = torch.randn(4, 3, 224, 224)
    with torch.no_grad():
        out = model(x)

    assert isinstance(out, torch.Tensor)
    assert out.shape == (4, 2)

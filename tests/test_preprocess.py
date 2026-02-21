import io
from PIL import Image
import torch

from src.api import _preprocess_image


def test_preprocess_image_returns_tensor_and_shape():
    # create a simple RGB image in memory
    img = Image.new("RGB", (300, 300), color=(123, 222, 64))
    bio = io.BytesIO()
    img.save(bio, format="JPEG")
    data = bio.getvalue()

    tensor = _preprocess_image(data, img_size=224)

    assert isinstance(tensor, torch.Tensor)
    # batch dim + 3 channels + H + W
    assert tensor.dim() == 4
    assert tensor.size(1) == 3
    assert tensor.size(2) == 224 and tensor.size(3) == 224
    assert tensor.dtype == torch.float32

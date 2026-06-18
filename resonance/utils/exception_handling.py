import time
from pathlib import Path

from resonance.device.device import input_tap, screenshot
from resonance.vision.ocr import predict

ROOT_PATH = Path()
IMAGE_PATH = ROOT_PATH / "logs" / "image"
IMAGE_PATH.mkdir(parents=True, exist_ok=True)


def save_error_screenshot():
    timestamp = int(time.time() * 1000)
    try:
        image = screenshot()
        image.save_image(IMAGE_PATH / f"{timestamp}.png")
        return timestamp
    except Exception:
        return None


def get_exception():
    image = screenshot()
    if not_strength(image):
        return "澄明度不足"
    if not_negotiate_price(image):
        return "议价次数不足"
    return ""


def get_excption():
    return get_exception()


def not_strength(image):
    image.crop_image((443, 315), (938, 400))
    data = predict(image.image)
    if not data:
        return False
    if "澄明度不足" in data[0]["text"]:
        input_tap((319, 512))
        return True
    return False


def not_negotiate_price(image):
    image = image.crop_image((459, 422), (816, 462))
    data = predict(image.image)
    if not data:
        return False
    if "重新议价" in data[0]["text"]:
        input_tap((319, 512))
        return True
    return False

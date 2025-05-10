import unicodedata
import re
import string
from PIL import Image

def clean_text(text: str):
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\s+', ' ', text)
    text = ''.join(c for c in text if c in string.printable)
    return text.strip()

def resize_image_if_needed(image_path: str, max_width: int = 800):
    image = Image.open(image_path)
    if image.width > max_width:
        ratio = max_width / image.width
        new_size = (max_width, int(image.height * ratio))
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        image = image.resize(new_size, resample)
        resized_path = image_path.replace('.jpg', '_resized.jpg').replace('.png', '_resized.png')
        image.save(resized_path)
        return resized_path
    return image_path

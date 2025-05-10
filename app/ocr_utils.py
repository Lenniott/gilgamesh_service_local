from PIL import Image, ImageEnhance, ImageFilter
import easyocr
import pytesseract
import unicodedata
import re
import string

EASYOCR_READER = easyocr.Reader(['en'], gpu=False)

def preprocess_image(image_path: str):
    image = Image.open(image_path).convert('L')
    image = image.filter(ImageFilter.MedianFilter())
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)
    return image

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

def ocr_image(image_path: str, reader=None):
    image_path = resize_image_if_needed(image_path)
    if reader is None:
        reader = EASYOCR_READER
    try:
        result = reader.readtext(image_path, detail=0)
        text = ' '.join(result)
        text = clean_text(text)
        if text.strip():
            return text
    except Exception as e:
        print(f"Warning: EasyOCR failed on {image_path}: {e}")
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, config='--psm 6')
    text = clean_text(text)
    if not text.strip():
        preprocessed = preprocess_image(image_path)
        debug_path = image_path.replace('.jpg', '_preprocessed.jpg').replace('.png', '_preprocessed.png')
        preprocessed.save(debug_path)
        text = pytesseract.image_to_string(preprocessed, config='--psm 6')
        text = clean_text(text)
    return text

"""Generate the official graphite NOMIKO multi-resolution Windows icon."""
from pathlib import Path
from PIL import Image, ImageDraw

def generate(directory='assets'):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((18, 18, 494, 494), radius=112, fill=(28, 30, 37, 255))
    d.rounded_rectangle((28, 28, 484, 484), radius=105, outline=(82, 86, 100, 255), width=4)
    d.polygon([(119, 367), (119, 147), (177, 147), (177, 367)], fill=(230, 233, 244, 255))
    d.polygon([(177, 147), (323, 367), (269, 367), (119, 147)], fill=(209, 215, 233, 255))
    d.polygon([(324, 367), (324, 147), (385, 147), (385, 367)], fill=(230, 233, 244, 255))
    d.rounded_rectangle((334, 101, 393, 128), radius=13, fill=(166, 143, 255, 255))
    d.rounded_rectangle((42, 42, 470, 470), radius=90, outline=(47, 49, 60, 255), width=2)
    image.save(root / 'NOMIKO.ico', format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    image.resize((256,256), Image.Resampling.LANCZOS).save(root / 'NOMIKO.png')

if __name__ == '__main__':
    generate()

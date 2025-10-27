from PIL import Image

# Abre a imagem
img = Image.open("data/layer_12.png")

print(img.format, img.size, img.mode)

print(img.info.keys())

print(img.info)

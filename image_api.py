from flask import Flask, request, jsonify
from PIL import Image, ImageChops
import base64
import io

app = Flask(__name__)

def trim_white_borders(im: Image.Image, threshold: int = 240) -> Image.Image:
    """Remove bordas brancas da imagem com um limiar definido."""
    gray_im = im.convert("L")
    bin_im = gray_im.point(lambda p: 255 if p > threshold else p)
    inverted_im = ImageChops.invert(bin_im)
    bbox = inverted_im.getbbox()
    return im.crop(bbox) if bbox else im

def format_image(img: Image.Image, final_size: tuple[int, int] = (1200, 1200), threshold: int = 240) -> Image.Image:
    """Formata uma imagem para quadrado, remove bordas brancas e redimensiona."""

    # Trata transparência (PNG com canal alpha)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    else:
        img = img.convert("RGB")

    # 1) Corta bordas brancas
    img = trim_white_borders(img, threshold=threshold)

    img_width, img_height = img.size
    aspect_ratio = img_width / img_height

    # Verifica se é muito horizontal ou vertical; rotaciona para melhor centralização
    if aspect_ratio > 2:
        img = img.rotate(-45, expand=True, fillcolor="white")
        img = trim_white_borders(img, threshold=threshold)
        img_width, img_height = img.size
    elif aspect_ratio < 0.5:
        img = img.rotate(45, expand=True, fillcolor="white")
        img = trim_white_borders(img, threshold=threshold)
        img_width, img_height = img.size

    # Cria canvas quadrado mantendo o centro
    if img_width > img_height:
        new_size = (img_width, img_width)
        offset = (0, (img_width - img_height) // 2)
    else:
        new_size = (img_height, img_height)
        offset = ((img_height - img_width) // 2, 0)

    new_img = Image.new("RGB", new_size, "white")
    new_img.paste(img, offset)

    # Redimensiona para o tamanho final
    return new_img.resize(final_size, Image.LANCZOS)


@app.route("/format_image", methods=["POST"])
def format_image_endpoint():
    """Endpoint que recebe base64 PNG, devolve base64 WEBP formatado."""
    try:
        # Recupera dados do JSON
        data = request.get_json(force=True)
        if not data or "image_base64" not in data:
            return jsonify(error="'image_base64' é obrigatório"), 400

        image_base64_str = data["image_base64"]
        threshold = data.get("threshold", 240)

        # Decodifica base64 para bytes
        image_bytes = base64.b64decode(image_base64_str)
        img = Image.open(io.BytesIO(image_bytes))

        # Formata a imagem
        formatted_img = format_image(img, threshold=threshold)

        # Salva em memória no formato WebP
        buffer = io.BytesIO()
        formatted_img.save(buffer, format="WEBP")
        buffer.seek(0)

        # Codifica de volta para base64
        formatted_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        return jsonify(formatted_image_base64=formatted_base64)

    except Exception as e:
        return jsonify(error=str(e)), 400


# Permite executar diretamente: python image_api.py
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000) 
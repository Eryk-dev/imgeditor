from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image, ImageChops
import base64
import io

app = FastAPI(
    title="Image Formatter API",
    description="Recebe uma imagem em base64, formata para 1200x1200 (WebP) e devolve em base64.",
    version="1.0.0",
)

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


class ImageRequest(BaseModel):
    image_base64: str
    threshold: int | None = 240  # Permite ajustar o limiar opcionalmente

class ImageResponse(BaseModel):
    formatted_image_base64: str


@app.post("/format_image", response_model=ImageResponse)
async def format_image_endpoint(request: ImageRequest):
    """Endpoint que recebe base64 PNG, devolve base64 WEBP formatado."""
    try:
        # Decodifica base64 para bytes
        image_bytes = base64.b64decode(request.image_base64)
        img = Image.open(io.BytesIO(image_bytes))

        # Formata a imagem
        formatted_img = format_image(img, threshold=request.threshold or 240)

        # Salva em memória no formato WebP
        buffer = io.BytesIO()
        formatted_img.save(buffer, format="WEBP")
        buffer.seek(0)

        # Codifica de volta para base64
        formatted_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        return {"formatted_image_base64": formatted_base64}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 
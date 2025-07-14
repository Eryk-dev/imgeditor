from PIL import Image, ImageChops
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

def trim_white_borders(im, threshold=240):
    gray_im = im.convert('L')
    bin_im = gray_im.point(lambda p: 255 if p > threshold else p)
    inverted_im = ImageChops.invert(bin_im)
    bbox = inverted_im.getbbox()
    if bbox:
        return im.crop(bbox)
    else:
        return im

def make_square_and_resize(image_path, output_folder, final_size=(1200, 1200)):
    try:
        img = Image.open(image_path)

        # Verifica se a imagem é PNG com transparência
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            # Cria nova imagem branca e cola a original por cima
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  
            img = background
        else:
            img = img.convert('RGB')

        # 1) Corta margens brancas antes de qualquer outra operação
        img = trim_white_borders(img, threshold=240)

        # Obtém as dimensões da imagem
        img_width, img_height = img.size
        aspect_ratio = img_width / img_height

        # Verifica se é muito horizontal ou muito vertical
        if aspect_ratio > 2:
            # Rotaciona para tentar centralizar melhor
            img = img.rotate(-45, expand=True, fillcolor='white')
            # 2) Corta novamente após rotação
            img = trim_white_borders(img, threshold=240)
            img_width, img_height = img.size
        elif aspect_ratio < 0.5:
            img = img.rotate(45, expand=True, fillcolor='white')
            # 2) Corta novamente após rotação
            img = trim_white_borders(img, threshold=240)
            img_width, img_height = img.size

        # Agora, cria um quadrado, mantendo o produto no centro
        if img_width > img_height:
            new_size = (img_width, img_width)
            offset = (0, (img_width - img_height) // 2)
        else:
            new_size = (img_height, img_height)
            offset = ((img_height - img_width) // 2, 0)

        # Cria um canvas quadrado branco
        new_img = Image.new("RGB", new_size, "white")
        new_img.paste(img, offset)

        # Redimensiona para o tamanho final
        new_img = new_img.resize(final_size, Image.LANCZOS)

        # Salva em WebP
        formatted_image_path = os.path.join(
            output_folder,
            f"{os.path.splitext(os.path.basename(image_path))[0]}_formatted.webp"
        )
        new_img.save(formatted_image_path, 'WEBP')

        print(f"Imagem formatada salva em: {formatted_image_path}")
        return formatted_image_path

    except Exception as e:
        print(f"Erro ao formatar a imagem {image_path}: {e}")
        return None

def process_images_in_directory(input_directory, output_directory, final_size=(1200, 1200), max_workers=None):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.heic', '.avif')
    image_paths = []

    # Coleta apenas as imagens da pasta principal
    for file in os.listdir(input_directory):
        if file.lower().endswith(image_extensions):
            image_path = os.path.join(input_directory, file)
            image_paths.append(image_path)

    total_images = len(image_paths)
    print(f"Total de imagens a processar: {total_images}")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_image = {
            executor.submit(make_square_and_resize, image_path, output_directory, final_size): image_path
            for image_path in image_paths
        }
        with tqdm(total=total_images, desc="Processando Imagens", unit="imagem") as pbar:
            for future in as_completed(future_to_image):
                image_path = future_to_image[future]
                try:
                    result = future.result()
                    if result:
                        pass
                except Exception as exc:
                    print(f"Imagem {image_path} gerou uma exceção: {exc}")
                finally:
                    pbar.update(1)

if __name__ == "__main__":
    directories = [
        '/Users/eryk/Documents/141Air/Fotos/Técnicas manbrape prontas',
        '/Users/eryk/Documents/141Air/Fotos/Técnicas royce prontas'
    ]
    
    for input_directory in directories:
        print(f"\n==> Processando pasta: {input_directory}")
        process_images_in_directory(input_directory, input_directory, max_workers=2)
        print(f"==> Concluído: {input_directory}")
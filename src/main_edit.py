from config.config import config
from glob import glob
from natsort import os_sorted
import os
import shutil
import numpy as np
from pdf2image import convert_from_path
from PIL import Image

from rotator import main as rotate
from utils import is_scanned_pdf, count_pages, clear_pdf_waste_pages
from utils import rename_files_in_directory
from crop_tables import get_table_coords, crop_goods_table


def main():
    """ take all files in IN_FOLDER, preprocess, extract additional and save to IN_FOLDER_EDIT"""

    rename_files_in_directory(config['IN_FOLDER'])

    # collect files
    files, extensions = [], ['.pdf', '.jpeg', '.jpg', '.png']
    for ext in extensions:
        files.extend(glob(os.path.join(config['IN_FOLDER'], f'*{ext}')))

    # preprocess and copy to "edited"
    for file in os_sorted(files):
        file_type = os.path.splitext(file)[1]
        file_name = os.path.basename(file).rsplit('.', 1)[0]

        # if digital pdf
        if (file_type.lower() == '.pdf') and (is_scanned_pdf(file) is False):
            if count_pages(file) > 7:
                print(f'page limit exceeded in {file}')
                continue
            cleared_pdf = clear_pdf_waste_pages(file)
            save_path = os.path.join(config['IN_FOLDER_EDIT'], file_name + f'_{file_type.replace(".", "")}' + '.pdf')
            with open(save_path, 'wb') as f:
                cleared_pdf.write(f)

        # if file is image, or file is scanned pdf
        else:
            # if file is scanned pdf -> get first 3! pages in jpg
            if file_type.lower() == '.pdf':
                # image = np.array(convert_from_path(file, first_page=0, last_page=1,
                #                                    fmt='jpg', poppler_path=config["POPPLER_PATH"])[0])
                images = convert_from_path(file, first_page=0, last_page=3, fmt='jpg', jpegopt={"quality": 100},
                                           poppler_path=config["POPPLER_PATH"])
                images = list(map(lambda x: np.array(x), images))
            # if file is image
            elif file_type.lower() in ['.jpg', '.jpeg', '.png']:
                images = [np.array(Image.open(file))]
            else:
                print(f'ERROR IN: {file}')
                continue

            # добавляем зумированное изображение в случае одностраничного документа
            prefix = ''
            if len(images) == 1:
                image = images[0]
                rotated = Image.fromarray(rotate(image))
                table_coords = get_table_coords(rotated)
                cropped = crop_goods_table(rotated, table_coords)
                images = [rotated, cropped]
                prefix = 'zoom'

            for i, image in enumerate(images):
                rotated = Image.fromarray(rotate(image))
                if i == 0:  # оригинальный файл или первая страница записывается без префиксов
                    save_path = os.path.join(config['IN_FOLDER_EDIT'],
                                             file_name + f'_{file_type.replace(".", "")}' + '.jpg')
                else:  # далее добавляются префиксы
                    save_path = os.path.join(config['IN_FOLDER_EDIT'],
                                             file_name + f'_{file_type.replace(".", "")}_{prefix}{i}' + '.jpg')
                if rotated.mode == "RGBA":
                    rotated = rotated.convert('RGB')
                rotated.save(save_path, quality=100)

                command = f'magick convert {save_path} {config["magick_opt"]} {save_path}'
                os.system(command)
                print(save_path)

    print(f"\nФайлы сохранены в {config['IN_FOLDER_EDIT']}\n")


if __name__ == '__main__':
    main()
    # z = os.path.join(os.path.dirname(__file__), '..', 'data', '620.jpg')
    # z = r'C:\Users\Filipp\PycharmProjects\Invoice_scanner\IN\edited\620.jpg'
    # print(os.path.splitext(z)[0]+'_tab')
    # print(os.path.split(z))

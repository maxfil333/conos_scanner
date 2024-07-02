import os
import shutil
import subprocess
import numpy as np
from glob import glob
from PIL import Image
from itertools import count
from natsort import os_sorted
from pdf2image import convert_from_path

from config.config import config
from rotator import main as rotate
from utils import rename_files_in_directory
from crop_tables import get_table_coords, crop_goods_table
from utils import is_scanned_pdf, count_pages, clear_pdf_waste_pages


def main(hide_logs=False, stop_when=-1):
    """ take all files in IN_FOLDER, preprocess, extract additional and save to IN_FOLDER_EDIT"""

    rename_files_in_directory(config['IN_FOLDER'], hide_logs=hide_logs)

    # collect files
    files, extensions = [], ['.pdf', '.jpeg', '.jpg', '.png']
    for ext in extensions:
        files.extend(glob(os.path.join(config['IN_FOLDER'], f'*{ext}')))

    # preprocess and copy to "edited"
    c = count(1)
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
                if prefix == 'zoom':  # rotate уже выполнено
                    rotated = image
                else:
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

                command = [config["magick_exe"], "convert", save_path, *config["magick_opt"], save_path]
                subprocess.run(command)
                print(save_path)

        # _____  STOP ITERATION  _____
        if stop_when > 0:
            stop = next(c)
            if stop == stop_when:
                break

    print(f"\nФайлы сохранены в {config['IN_FOLDER_EDIT']}\n")


if __name__ == '__main__':
    main()


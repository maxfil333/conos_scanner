import os
import glob
import json
import fitz
import shutil
import traceback
import subprocess
import numpy as np
from PIL import Image
from itertools import count
from pdf2image import convert_from_path

from config.config import config
from src.logger import logger
from src.utils import delete_all_files, rename_files_in_directory, filtering_and_foldering_files
from src.utils import is_scanned_pdf, count_pages, clear_pdf_waste_pages, image_upstanding_and_rotate


def main(dir_path: str = config['IN_FOLDER'], hide_logs=False, stop_when=-1):
    """ for folder in dir_path(IN), creates folder in EDITED, preprocess, extract additional and save to this folder """

    # очистка EDITED
    delete_all_files(config['EDITED'])
    # переименование файлов и папок
    rename_files_in_directory(dir_path, hide_logs=hide_logs)
    # упаковка одиночных файлов в папки
    filtering_and_foldering_files(dir_path)

    c = count(1)

    for folder_ in os.scandir(dir_path):
        if not os.path.isdir(folder_):  # folder_ это не папка -> пропускаем
            continue
        if not os.listdir(folder_):  # если пустая папка -> пропускам
            continue
        folder, folder_name = folder_.path, folder_.name
        valid_types = config['valid_ext'] + config['excel_ext']
        valid_files = [x for x in glob.glob(f"{folder}/*")
                       if not os.path.isdir(x) and os.path.splitext(x)[-1] in valid_types]
        if not valid_files:  # если нет ни одного файла с валидным расширением -> пропускам
            continue
        main_file = valid_files[0]  # берем любой (первый) файл
        main_base = os.path.basename(main_file)
        main_type = os.path.splitext(main_file)[-1]
        print('main_file:', main_file)

        edited_folder = os.path.join(config['EDITED'], folder_name)
        main_save_path = os.path.join(edited_folder, main_base)
        os.makedirs(edited_folder, exist_ok=False)
        main_local_files = []  # список главных изображений (без _TAB1, _TAB2);
        # Если scannedPDF + required_pages, то len(main_local_files) может быть > 1

        try:
            # if digital pdf
            if (main_type.lower() == '.pdf') and (is_scanned_pdf(main_file) is False):
                print('file type: digital')
                if count_pages(main_file) > 7:
                    logger.print(f'page limit exceeded in {main_file}')
                    continue
                cleared_pdf_bytes = clear_pdf_waste_pages(main_file)
                fitz.open("pdf", cleared_pdf_bytes).save(main_save_path)
                # align_pdf_orientation(cleared_pdf_bytes, main_save_path)

            # if file is (image | scanned pdf)
            else:
                images = []

                if main_type.lower() == '.pdf':
                    print('file type: scanned pdf')

                    # get first 3 pages
                    images = convert_from_path(main_file, first_page=0, last_page=3, fmt='jpg',
                                               jpegopt={"quality": 100},
                                               poppler_path=config["POPPLER_PATH"])
                    images = list(map(lambda x: np.array(x), images))

                elif main_type.lower() in ['.jpg', '.jpeg', '.png']:
                    images = [np.array(Image.open(main_file))]

                elif main_type.lower() in config['excel_ext']:
                    shutil.copy(main_file, main_save_path)
                else:
                    logger.print(f'main edit. ERROR IN: {main_file}')
                    continue

                for i, image in enumerate(images):
                    rotated = image_upstanding_and_rotate(image)
                    name, ext = os.path.splitext(main_save_path)
                    idx_save_path = f'{name}({i}).jpg'
                    rotated.save(idx_save_path, quality=100)
                    main_local_files.append(idx_save_path)

                    command = [config["magick_exe"], "convert", idx_save_path, *config["magick_opt"], idx_save_path]
                    subprocess.run(command)

            with open(os.path.join(edited_folder, 'params.json'), 'w', encoding='utf-8') as f:
                params_dict = {"main_file": main_file}
                json.dump(params_dict, f, ensure_ascii=False, indent=4)
        except:
            logger.print("ERROR IN MAIN_EDIT:", traceback.format_exc(), sep='\n')

        print('------------------------------')
        # _____  STOP ITERATION  _____
        if stop_when > 0:
            stop = next(c)
            if stop == stop_when:
                break


if __name__ == '__main__':
    main()

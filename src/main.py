import os
import sys
import time
import json
import shutil
import msvcrt
import argparse
import traceback
from glob import glob
from itertools import count
from natsort import os_sorted
from openai import PermissionDeniedError

from config.config import config, running_params, NAMES
from src.logger import logger
from src.main_edit import main as main_edit
from src.utils_openai import pdf_to_ai, excel_to_ai, images_to_ai
from src.generate_html import create_html_form
from src.utils import create_date_folder_in_check
from src.utils import convert_json_values_to_strings
from src.response_postprocessing import local_postprocessing


def main(date_folder: str,
         hide_logs: bool = False,
         test_mode: bool = False,
         use_existing: bool = False,
         text_to_assistant: bool = False,
         stop_when: int = 0):
    """
    :param date_folder: folder for saving results
    :param hide_logs: run without logs
    :param test_mode: run without main_openai using "config/__test.json"
    :param use_existing: run without main_edit using files in "IN/edited" folder
    :param text_to_assistant: do not use OCR to extract text from digital pdf, use loading pdf to assistant instead
    :param stop_when: stop script after N files
    :return:
    """

    # _______ CONNECTION ________
    connection = 'http'

    # _____  FILL IN_FOLDER_EDIT  _____
    if not use_existing:
        main_edit(hide_logs=hide_logs, stop_when=stop_when)

    c, stop = count(1), 0
    for folder_ in os.scandir(config['EDITED']):
        folder, folder_name = folder_.path, folder_.name

        files = os_sorted(glob(f"{folder}/*.*"))
        files = [file for file in files if os.path.splitext(file)[-1] in config['valid_ext'] + config['excel_ext']]

        with open(os.path.join(folder, 'params.json'), 'r', encoding='utf-8') as f:
            params_dict = json.load(f)
            original_file: str = params_dict['main_file']

        try:
            # _____  CREATE JSON  _____
            logger.print('-' * 30)
            logger.print('\nedited.folder:', folder, sep='\n')
            logger.print('edited.files:', *files, sep='\n')
            json_name = folder_name + '_' + '0' * 11 + '.json'

            # _____________ RUN MAIN_OPENAI.PY _____________
            if os.path.splitext(files[0])[-1].lower() == '.pdf':  # достаточно проверить 1-й файл, чтобы определить .ext
                pdf_file = files[0]
                result = pdf_to_ai(pdf_file, test_mode, text_to_assistant, config, running_params)
            elif os.path.splitext(files[0])[-1].lower() in config['excel_ext']:
                excel_file = files[0]
                result = excel_to_ai(excel_file, test_mode, text_to_assistant, config, running_params)
            else:
                result = images_to_ai(files, test_mode, text_to_assistant, config, running_params)

            # _____________________ LOGS _____________________
            logger.print('openai result:\n', repr(result))
            with open(os.path.join(config['CONFIG'], 'openai_response_log.json'), 'w', encoding='utf-8') as f:
                json.dump(json.loads(result), f, ensure_ascii=False, indent=4)

            # _____________ LOCAL POSTPROCESSING _____________
            result = local_postprocessing(result)

            if result is None:
                continue

            # _____________ CONVERT VALUES TO STRING _____________
            result = json.dumps(convert_json_values_to_strings(json.loads(result)), ensure_ascii=False, indent=4)

            # _____ * SAVE JSON FILE * _____
            local_check_folder: str = os.path.join(date_folder, running_params['text_or_scanned_folder'], folder_name)
            os.makedirs(local_check_folder, exist_ok=False)
            json_path = os.path.join(date_folder, config['NAME_verified'], json_name)
            with open(json_path, 'w', encoding='utf-8') as file:
                file.write(result)

            # _____ * COPY ORIGINAL FILE * _____
            shutil.copy(original_file, os.path.join(local_check_folder, os.path.basename(original_file)))

            # _____ * CREATE HTML FILE * _____
            html_name = os.path.basename(local_check_folder) + '.html'
            html_path = os.path.join(local_check_folder, html_name)
            create_html_form(json_path, html_path, original_file)

            # _____ clear temp variable running_params _____
            running_params.clear()

            # _____  STOP ITERATION  _____
            stop = next(c)
            if stop_when > 0:
                if stop == stop_when:
                    break

        except PermissionDeniedError:
            raise
        except Exception as error:
            logger.print('ERROR!:', error)
            logger.print(traceback.format_exc())
            continue

    # _____  RESULT MESSAGE  _____
    return (f'Обработано счетов: {stop}'
            f'\n{date_folder}')


if __name__ == "__main__":
    logger.print("CONFIG INFO:")
    logger.print('sys._MEIPASS:', hasattr(sys, '_MEIPASS'))
    logger.print(f'POPPLER_RPATH = {config["POPPLER_PATH"]}')
    logger.print(f'magick_exe = {config["magick_exe"]}')
    logger.print(f'magick_opt = {config["magick_opt"]}')

    parser = argparse.ArgumentParser(description="DESCRIPTION: Invoice Scanner")
    parser.add_argument('--hide_logs', action='store_true', help='Скрыть логи')
    parser.add_argument('--test_mode', action='store_true', help='Режим тестирования')
    parser.add_argument('--use_existing', action='store_true', help='Использовать существующие файлы')
    parser.add_argument('--text_to_assistant', action='store_true', help='Обрабатывать цифровые pdf ассистентом')
    parser.add_argument('--no_exit', action='store_true', help='Не закрывать окно')
    parser.add_argument('--stop_when', type=int, default=-1, help='Максимальное количество файлов')
    args = parser.parse_args()
    logger.print(args, end='\n\n')

    date_folder = create_date_folder_in_check(config['CHECK_FOLDER'])
    try:
        result_message = main(date_folder=date_folder,
                              hide_logs=args.hide_logs,
                              test_mode=args.test_mode,
                              use_existing=args.use_existing,
                              text_to_assistant=args.text_to_assistant,
                              stop_when=args.stop_when)
        logger.print(f'\n{result_message}\n')
    except PermissionDeniedError:
        logger.print(traceback.format_exc())
        logger.print('ОШИБКА ВЫПОЛНЕНИЯ:\n!!! Включите VPN !!!')
    except Exception as global_error:
        logger.print('GLOBAL_ERROR!:', global_error)
        logger.print(traceback.format_exc())

    if getattr(sys, 'frozen', False):
        if args.no_exit:
            msvcrt.getch()
        else:
            logger.print('Завершено. Выполняется закрытие...')

    logger.save(date_folder)
    time.sleep(3)

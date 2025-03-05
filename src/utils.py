import os
import re
import io
import fitz
import json
import glob
import shutil
import base64
import PyPDF2
import openai
import hashlib
import pytesseract
import numpy as np
import pandas as pd
from openai import OpenAI
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from io import BytesIO, StringIO
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

from config.config import config
from src.logger import logger
from src.utils_config import get_stream_dotenv
from src.rotator import main as custom_rotate


# _____________________________________________________________________________________________________________ ENCODERS

# Function to encode the image
def base64_encode_image(image_path: str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def base64_encode_pil(image: Image.Image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def calculate_hash(file_path):
    # Инициализация хэш-объекта MD5
    md5_hash = hashlib.md5()

    # Открываем файл в бинарном режиме для чтения
    with open(file_path, "rb") as f:
        # Чтение файла блоками по 4096 байт (можно настроить)
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)

    # Возвращаем хэш-сумму в виде шестнадцатеричной строки
    return md5_hash.hexdigest()


# _______________________________________________________________________________________________________________ COMMON


def group_files_by_name(file_list: list[str]) -> dict:
    groups = defaultdict(list)
    pattern = re.compile(r'^(.*?)(?:_TAB\d+\+)?\.(\w{3,4})$')
    for file_name in file_list:
        match = pattern.match(file_name)
        if match:
            basename = match.group(1)
            extension = match.group(2).lower()
            groups[basename, extension].append(file_name)
        else:
            groups[file_name].append(file_name)
    return groups


def convert_json_values_to_strings(obj) -> dict | list | str:
    if isinstance(obj, dict):
        return {k: convert_json_values_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_json_values_to_strings(i) for i in obj]
    elif obj is None:
        return ""
    else:
        return str(obj)


def handling_openai_json(response: str, hide_logs=False) -> str | None:
    # удаление двойных пробелов и переносов строк
    re_response = re.sub(r'(\s{2,}|\n)', ' ', response)

    # проверка на json-формат
    try:
        json.loads(re_response)
        if not hide_logs:
            logger.print('RECOGNIZED: JSON')
        return re_response
    except json.decoder.JSONDecodeError:
        # поиск ```json (RESPONSE)```
        json_response = re.findall(r'```\s?json\s?(.*)```', re_response, flags=re.DOTALL | re.IGNORECASE)
        if json_response:
            if not hide_logs:
                logger.print('RECOGNIZED: ``` json... ```')
            return json_response[0]
        else:
            # поиск текста в {}
            figure_response = re.findall(r'{.*}', re_response, flags=re.DOTALL | re.IGNORECASE)
            if figure_response:
                if not hide_logs:
                    logger.print('RECOGNIZED: {...}')
                return figure_response[0]
            else:
                logger.print('NOT RECOGNIZED JSON')
                return None


# _________________________________________________________________________________________________________________ TEXT

def replace_symbols_with_latin(match_obj):
    """ Замена кириллических символов на латиницу """

    text = match_obj.group(0)
    cyrillic_to_latin = {
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y',
        'Х': 'X'
    }
    result = ''
    for char in text:
        if char in cyrillic_to_latin:
            result += cyrillic_to_latin[char]
        else:
            result += char
    return result


def replace_container_with_latin(text, container_regex):
    """ Замена в тексте контейнеров на контейнеры латиницей """

    return re.sub(pattern=container_regex,
                  repl=replace_symbols_with_latin,
                  string=text)


def replace_container_with_none(text, container_regex):
    """ Замена в тексте контейнеров на контейнеры латиницей """

    return re.sub(pattern=container_regex,
                  repl='',
                  string=text)


def switch_to_latin(s: str, reverse: bool = False) -> str:
    cyrillic_to_latin = {'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C',
                         'Т': 'T', 'У': 'Y', 'Х': 'X'}
    latin_to_cyrillic = {'A': 'А', 'B': 'В', 'E': 'Е', 'K': 'К', 'M': 'М', 'H': 'Н', 'O': 'О', 'P': 'Р', 'C': 'С',
                         'T': 'Т', 'Y': 'У', 'X': 'Х'}
    new = ''
    if not reverse:
        for letter in s:
            if letter in cyrillic_to_latin:
                new += cyrillic_to_latin[letter]
            else:
                new += letter
    else:
        for letter in s:
            if letter in latin_to_cyrillic:
                new += latin_to_cyrillic[letter]
            else:
                new += letter
    return new


# ______________________________________________________________________________________________________________ FOLDERS

def rename_files_in_directory(directory_path: str, max_len: int = 45, hide_logs: bool = False) -> None:
    def get_unique_filename(filepath):
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(f"{base}({counter}){ext}"):
            counter += 1
        return f"{base}({counter}){ext}"

    def sanitize_filename(filename: str) -> str:
        # Заменяем все недопустимые символы на пробелы
        sanitized = re.sub(r'[<>/\"\\|?*#]', ' ', filename)
        # Убираем пробелы в начале и конце строки
        sanitized = sanitized.strip()
        # Заменяем пробелы на "_"
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized

    def crop_filename(filename: str, max_len: int) -> str:
        base, ext = os.path.splitext(filename)
        base = base[-max_len:]
        return base + ext

    def lower_extension(filename: str) -> str:
        base, ext = os.path.splitext(filename)
        return base + ext.lower()

    for filename in os.listdir(directory_path):
        # если путь - директория
        if os.path.isdir(os.path.join(directory_path, filename)):
            rename_files_in_directory(os.path.join(directory_path, filename))

        new_filename = sanitize_filename(filename)
        new_filename = crop_filename(new_filename, max_len=max_len)
        new_filename = lower_extension(new_filename)

        old_filepath = os.path.join(directory_path, filename)
        new_filepath = os.path.join(directory_path, new_filename)
        try:
            os.rename(old_filepath, new_filepath)
        except FileExistsError:
            new_filepath = get_unique_filename(new_filepath)
            os.rename(old_filepath, new_filepath)

        if not hide_logs and old_filepath != new_filepath:
            logger.print(f"Файл '{filename}'переименован в '{new_filename}'")


def delete_all_files(dir_path: str):
    for folder_ in os.scandir(dir_path):
        if folder_.is_dir():
            shutil.rmtree(folder_.path)
        else:
            os.remove(folder_.path)


def create_date_folder_in_check(root_dir):
    """Создать внутри в указанной директории папку с текущей датой-временем и 3 подпапки"""

    # Создаем строку с текущей датой и временем
    folder_name = datetime.now().strftime("%d-%m-%Y___%H-%M-%S")
    # Создаем папку с указанным именем
    folder_path = os.path.join(root_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    # Создаем подпапки
    subfolders = [config['NAME_scanned'], config['NAME_text'], config['NAME_verified']]
    for subfolder in subfolders:
        subfolder_path = os.path.join(folder_path, subfolder)
        os.makedirs(subfolder_path, exist_ok=True)
    return folder_path


def extract_excel_text(file_path: str) -> str:
    """Читает первую страницу Excel-файла (счет на оплату) и преобразует данные в текст."""
    file_ext = os.path.splitext(file_path)[-1]
    if file_ext in ['.xlsx', '.xltx']:
        df = pd.read_excel(file_path, sheet_name=0, header=None, engine='openpyxl')  # Читаем без заголовков
    else:
        df = pd.read_excel(file_path, sheet_name=0, header=None, engine='xlrd')  # Читаем без заголовков

    raw_lines = []  # Список всех строк без удаления пустых
    table_start = None  # Индекс начала таблицы

    # Перебираем строки, сохраняя пустые строки для корректного индекса
    for i, row in df.iterrows():
        row_values = [str(cell).strip() if pd.notna(cell) else "" for cell in row]  # Оставляем пустые ячейки
        text_line = " | ".join(row_values).strip(" |")  # Убираем лишние разделители
        raw_lines.append(text_line)

    # Определяем начало таблицы – ищем первую строку, содержащую числа (например, цену, количество)
    for i, row in enumerate(df.itertuples(index=False, name=None)):
        row_values = [str(cell).strip() if pd.notna(cell) else "" for cell in row]
        if any(cell.replace('.', '', 1).isdigit() for cell in row_values if cell):  # Проверяем, есть ли числа
            if len(list(filter(bool, row_values))) >= 5:
                table_start = i
                break

    # Разделяем "Шапку" и "Товары/услуги"
    if table_start is not None:
        header_text = "\n".join(raw_lines[:table_start]).strip()
        table_text = "\n".join(raw_lines[table_start:]).strip()
        formatted_text = f"*****\n{header_text}\n\n*****\n{table_text}"
    else:
        z = '\n'.join(raw_lines)
        formatted_text = f"*****\n\n{z}"

    return formatted_text


def count_extensions(folder: Optional[str] = None, files: Optional[list[str]] = None) -> Optional[dict]:
    """ returns {'.xls': 4, '.pdf': 1, '.xlsx': 12} like dict """
    extensions = {}

    if folder:
        files = glob.glob(fr"{folder}/*")
    elif files:
        files = files
    else:
        return None

    for file in files:
        if not os.path.isdir(file):
            ext = os.path.splitext(file)[-1]
            extensions[ext] = extensions.setdefault(ext, 0) + 1
    return extensions


# _______________________________________________________________________________________________________________ IMAGES

def add_text_bar(image: str | Image.Image, text, h=75, font_path='verdana.ttf', font_size=50):
    # Открыть изображение
    if isinstance(image, Image.Image):
        pass
    else:
        image = Image.open(image)

    width, height = image.size

    # Создать новое изображение с дополнительной высотой h
    new_image = Image.new('RGB', (width, height + h), (255, 255, 255))
    new_image.paste(image, (0, h))

    # Создать объект для рисования
    draw = ImageDraw.Draw(new_image)

    # Загрузить шрифт
    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load_default()

    # Определить размер текста с помощью textbbox
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Определить позицию текста по центру полоски
    text_x = (width - text_width) // 2
    text_y = (h - text_height) // 2

    # Добавить текст на полоску
    draw.text((text_x, text_y), text, fill=(0, 0, 0), font=font)

    return new_image


def crop_center(image):
    img_w, img_h = image.width, image.height
    x1, x2 = 0, img_w
    y1, y2 = img_h * 0.25, img_h * 0.75
    return image.crop((x1, y1, x2, y2))


def image_upstanding(img: np.ndarray) -> np.ndarray:
    """ Приведение изображений в вертикальное положение с помощью tesseract"""

    pil_img = Image.fromarray(img)
    osd = pytesseract.image_to_osd(pil_img)
    rotation = int(osd.split("\n")[2].split(":")[1].strip())
    confidence = float(osd.split("\n")[3].split(":")[1].strip())
    # logger.print('rotation:', rotation, 'confidence:', confidence)
    if confidence > 3:
        return np.array(pil_img.rotate(-rotation, expand=True))
    return img


def image_upstanding_and_rotate(image: np.ndarray) -> Image.Image:
    try:
        upstanding = image_upstanding(image)  # 0-90-180-270 rotate
    except:
        upstanding = image
    try:
        rotated = custom_rotate(upstanding)  # accurate rotate
    except:
        rotated = upstanding
    rotated = Image.fromarray(rotated)
    if rotated.mode == "RGBA":
        rotated = rotated.convert('RGB')
    return rotated

# __________________________________________________________________________________________________________________ PDF

def is_scanned_pdf(file_path, pages_to_analyse=None) -> Optional[bool]:
    try:
        # Открытие PDF файла
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            if pages_to_analyse:
                pages = list(map(lambda x: x - 1, pages_to_analyse))
            else:
                pages = list(range(num_pages))

            # Проверка текста на каждой странице
            scan_list, digit_list = [], []
            for page_num in pages:
                page = reader.pages[page_num]
                text = page.extract_text()
                if text.strip() and len(text.strip()) > 30:
                    digit_list.append(page_num)  # Если текст найден
                else:
                    scan_list.append(page_num)  # Если текст не найден

            if not scan_list:
                return False
            elif not digit_list:
                return True
            else:
                logger.print(f'! utils.is_scanned_pdf: mixed pages types in {file_path} !')
                return 0 in scan_list  # определяем по первой странице

    except Exception as e:
        logger.print(f"Error reading PDF file: {e}")
        return None


def count_pages(file_path):
    try:
        # Открытие PDF файла
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return len(reader.pages)

    except Exception as e:
        logger.print(f"Error reading PDF file: {e}")
        return None


def extract_text_with_fitz(pdf_path) -> list[str]:
    """ return list of texts for every page """

    document = fitz.open(pdf_path)
    texts = []
    for page_num in range(len(document)):
        page = document.load_page(page_num)  # загружаем страницу
        texts.append(page.get_text())  # извлекаем текст
    return texts


def align_pdf_orientation(input_file: str | bytes, output_pdf_path: str) -> None:
    """ get input_pdf_path - save to output_pdf_path - returns None """

    if isinstance(input_file, bytes):
        pdf_document = fitz.open("pdf", input_file)
    elif isinstance(input_file, str):
        pdf_document = fitz.open(input_file)
    else:
        print(f'!! align_pdf_orientation input: {input_file} is not valid !!')
        return

    for page_number in range(len(pdf_document)):
        page = pdf_document[page_number]
        # Извлекаем текст со страницы
        text = page.get_text("text")
        # Если текст есть, определяем его ориентацию
        if text:
            # Определяем ориентацию страницы (0, 90, 180, 270 градусов)
            # Основываемся на высоте и ширине bounding box для текста
            blocks = page.get_text("blocks")
            middle = len(blocks) // 2
            if blocks:
                widths = []
                heights = []

                try:
                    for i in [0, 1, middle - 1, middle, middle + 1, len(blocks) - 1, len(blocks) - 2]:
                        _, _, w, h, _, _, _ = blocks[i]
                        widths.append(w)
                        heights.append(h)
                    width = sum(widths) / len(widths)
                    height = sum(heights) / len(heights)
                    if width > height:
                        # Текст ориентирован горизонтально
                        page.set_rotation(0)
                    else:
                        # Текст ориентирован вертикально (90 градусов)
                        page.set_rotation(90)
                except:
                    pass

    # Сохраняем PDF-документ с поворотами
    pdf_document.save(output_pdf_path)
    pdf_document.close()


def extract_pages(input_pdf_path, pages_to_keep, output_pdf_path=None) -> bytes:
    """ Извлечение страниц из pdf. Если output_pdf_path не задан, возвращает байты """

    # Открываем исходный PDF файл
    with open(input_pdf_path, "rb") as input_pdf_file:
        reader = PyPDF2.PdfReader(input_pdf_file)
        writer = PyPDF2.PdfWriter()

        # Извлекаем указанные страницы
        for page_num in pages_to_keep:
            # Нумерация страниц в PyPDF2 начинается с 0
            writer.add_page(reader.pages[page_num - 1])

        if output_pdf_path:
            # Записываем результат в новый PDF файл
            with open(output_pdf_path, "wb") as output_pdf_file:
                writer.write(output_pdf_file)
        else:
            # Создаем байтовый буфер для хранения результата
            output_buffer = io.BytesIO()
            writer.write(output_buffer)

            # Возвращаем байты PDF-файла
            return output_buffer.getvalue()


def get_pdf_bytes_with_selected_pages(pdf_path: str, pages: list[int] = ()) -> bytes:
    """Возвращает PDF в виде байтового объекта с указанными страницами"""
    reader = PyPDF2.PdfReader(pdf_path)
    writer = PyPDF2.PdfWriter()

    for page in pages:
        writer.add_page(reader.pages[page])

    pdf_bytes = io.BytesIO()
    writer.write(pdf_bytes)
    pdf_bytes.seek(0)  # Перемещаем указатель в начало

    return pdf_bytes.getvalue()  # Возвращаем PDF в виде байтов


def clear_pdf_waste_pages(pdf_path) -> bytes:
    """Удаляет лишние страницы, возвращает bytes"""

    normal_pages = []
    reader = PyPDF2.PdfReader(pdf_path)
    num_pages = len(reader.pages)
    # Проверка текста на каждой странице
    for page_num in range(num_pages):
        page = reader.pages[page_num]
        text = page.extract_text()
        # print(len(text))
        if len(text.strip()) > 8000:  # страница сплошного текста
            pass
        elif len(text.strip()) < 50:  # пустая страница или сканированная (нераспознаваемая)
            pass
        else:
            normal_pages.append(page_num)
    return get_pdf_bytes_with_selected_pages(pdf_path, pages=normal_pages)


# _______________________________________________________________________________________________________________ OPENAI

def update_assistant(client, assistant_id: str, model: int):
    if model == 3:
        model = 'gpt-3.5-turbo'
    if model == 4:
        model = 'gpt-4o'

    my_updated_assistant = client.beta.assistants.update(
        assistant_id,
        model=model
    )
    return my_updated_assistant


def update_assistant_system_prompt(new_prompt: str):
    load_dotenv(stream=get_stream_dotenv())
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
    client = OpenAI()
    client.beta.assistants.update(
        ASSISTANT_ID,
        instructions=new_prompt
    )


# ____________________________________________________________________________________________________________ MAIN_EDIT

def filtering_and_foldering_files(dir_path: str):
    """ Фильтрация по расширению и упаковка одиночных файлов в папки """
    for entry in os.scandir(dir_path):
        path = os.path.abspath(entry.path)
        if not os.path.isdir(path):  # папки пропускаются
            base = os.path.basename(os.path.basename(path))
            ext = os.path.splitext(os.path.basename(path))[-1]
            if ext not in config['valid_ext'] + config['excel_ext']:  # недопустимые расширения пропускаются
                continue
            counter = 1
            folder_name = f'{os.path.splitext(base)[0]}({ext.strip(".")})'
            folder_path = os.path.join(dir_path, folder_name)
            while os.path.exists(folder_path):
                folder_name = f'{base}({ext})({counter})'
                folder_path = os.path.join(dir_path, folder_name)
                counter += 1
            os.makedirs(folder_path, exist_ok=False)
            shutil.move(path, folder_path)


def mark_get_required_pages(pdf_path: str) -> list[int] | None:
    """ gets [2, 3] from '...EDITED\img@2@3.pdf' """

    if os.path.splitext(pdf_path)[-1] != '.pdf':
        return

    num_pages = count_pages(pdf_path)
    if not num_pages:
        return
    valid_pages = list(range(1, num_pages + 1))
    regex = r'(.*?)((?:@\d+)+)$'
    basename = os.path.basename(pdf_path)
    name, ext = os.path.splitext(basename)
    pages = re.findall(regex, name)
    if pages:
        pages = [int(x) for x in pages[0][1].split('@') if (x != '' and int(x) in valid_pages)]
    return sorted(list(set(pages)))


def mark_get_main_file(dir_path: str) -> str | None:
    # all files in dir
    files = os.listdir(dir_path)
    if not files:
        return

    # pdf, jpg or png files
    valid_files = [f for f in files if os.path.splitext(f)[-1] in config['valid_ext']]

    # 1. Главный файл .pdf или .jpg/.png + содержит @1 или @
    regex1 = r'(.*?)((?:@\d+)+)$'  # ...@1@2@3
    regex2 = r'(.*?)((?:@))$'  # ...@
    regexes = [regex1, regex2]
    for regex in regexes:
        valid_files_matched = [f for f in valid_files if re.fullmatch(regex, os.path.splitext(f)[0])]
        if valid_files_matched:
            return valid_files_matched[0]

    if valid_files:  # 2. Главный файл .pdf или .jpg/.png
        return valid_files[0]
    else:  # 3. Главный файл - случайный
        return files[0]


if __name__ == '__main__':
    pass
    # update_assistant_system_prompt(config['system_prompt'])

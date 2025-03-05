import os
import re
import sys
import pytesseract
import numpy as np
import pandas as pd
from PIL import Image
from pytesseract import Output


def extract_text_from_image(image: np.ndarray, psm=3):
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        pytesseract.pytesseract.tesseract_cmd = os.path.join(bundle_dir, 'Tesseract-OCR', 'tesseract.exe')

    config = f'--psm {psm}'  # --psm 4 --oem 3
    text = pytesseract.image_to_string(image, config=config, lang='rus+eng')
    return text


rgx = (r"((?:place|port) of (?:loading|discharge|receipt|delivery))|((?:description of goods)|(?:cargo description)|"
       r"(?:description of cargo))|"
       r"(particulars (?:declared|furnished) by (?:the)? shipper)")


def get_table_coords(image: str | Image.Image, regex: str = rgx) -> dict | None:
    def get_text_and_coords(group):
        text = " ".join(group['text'])
        min_left = group['left'].min()
        min_top = group['top'].min()
        return pd.Series({'text': text, 'min_left': min_left, 'min_top': min_top})

    df = pytesseract.image_to_data(image, output_type=Output.DATAFRAME, lang='eng+rus')
    df = df[df['conf'] > 75]
    if df.isna().all().all():
        return None
    grouped = df.groupby(['page_num', 'block_num', 'level', 'line_num']).apply(get_text_and_coords).reset_index()
    grouped = grouped[['text', 'min_left', 'min_top']]

    extracted_df = grouped['text'].str.extract(regex, flags=re.IGNORECASE)  # Извлекаем группы

    group_number = extracted_df.notna().idxmax(axis=1) + 1  # добавляем номер группы
    grouped['group_number'] = group_number

    filtered_df = grouped[extracted_df.notna().any(axis=1)]
    if filtered_df.empty:
        return None
    filtered_df_0 = filtered_df.sort_values('group_number', ascending=False).iloc[0]
    left, top = filtered_df_0.min_left, filtered_df_0.min_top - 50 if filtered_df_0.min_top - 50 > 0 else filtered_df_0.min_top

    return {'min_left': left, 'min_top': top}


def crop_goods_table(image: Image.Image, coords):
    if coords is None:
        return image

    img_w, img_h = image.width, image.height
    x1, x2 = 0, img_w
    y1, y2 = coords['min_top'], img_h
    return image.crop((x1, y1, x2, y2))

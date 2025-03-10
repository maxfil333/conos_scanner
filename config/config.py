import os
import sys
import json
import msvcrt
from dotenv import load_dotenv

from src.logger import logger
from config.pydantic_schema import PydanticSchema

load_dotenv("../config/paths.env")

config: dict = dict()
running_params: dict = dict()
config['magick_opt'] = '-colorspace Gray -quality 100 -units PixelsPerInch -density 350'.split(' ')
config['NAME_scanned'] = '0_scan'
config['NAME_text'] = '1_text'
config['NAME_verified'] = 'EXPORT'

if getattr(sys, 'frozen', False):  # в сборке
    config['BASE_DIR'] = os.path.dirname(sys.executable)
    config['POPPLER_PATH'] = os.path.join(sys._MEIPASS, 'poppler')
    config['magick_exe'] = os.path.join(sys._MEIPASS, 'magick', 'magick.exe')
else:
    config['BASE_DIR'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config['POPPLER_PATH'] = os.getenv("POPPLER_PATH")
    config['magick_exe'] = 'magick'  # или полный путь до ...magick.exe файла, если не добавлено в Path

config['CONFIG'] = os.path.join(config['BASE_DIR'], 'config')
config['IN_FOLDER'] = os.path.join(config['BASE_DIR'], 'IN')
config['EDITED'] = os.path.join(config['BASE_DIR'], 'EDITED')
os.makedirs(config['EDITED'], exist_ok=True)
config['CHECK_FOLDER'] = os.path.join(config['BASE_DIR'], 'CHECK')
os.makedirs(config['CHECK_FOLDER'], exist_ok=True)
config['CSS_PATH'] = "../../../../config/styles.css"
config['JS_PATH'] = "../../../../config/scripts.js"
config['crypto_env'] = os.path.join(config['CONFIG'], 'encrypted.env')
config['TESTFILE'] = os.path.join(config['CONFIG'], 'test.json')
config['GPTMODEL'] = 'gpt-4o-2024-08-06'

config['valid_ext'] = ['.pdf', '.jpg', '.jpeg', '.png']
config['excel_ext'] = ['.xls', '.xltx', '.xlsx']

try:
    with open(os.path.join(config['CONFIG'], 'crypto.key'), 'r') as f:
        config['crypto_key'] = f.read()
except FileNotFoundError as e:
    print(e)
    print('Не найден crypto.key')
    if getattr(sys, 'frozen', False):
        msvcrt.getch()
        sys.exit()

# "magick_opt": '-colorspace Gray -white-threshold 85% -level 0%,100%,0.5 -bilateral-blur 15 '
#               '-gaussian-blur 6 -quality 100 -units PixelsPerInch -density 350',
# "magick_opt": '-colorspace Gray -level 0%,100%,0.7 '
#               '-quality 100 -units PixelsPerInch -density 350',
# "magick_opt": '-colorspace Gray -auto-threshold OTSU -gaussian-blur 3 -enhance -enhance -enhance '
#               '-quality 100 -units PixelsPerInch -density 350',

# config['json_struct'] = ('{"shipper":"","consignee":"","Notify party":"",'
#                          '"bill of lading (B/L)":"","Booking":"","Reference":"",'
#                          '"vessel":"","voyage":"","port of loading":"","place of receipt":"",'
#                          '"place of delivery":"","port of discharge":"","goods":[{"container number":"",'
#                          '"container size":"","container type":"","seals":"","type of packages":"",'
#                          '"number of packages":"","gross weight":"","description":""}],'
#                          '"SUM GROSS WEIGHT":"","SUM TOTAL WEIGHT":"",'
#                          '"freight and charge":"","date of issue BL":"","date of shipped on board":""}')


class ConfigNames:
    goods = 'containers'
    name = 'container_goods'
    container = 'container'
    seals = 'seals'

NAMES = ConfigNames()


config['valid_ext'] = ['.pdf', '.jpg', '.jpeg', '.png']
config['excel_ext'] = ['.xls', '.xltx', '.xlsx']

config['response_format'] = PydanticSchema
config['system_prompt'] = f"You are an AI specialized in extracting Bill of Lading (BL) data."

logger.print("CONFIG INFO:")
logger.print('sys.frozen:', getattr(sys, 'frozen', False))

for k, v in config.items():
    if k not in ['crypto_key',
                 'response_format',
                 'system_prompt']:
        logger.print(f"{k}: {v}")


if __name__ == '__main__':
    pass



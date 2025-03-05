import os
import sys
import json
import msvcrt

from src.logger import logger


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
    config['POPPLER_PATH'] = r'C:\Program Files\poppler-22.01.0\Library\bin'
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
    name = 'container goods'
    container = 'container'
    seals = 'seals'


NAMES = ConfigNames()


config['valid_ext'] = ['.pdf', '.jpg', '.jpeg', '.png']
config['excel_ext'] = ['.xls', '.xltx', '.xlsx']

JSON_SCHEMA = {
    "name": "document",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "shipper": {"type": "string"},
            "shippers country": {"type": "string"},
            "consignee": {"type": "string"},
            "notify party": {"type": "string"},
            "bill of lading": {
                "description": "BL | bill of lading number | b/l number | Waybill number | B/L № | Номер коносамента | К/С",
                "type": "string"
            },
            "containers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "container": {"type": "string", "description": "[A-Z]{3}U ?[0-9]{7}"},
                        "container goods": {"type": "string", "description": "name (description) of goods"},
                        "container size": {
                            "type": "string",
                            "enum": ["20", "25", "40", "45"]
                        },
                        "container type": {
                            "type": "string",
                            "enum": ["GP", "DV", "DC", "TC", "TK", "HC", "OT", "RF", "RH", "VGP", "FT",
                                     "HCPW(HIGH CUBE PALLET WIDE)", "bulk"]
                        },
                        "seals": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "CONTAINER/40RH/<SEAL №>/WEIGH..."
                        },
                        "gross weight": {"type": "number"},
                        "tara weight": {"type": "number"},
                    },
                    "required": ["container", "container goods", "container size", "container type", "seals",
                                 "gross weight", "tara weight"],
                    "additionalProperties": False
                }
            },
        },
        "required": [
            "shipper",
            "shippers country",
            "consignee",
            "notify party",
            "bill of lading",
            "containers",
        ],
        "additionalProperties": False
    }
}

config['response_format'] = {"type": "json_schema", "json_schema": JSON_SCHEMA}

config['system_prompt'] = f"""
Извлеки данные из коносамента.
Если какой-то из параметров не найден, впиши значение ''.
""".strip()
# TODO: "few-shot" prompting for extracting seals "BMOU1234567/20DC/VT171687"


logger.print("CONFIG INFO:")
logger.print('sys.frozen:', getattr(sys, 'frozen', False))

for k, v in config.items():
    if k not in ['crypto_key',
                 'response_format',
                 'system_prompt']:
        logger.print(f"{k}: {v}")


if __name__ == '__main__':
    pass

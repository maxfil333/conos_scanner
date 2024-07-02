import json
import os
import sys
import msvcrt

config = dict()
config['magick_opt'] = '-colorspace Gray -quality 100 -units PixelsPerInch -density 350'.split(' ')
config['NAME_scanned'] = 'scannedPDFs'
config['NAME_text'] = 'textPDFs'
config['NAME_verified'] = 'verified'

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
config['IN_FOLDER_EDIT'] = os.path.join(config['IN_FOLDER'], 'edited')
config['CHECK_FOLDER'] = os.path.join(config['BASE_DIR'], 'CHECK')
config['CSS_PATH'] = os.path.join(config['CONFIG'], 'styles.css')
config['JS_PATH'] = os.path.join(config['CONFIG'], 'scripts.js')
config['crypto_env'] = os.path.join(config['CONFIG'], 'encrypted.env')
config['TESTFILE'] = os.path.join(config['CONFIG'], '__test.json')

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

config['json_struct'] = ('{"shipper":"","consignee":"","Notify party":"",'
                         '"bill of lading (B/L)":"","Booking":"","Reference":"",'
                         '"vessel":"","voyage":"","port of loading":"","place of receipt":"",'
                         '"place of delivery":"","port of discharge":"","goods":[{"container number":"",'
                         '"container size":"","container type":"","seals":"","type of packages":"",'
                         '"number of packages":"","gross weight":"","description":""}],'
                         '"SUM GROSS WEIGHT":"","SUM TOTAL WEIGHT":"",'
                         '"freight and charge":"","date of issue BL":"","date of shipped on board":""}')

config['system_prompt'] = f"""
Ты бот для анализа документов для морских грузоперевозок. 
Твоя задача заполнить json шаблон на основе отсканированного коносамента. 

Шаблон:
{config['json_struct'].strip()}

Особенности:
- Ищи информацию на всех страницах документа.
- Один container может включать в себя несколько seals.
- shipper, consignee, notify party - кратко.
- containers записаны в формате [A-Z]{{4}}\s?[0-9]{{7}}.
- seals записаны до или после containers.
- container size - 20, 40, 45.
- container type - GP, DC, TC, TK, HC, OT, RF, VGP, FT, HCPW(HIGH CUBE PALLET WIDE), bulk. 
- description - краткое описание груза.
- Даты записывай как DD-MM-YYYY.
- Если какой-то из параметров не найден, впиши значение ''.
- Запиши результат в одну строку.c
""".strip()

print("CONFIG INFO:")
print('sys._MEIPASS:', hasattr(sys, '_MEIPASS'))
print(f'POPPLER_RPATH = {config["POPPLER_PATH"]}')
print(f'magick_exe = {config["magick_exe"]}')
print(f'magick_opt = {config["magick_opt"]}')

if __name__ == '__main__':
    print(getattr(sys, 'frozen', False))
    for k, v in config.items():
        print(k)
        print(v)
        print('-' * 50)
        if k == 'json_struct':
            try:
                json.loads(v)
            except json.decoder.JSONDecodeError:
                print("Нарушена структура json")
                break

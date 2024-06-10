import os

config = dict()
config['BASE_DIR'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config['IN_FOLDER'] = os.path.join(config["BASE_DIR"], 'IN')
config['IN_FOLDER_EDIT'] = os.path.join(config["IN_FOLDER"], 'edited')
config['CHECK_FOLDER'] = os.path.join(config["BASE_DIR"], 'CHECK')
config['NAME_scanned'] = 'scannedPDFs'
config['NAME_text'] = 'textPDFs'
config['NAME_verified'] = 'verified'
config['OUT_FOLDER'] = os.path.join(config["BASE_DIR"], 'OUT')
config["POPPLER_PATH"] = r'C:\Program Files\poppler-22.01.0\Library\bin'
config['CSS_PATH'] = os.path.join(config["BASE_DIR"], 'config', 'styles.css')
config['JS_PATH'] = os.path.join(config["BASE_DIR"], 'config', 'scripts.js')
config['magick_opt'] = '-colorspace Gray'

# "magick_opt": '-colorspace Gray -white-threshold 85% -level 0%,100%,0.5 -bilateral-blur 15 '
#               '-gaussian-blur 6 -quality 100 -units PixelsPerInch -density 350',
# "magick_opt": '-colorspace Gray -level 0%,100%,0.7 '
#               '-quality 100 -units PixelsPerInch -density 350',
# "magick_opt": '-colorspace Gray -auto-threshold OTSU -gaussian-blur 3 -enhance -enhance -enhance '
#               '-quality 100 -units PixelsPerInch -density 350',

config['json_struct'] = ('{"shipper":"","consignee":"","bill of lading":"","Notify party":"",'
                         '"vessel №":"","voyage №":"","port of loading":"","place of receipt":"",'
                         '"place of delivery":"","port of discharge":"","goods":[{"container №":"",'
                         '"container type": "", "seals №":"", "type of packages":"","number of packages":"", '
                         '"gross weight":"", "description":""}],"SUM GROSS WEIGHT":"", "SUM TOTAL WEIGHT":"",'
                         '"freight and charge":"","date of issue BL": "","date of shipped on board":""}')

config['system_prompt'] = f"""
Ты бот для анализа документов для морских грузоперевозок. 
Твоя задача заполнить json шаблон на основе отсканированного коносамента. 

Шаблон:
{config['json_struct'].strip()}

Особенности:
- Ищи информацию на всех страницах документа.
- Один container может включать в себя несколько seals.
- containers записаны в формате [A-Z]{{4}}\s?[0-9]{{7}}.
- seals записаны до или после containers.
- shipper, consignee, notify party, description of goods,  записать о них всю доступную информацию.
- Если какой-то из параметров не найден, впиши значение ''.
- Запиши результат в одну строку.
""".strip()

if __name__ == '__main__':
    for k, v in config.items():
        print(k)
        print(v)
        print('-' * 50)

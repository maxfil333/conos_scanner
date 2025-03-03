import re
import json
import inspect
from dotenv import load_dotenv

from src.logger import logger
from config.config import NAMES

from src.utils import convert_json_values_to_strings, handling_openai_json, switch_to_latin
from src.utils import replace_container_with_latin
from src.utils_config import get_stream_dotenv

load_dotenv(stream=get_stream_dotenv())


# ___________________________________________ HANDLING OPENAI OUTPUT (JSON) ___________________________________________

def local_postprocessing(response) -> str | None:
    re_response = handling_openai_json(response)
    if re_response is None:
        return None
    logger.print(f'function "{inspect.stack()[1].function}":')
    dct = convert_json_values_to_strings(json.loads(re_response))

    container_regex = r'[A-ZА-Я]{3}U\s?[0-9]{6}-?[0-9]'
    container_regex_lt = r'[A-Z]{3}U\s?[0-9]{6}-?[0-9]'

    load_dotenv(stream=get_stream_dotenv())

    # Услуги

    for i_, good_dct in enumerate(dct[NAMES.goods]):

        # 1 Containers
        cont = good_dct[NAMES.container]
        good_dct[NAMES.container] = replace_container_with_latin(cont, container_regex)
        cont = good_dct[NAMES.container]
        containers_cont = list(map(lambda x: re.sub(r'[\s\-]', '', x), re.findall(container_regex_lt, cont)))
        uniq_containers_from_cont = list(dict.fromkeys(containers_cont))
        good_dct[NAMES.container] = ' '.join(uniq_containers_from_cont)

        # 2 Seals
        seals = good_dct[NAMES.seals]
        seals = [switch_to_latin(seal) for seal in seals]
        seals = list(map(lambda x: re.sub(r'[\s\-]', '', x), seals))
        good_dct[NAMES.seals] = " ".join(seals)

    string_dictionary = convert_json_values_to_strings(dct)
    return json.dumps(string_dictionary, ensure_ascii=False, indent=4)

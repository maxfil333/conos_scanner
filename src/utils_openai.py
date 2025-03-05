from config.config import config
from src.utils import extract_text_with_fitz, extract_excel_text
from src.main_openai import run_chat, run_assistant


def pdf_to_ai(file: str, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict,
              response_format=config['response_format']) -> str:

    running_params.setdefault('text_or_scanned_folder', config['NAME_text'])
    running_params.setdefault('current_texts', extract_text_with_fitz(file))
    running_params.setdefault('doc_type', 'pdf')

    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            return f.read()
    if not text_to_assistant:
        result = run_chat(file,
                          response_format=response_format, text_content=running_params['current_texts'])
        return result
    else:
        result = run_assistant(file)
        return result


def excel_to_ai(file: str, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict) -> str:
    running_params['text_or_scanned_folder'] = config['NAME_text']
    running_params['current_texts'] = extract_excel_text(file)
    running_params['doc_type'] = 'excel'
    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            return f.read()
    result = run_chat('',
                      response_format=config['response_format'], text_content=running_params['current_texts'])
    return result


def images_to_ai(files: list, test_mode: bool, text_to_assistant: bool, config: dict, running_params: dict) -> str:
    running_params['text_or_scanned_folder'] = config['NAME_scanned']
    files.sort(reverse=True)
    if test_mode:
        with open(config['TESTFILE'], 'r', encoding='utf-8') as f:
            return f.read()
    result = run_chat(*files,
                      response_format=config['response_format'], text_content=None)
    return result

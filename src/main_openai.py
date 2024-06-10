import openai
from openai import OpenAI

import os
from dotenv import load_dotenv
from time import perf_counter
import re
import json
from PIL import Image

from config.config import config
from utils import base64_encode_pil, convert_json_values_to_strings


# ___________________________ CHAT ___________________________

def run_chat(*img_paths: str, detail='high', show_logs=False) -> str:
    load_dotenv()
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    content = []
    for img_path in img_paths:
        d = {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_encode_pil(Image.open(img_path))}",
                          "detail": detail}
        }
        content.append(d)

    start = perf_counter()
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=
        [
            {"role": "system", "content": config['system_prompt']},
            {"role": "user", "content": content}
        ],
        max_tokens=2000,
    )
    print(f'img_paths: {img_paths}')
    print(f'time: {perf_counter() - start:.2f}')
    print(f'completion_tokens: {response.usage.completion_tokens}')
    print(f'prompt_tokens: {response.usage.prompt_tokens}')
    print(f'total_tokens: {response.usage.total_tokens}')

    response = response.choices[0].message.content

    re_response = re.sub(r'(\s{2,}|```|\n)', '', response)
    if re_response[0:4] == 'json':
        re_response = re_response[4:]

    if show_logs:
        print('run_chat response:')
        print(repr(response))
        print('run_chat re_response:')
        print(repr(re_response))

    dictionary = json.loads(re_response)

    # container_regex = r'[A-Z]{4}\s?[0-9]{7}'
    # for item in dictionary['Услуги']:
    #     name = item['Наименование']
    #     item['Номера контейнеров'] = ' '.join(list(map(lambda x:
    #                                                    re.sub(r'\s', '', x), re.findall(container_regex, name))))
    string_dictionary = convert_json_values_to_strings(dictionary)
    return json.dumps(string_dictionary, ensure_ascii=False, indent=4)


# ___________________________ ASSISTANT ___________________________

def run_assistant(file_path, show_logs=False):
    load_dotenv()
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

    start = perf_counter()
    client = OpenAI()
    assistant = client.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)

    message_file = client.files.create(file=open(file_path, "rb"), purpose="assistants")
    # Create a thread and attach the file to the message
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": " ",
                "attachments": [{"file_id": message_file.id, "tools": [{"type": "file_search"}]}],
            }
        ]
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id, assistant_id=assistant.id
    )
    if run.status == 'completed':
        print(f'file_path: {file_path}')
        print(f'time: {perf_counter() - start:.2f}')
        print(f'completion_tokens: {run.usage.completion_tokens}')
        print(f'prompt_tokens: {run.usage.prompt_tokens}')
        print(f'total_tokens: {run.usage.total_tokens}')

    messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
    response = messages[0].content[0].text.value

    re_response = re.sub(r'(\s{2,}|```|\n)', '', response)
    if re_response[0:4] == 'json':
        re_response = re_response[4:]

    if show_logs:
        print('run_chat response:')
        print(repr(response))
        print('run_chat re_response:')
        print(repr(re_response))

    dictionary = json.loads(re_response)

    # container_regex = r'[A-Z]{4}\s?[0-9]{7}'
    # for item in dictionary['Услуги']:
    #     name = item['Наименование']
    #     item['Номера контейнеров'] = ' '.join(list(map(lambda x:
    #                                                    re.sub(r'\s', '', x), re.findall(container_regex, name))))

    string_dictionary = convert_json_values_to_strings(dictionary)
    return json.dumps(string_dictionary, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    file_path = os.path.join('..', 'IN/221.jpg')
    result = run_chat(file_path,
                      os.path.join('..', 'IN/222.jpg'),
                      # os.path.join('..', 'IN/edited/458.jpg'),
                      detail='high', show_logs=False)
    #
    # result = run_assistant(os.path.join(file_path),
    #                        show_logs=True)

    print('#' * 50)
    print(result)
    print('#' * 50)

    json_path = os.path.join("..", "OUT", os.path.splitext(os.path.basename(file_path))[0] + ".json")
    with open(json_path, 'w', encoding='utf-8') as file:
        file.write(result)

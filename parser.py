import os
import re
import json
import argparse
from multiprocessing import Process, Manager
from natasha import MorphVocab, NamesExtractor


# # Блок констант - префиксы и суффиксы договоров. Редактируй при необходимости.

# Новая нумерация
PREFIXES_NEW = ["МБ", "ПВ", "ВД", "ЗБ", "КХ", "ПТ", "ДВ", "УС", "АЛ", "ТП", "ММ", "ДЦ"]
SUFFIXES_NEW = ["022", "066", "142", "024", "099", "042", "054", "055", "059", "063", "163", "070", "072", "002", "074"]
ACCEPTABLE_YEARS_NEW = [f"{y:02d}" for y in range(18, 30)]

# Старая нумерация
PREFIXES_OLD = ["МБ", "МЮ", "МЕ", "МС", "МЧ", "МПМ", "МР", "МФА", "М", "МК", "МО", "МТ", "Е", "Н", "К", "ВДБ", "ВДЮ",
                "ВДЕ", "ВДС", "ВДЧ", "ВДПМ", "ВДР", "ВДФА", "ВДК", "ВДО", "ВДТ", "ЗБ", "ЗЮ", "ЗЕ", "ЗС", "ЗЧ", "ЗПМ",
                "ЗР", "ЗФА", "З", "ЗК", "ЗО", "ЗТ", "КХБ", "КХЮ", "КХЕ", "КХС", "КХЧ", "КХПМ", "КХР", "КХФА", "КХК",
                "КХО", "КХТ", "ПБ", "ПЮ", "ПЕ", "ПЧ", "ППМ", "ПТР", "ПФА", "П", "ПК", "ПО", "ПТ", "ДБ", "ДЮ", "ДЕ",
                "ДС", "ДЧ", "ДПМ", "ДР", "ДФА", "Д", "ДК", "ДО", "ДТ", "УБ", "УЮ", "УЕ", "УС", "УЧ", "УПМ", "УР", "УФА",
                "УК", "УО", "УТ", "ББ", "АЮ", "АПМ", "БР", "А", "АК", "АО", "АТ", "ЦБ", "ЦЮ", "ЦЕ", "ЦС", "ЦЧ", "ЦПМ",
                "ЦР", "ЦФА", "Ц", "ЦК", "ЦО", "ЦТ", "Ю", "С", "Ч", "ПМ", "Р", "ФА", "О", "Т", "ВД", "КХ", "ПС", "АБ",
                "АЕ", "АС", "АЧ", "АР", "АФА", "У", "ММ", "Б", "МСМ", "ЦСМ", "СМ", "ВДСМ", "ЗСМ", "КХСМ", "ПСМ", "ДСМ",
                "УСМ", "АСМ", "МТЛ", "ЦТЛ", "ТЛ", "ВДТЛ", "ЗТЛ", "КХТЛ", "ПТЛ", "ДТЛ", "УТЛ", "АТЛ", "ММВ", "ЦМВ", "МВ",
                "ВДМВ", "ЗМВ", "КХМВ", "ПТМВ", "ДМВ", "УМВ", "АМВ", "ДЦ"
                ]
ACCEPTABLE_YEARS_OLD = [f"{y:02d}" for y in range(5, 19)]

# в платежках часто путают букву и цифру "3", поэтому добавляем оба варианта
for SET in [PREFIXES_NEW, PREFIXES_OLD]:
    for p in SET:
        if 'З' in p:
            SET.append(p.replace('З', '3'))


# # # Собираем регулярки для поиска номера договора в строках

# # Новая нумерации

# Основная регулярка
REGEX_NEW = re.compile(f"({'|'.join(p for p in PREFIXES_NEW)})\s?\d+\s?-?-?\s?(20)*"
                       f"({'|'.join(y for  y in ACCEPTABLE_YEARS_NEW)})*\s?/?\s?({'|'.join(s for s in SUFFIXES_NEW)})*")

# Вспомогательные регулярки, используем для приведения номера к стандартному виду
MISC_REGEX_NEW = {
    'prefix_and_whitespace': re.compile(f"^({'|'.join(p for p in PREFIXES_NEW)})\s"),
    'whitespace_before_year': re.compile(f"({'|'.join(p for p in PREFIXES_NEW)})\s?\d+\s?-?-?\s?(20)*"
                                         f"({'|'.join(y for  y in ACCEPTABLE_YEARS_NEW)})*")
}

# # Старая нумерация

# Основная регулярка
REGEX_OLD = re.compile(f"(\s|№|;)({'|'.join(p for p in PREFIXES_OLD)})\s?"
                       f"(20)*({'|'.join(y for  y in ACCEPTABLE_YEARS_OLD)})\s?-?-?\s?\d+")

# Вспомогательные регулярки, используем для приведения номера к стандартному виду
MISC_REGEX_OLD = {
    'prefix_and_whitespace': re.compile(f"^({'|'.join(p for p in PREFIXES_OLD)})\s"),
    'whitespace_before_num': re.compile(f"({'|'.join(y for  y in ACCEPTABLE_YEARS_OLD)})\s?-?-?\s?\d+")
}


class Natasha(object):
    '''Класс парсера'''

    def __init__(self):
        self.morph_vocab = MorphVocab()
        self.names_extractor = NamesExtractor(self.morph_vocab)
        self.regex_new = REGEX_NEW
        self.misc_regex_new = MISC_REGEX_NEW
        self.regex_old = REGEX_OLD
        self.misc_regex_old = MISC_REGEX_OLD

    def __extract_name(self, text):
        '''Достаем имя из строки'''

        names = list(self.names_extractor(text))
        longest_name = None
        name_length = 0
        last_name = None
        for name in names:
            if last_name is None and name.fact.as_json.get('last'):
                last_name = name.fact.as_json.get('last')
            if len(name.fact.as_json) > name_length:
                longest_name = name.fact.as_json
                name_length = len(name.fact.as_json)
        if longest_name:
            if 'last' not in longest_name and last_name:
                longest_name['last'] = last_name
            return longest_name
        else:
            return {}

    def __extract_num(self, text):
        '''Достаем номер договора из строки'''

        # ищем новый номер
        match = self.regex_new.search(text)
        num = match.group() if match else None

        if num:
            # приводим номер к нормальному виду, если нашли
            num = num.replace('--', '-')

            for suspicious_prefix in [p for p in PREFIXES_NEW if '3' in p]:
                if num.startswith(suspicious_prefix):
                    replacement = suspicious_prefix.replace('3', 'З')
                    num = num.replace(suspicious_prefix, replacement, 1)

            if ' ' in num:
                wp_match = self.misc_regex_new['prefix_and_whitespace'].search(num)
                if wp_match:
                    wp_search = wp_match.group()
                    wp_replace = wp_search.replace(' ', '')
                    num = num.replace(wp_search, wp_replace)

            if ' ' in num:
                before_year_match = self.misc_regex_new['whitespace_before_year'].search(num)
                if before_year_match:
                    before_year_search = before_year_match.group()
                    before_year_replace = before_year_search
                    if '-' not in before_year_search:
                        before_year_replace = before_year_replace.replace(' ', '-', 1)
                    before_year_replace = before_year_replace.replace(' ', '')
                    num = num.replace(before_year_search, before_year_replace)

            return num

        # номер в новом формате не нашли - поищем тогда старый формат
        match = self.regex_old.search(text)
        num = match.group() if match else None
        if num:
            num = num[1:]
            # приводим номер к нормальному виду, если нашли
            num = num.replace('--', '-')

            for suspicious_prefix in [p for p in PREFIXES_OLD if '3' in p]:
                if num.startswith(suspicious_prefix):
                    replacement = suspicious_prefix.replace('3', 'З')
                    num = num.replace(suspicious_prefix, replacement, 1)

            if ' ' in num:
                wp_match = self.misc_regex_old['prefix_and_whitespace'].search(num)
                if wp_match:
                    wp_search = wp_match.group()
                    wp_replace = wp_search.replace(' ', '')
                    num = num.replace(wp_search, wp_replace)

            if ' ' in num:
                before_num_match = self.misc_regex_old['whitespace_before_num'].search(num)
                if before_num_match:
                    before_num_search = before_num_match.group()
                    before_num_replace = before_num_search
                    if '-' not in before_num_search:
                        before_num_replace = before_num_replace.replace(' ', '-', 1)
                    before_num_replace = before_num_replace.replace(' ', '')
                    num = num.replace(before_num_search, before_num_replace)
            if '-' not in num:
                return None  # Скорее всего, это кусок адреса, а не номер договора
            else:
                return num   # А вот тут у нас наверняка номер договора

    def parse_row(self, row):
        '''Полный парсинг одной записи'''

        row['name'] = self.__extract_name(row['text'])
        row['contract_num'] = self.__extract_num(row['text'])

        return row


def worker(chunk_to_parse, shared_list):
    '''Воркер одиночного процесса. Обрабатывает кусок данных, добавляет результат в общий список.
       Несколько воркеров работают параллельно.'''

    parser = Natasha()
    for row in chunk_to_parse:
        shared_list.append(parser.parse_row(row))


if __name__ == '__main__':
    # !!! ВЫПОЛНЕНИЕ НАЧИНАЕТСЯ ОТСЮДА !!!

    # читаем аргументы
    parser = argparse.ArgumentParser(description='Парсер назначений платежей.')
    parser.add_argument('-i', dest='input_filename', type=str, default='input.json',
                        help='Имя входного файла.')
    parser.add_argument('-o', dest='output_filename', type=str, default='output.json',
                        help='Имя выходного файла.')
    parser.add_argument('-t', dest='threads', type=int, default=6,
                        help='Количество параллельных потоков (увеличиваем для скорости).')
    args = parser.parse_args()

    # читаем входные данные
    if not os.path.isfile(args.input_filename):
        raise OSError(f"Ошибка: не найден входной файл: {args.input_filename}")

    try:
        to_parse = [{k: l[k].upper() for k in l} for l in json.loads(open(args.input_filename, 'rb').read())]
        for i, l in enumerate(to_parse):
            l['idx'] = i
    except:
        raise ValueError(f'Ошибка: содержимое файла "{args.input_filename}" не является валидным JSON!')

    results = Manager().list()  # Тут храним результаты, в расшаренной памяти

    # делим данные между потоками
    rows_count = len(to_parse)
    step = rows_count / args.threads
    start_idx = 0
    end_idx = 0
    partitions = {}
    for i in range(args.threads):
        end_idx = min(start_idx + step, rows_count)
        partitions[i] = [int(start_idx // 1), int(end_idx // 1)]
        start_idx = end_idx
    if partitions:
        partitions[args.threads - 1][-1] = rows_count

    # запускаем процессы
    workers = []
    for i in range(args.threads):
        part = partitions[i]
        workers.append(Process(target=worker, args=(to_parse[part[0]:part[1]], results)))
        workers[i].start()

    # ждем, пока все закончат
    for i in range(args.threads):
        workers[i].join()

    # сортируем результаты в изначальном порядке
    results = list(results)
    results = sorted(results, key=lambda r: r['idx'])

    # сохраняем в файл
    try:
        with open(args.output_filename, 'w+') as f:
            f.write(json.dumps(results, ensure_ascii=False, indent=4))

    except Exception as ex:
        print("Ошибка при сохранении результатов в файл!")
        raise ex

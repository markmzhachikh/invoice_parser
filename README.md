# Парсер назначений платежа
### Состав
* __parser.py__ - сам скрипт
* __test_input.json__ - пример входного файла
* __test_output.json__ - пример выходного файла
### Установка
* Установи [python версии >=3.8](https://www.python.org/downloads/) 
__Внимание, в версии 3.7 и ниже скрипт не запустится!__
* Проверь установку. В командной строке ```python --version``` должна возвращать что-то вроде ```Python 3.8.0```. 
```pip --version``` должна вернуть что-то наподобие ```pip 19.0.3```

_Нюанс: команда может забиндится на ```python3``` или ```py``` вместо ```python```. 
Аналогично, вместо ```pip``` бывает ```pip3```. В этом случае используй их вместо ```python``` и ```pip```._

* Установи [Наташеньку](https://github.com/natasha/natasha). Для этого в терминале выполни ```pip install natasha```

### Запуск
* Открой терминал в директории скрипта.
* Выполни ```python parser.py -i "test_input.json" -o "test_output.json"```. Если скрипт отработал молча - запуск успешный. 
### Аргументы командной строки
* ```-i``` - имя входного файла.
* ```-o``` - имя выходного файла.
### Входной файл.
Схема:
```.json
{
    "meta": {
        "prefixes": [
            "string", ... , "string"
        ],
        "suffixes": [
            "string", ... , "string"
        ]
    },
    "data": [
        {
            "num": "string",
            "text": "string"
        },
        ... ,
        {
            "num": "string",
            "text": "string"
        }
    ]
}
```
В поле ```meta``` нужно передавать список префиксов и суффиксов для новой нумерации договоров.
```data``` должо состоять из массива json-объектов вида: ```{"num":"НомерДокумента", "text":"ТекстНазначенияПлатежа"}```. 
Case-sensitive. 
[Пример валидного файла.](https://github.com/Av1chem/invoice_parser/blob/main/test_input.json)
### Выходной файл.
Состоит из массива json-объектов вида:
```
{
    "num": "НомерДокумента",
    "text": "ТекстНазначенияПлатежа",
    "idx": ИндексВФайле,
    "name": {
        "first": "Имя",
        "last": "Фамилия",
        "middle": "Отчество",
        "full_name": "ФамилияИмяОтчество"
    },
    "contract_num": "НомерДоговора"
}
```
[Пример выходного файла.](https://github.com/Av1chem/invoice_parser/blob/main/test_output.json)

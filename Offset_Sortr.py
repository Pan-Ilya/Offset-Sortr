import os
import re
import shutil
import time

import change_pdf_size
import funcs
import json
from pypdf import PdfReader
from pypdf.errors import PdfReadError
import traceback

# from config import data

COLOR_4_0 = ['1+0', '4+0']
COLOR_4_4 = ['1+1', '4+4']
VILETI = 4


def product_size_to_mm(product_size: str|list[int], reverse:bool=False) -> str|list[int]:
    """ Возвращает список целочисленных значений ВхШ страницы документа. Результат отсортирован по возрастанию. """

    if not reverse and isinstance(product_size, str):
        product_size = ''.join('x' if char.isalpha() else char for char in product_size)
        return sorted([int(size) for size in product_size.split('x')])

    elif reverse and isinstance(product_size, list):
        return 'x'.join(str(x) for x in product_size)


with open('config.json', 'r', encoding='utf-8-sig') as file:
    data = json.load(file)

    # Получить все имена не стандартных папкок и путей к ним из файлика конфигурации .ру
    # 1) Имена не стандартных папок (а точнее их размеры)
    all_podpis_sizes = [product_size_to_mm(file['podpis']) for file in data['special files']]

    # 2) Пути к стандартным папкам
    error = data['error files']
    other = data['other files']


def replacer(filename: str, destination: str) -> None:
    """ Перемещает файл в указанную директорию. Всего 3 возможных варианта:
    1) Перемещение файла в указанную директорию
    2) Перезапись папки и содержимого
    3) Перемещение папки в указанную директорию
    """

    if os.path.isfile(filename):
        os.replace(filename, destination)

    elif os.path.isdir(filename) and os.path.exists(destination):
        shutil.rmtree(destination)
        os.replace(filename, destination)

    elif os.path.isdir(filename):
        os.replace(filename, destination)

    else:
        raise NotADirectoryError('replacer function Error!')


def get_params_from_filename(filename: str) -> list[str | int] | bool:
    """ Возвращает список параметров .pdf файла из его названия.
     Пример имени файла:
     02-17_lider_pp_1146806_210x98_4+4_6v_130_1000.pdf """

    # offset_filename_pattern = r'(?i)(?P<size>\d{2,}[xх]\d{2,}).*?' \
    #                           r'(?P<color>\d\+\d)'

    offset_filename_pattern = r'(?i)(?P<size>\d{2,}[xх]\d{2,}).*?' \
                              r'(?P<color>\d\+\d).*?' \
                              r'(?P<density>\d{2,}(?:[a-z])*)'

    result = re.findall(offset_filename_pattern, filename)

    if result:
        product_size, color, density = result[0]
        return [product_size, color, density]

    return False


def check_colorify(color: str, pages: int) -> bool:
    """ Проверка цветности документа """

    if color in COLOR_4_4 and pages == 2 or \
            color in COLOR_4_0 and pages == 1:
        return True

    return False


@funcs.all_pages_has_same_size_checker
def CropBox_equal_special_product_size(file: PdfReader, product_size: str) -> bool:
    """ Фактический (видимый) размер документа равен специальному размеру, который указан в файле конфигурации.
    Размер готового изделия указан в подписи .pdf документа. """

    special_file_size = 0
    for special_file in data['special files']:
        if product_size_to_mm(special_file['podpis']) == product_size_to_mm(product_size):
            special_file_size = special_file['bleeds']

    current_file_size = sorted(funcs.get_current_page_size(file.pages[0]))

    if isinstance(special_file_size, str):
        special_file_size = product_size_to_mm(special_file_size)
        return current_file_size == special_file_size

    elif isinstance(special_file_size, list):
        special_file_size = [product_size_to_mm(file_size) for file_size in special_file_size]
        return current_file_size in special_file_size

    else:
        return False


# Из указанной директории проанализировать все файлы
input_dir = input('Select folder:\n')

while True:

    try:
        os.chdir(input_dir)

        for filename in funcs.get_all_filenames_in_directory(input_dir):

            if filename[-8:] == '_lic.pdf' in filename:
                result_name = filename.replace(filename[-8:], '.pdf')

            elif filename[-7:] == '_ob.pdf' in filename:
                result_name = filename.replace(filename[-7:], '.pdf')

            else:
                result_name = filename

            # Сначала выполнить все проверки ПДФ файла, затем направить его в соответствующую папку.

            product_size, color, density = get_params_from_filename(filename)
            product_size_mm = product_size_to_mm(product_size)

            FILE = False
            DIR = False

            if os.path.isfile(filename):
                FILE = True
                pdf_file = PdfReader(filename)
                pages = len(pdf_file.pages)

            elif os.path.isdir(filename):
                DIR = True
                files_in_directory = funcs.get_all_filenames_in_directory(filename)
                # files_in_directory = funcs.get_all_filenames_in_directory(f"{from_path}\\{filename}")

                # Проверка количества файлов внутри папки.
                if len(files_in_directory) != 2:
                    print(f'''[{funcs.get_current_time()}]   {filename}'
                    \rКол-во файлов внутри папки не равно двум. Направляю в ошибки.\n''')
                    replacer(filename, os.path.join(error, filename))
                    continue

                # Путь до конкретного файла внутри директории - os.path.join(from_path, filename, file)
                lic, ob = (PdfReader(os.path.join(input_dir, filename, file)) for file in files_in_directory)

                # Проверка количества страниц документа внутри папки.
                if len(lic.pages) != 1 or len(ob.pages) != 1:
                    print(f'''[{funcs.get_current_time()}]   {filename}'
                    \rФайл внутри папки содержит более одной страницы. Направляю в ошибки.\n''')
                    replacer(filename, os.path.join(error, filename))
                    continue

            else:
                print(f'''[{funcs.get_current_time()}]   {filename}'
                      \rОбъект не является ни файлом ни папкой, направляю его в папку с ошибками.\n''')
                replacer(filename, os.path.join(error, filename))
                continue

            # Проверка для файлов ==================================================================================

            # Отдельно для Офсет 80
            if FILE and density == '80':

                if not check_colorify(color, pages):
                    print(f'[{funcs.get_current_time()}]   {filename}\nЦветность документа не соответствует подписи.\n')
                    replacer(filename, os.path.join(error, filename))

                elif not funcs.CropBox_equal_product_size(pdf_file, product_size):
                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rCropBox документа не соответствует размеру подписи {product_size}.\n''')
                    replacer(filename, os.path.join(error, filename))

                elif not (funcs.all_pages_are_landscape(pdf_file, product_size) or
                          funcs.all_pages_are_portrait(pdf_file, product_size)):
                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rСтраницы документа имеют разную ориентацию.\n''')
                    replacer(filename, os.path.join(error, filename))

                else:
                    new_size_mm = [funcs.formats_80.get(x, x) for x in product_size_mm]
                    h, w = new_size_mm
                    new_size = product_size_to_mm(new_size_mm, reverse=True)
                    result_name = result_name.replace(product_size, new_size)

                    change_pdf_size.resize_pdf_mm(filename, filename, w + 4, h + 4)
                    print(f'Поймал с 80ку  - {result_name}\n')
                    replacer(filename, os.path.join(other, result_name))


            elif FILE and product_size_mm not in all_podpis_sizes:

                if not check_colorify(color, pages):
                    print(f'[{funcs.get_current_time()}]   {filename}\nЦветность документа не соответствует подписи.\n')
                    replacer(filename, os.path.join(error, filename))

                elif not funcs.CropBox_equal_product_size(pdf_file, product_size):
                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rCropBox документа не соответствует размеру подписи {product_size}.\n''')
                    replacer(filename, os.path.join(error, filename))

                elif not (funcs.all_pages_are_landscape(pdf_file, product_size) or
                          funcs.all_pages_are_portrait(pdf_file, product_size)):
                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rСтраницы документа имеют разную ориентацию.\n''')
                    replacer(filename, os.path.join(error, filename))

                else:
                    replacer(filename, os.path.join(other, result_name))

            elif FILE and product_size_mm in all_podpis_sizes:

                if not check_colorify(color, pages):
                    print(f'[{funcs.get_current_time()}]   {filename}\nЦветность документа не соответствует подписи.\n')
                    replacer(filename, os.path.join(error, filename))

                elif not CropBox_equal_special_product_size(pdf_file, product_size):
                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rCropBox документа не соответствует размеру подписи {product_size}.\n''')
                    replacer(filename, os.path.join(error, filename))

                elif not (funcs.all_pages_are_landscape(pdf_file, product_size) or
                          funcs.all_pages_are_portrait(pdf_file, product_size)):
                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rСтраницы документа имеют разную ориентацию.\n''')
                    replacer(filename, os.path.join(error, filename))

                else:
                    destination = ''
                    for files in data['special files']:
                        if product_size_to_mm(files['podpis']) == product_size_mm:
                            destination = files['folder']

                    replacer(filename, os.path.join(destination, result_name))


            # Проверка для ПАПОК ==================================================================================
            elif DIR and product_size_mm not in all_podpis_sizes:

                if color in COLOR_4_0:

                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rПапка Должна иметь двухстороннюю печать. Сейчас её подпись {color}. Направляю в ошибки.\n''')
                    replacer(filename, os.path.join(error, filename))

                elif not (
                        funcs.CropBox_equal_product_size(lic, product_size) and
                        funcs.CropBox_equal_product_size(ob, product_size)):

                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rCropBox документа внутри папки не соответствуетразмеру подписи {product_size}.\n''')
                    replacer(filename, os.path.join(error, filename))

                elif not (
                        funcs.all_pages_are_landscape(lic, product_size) and
                        funcs.all_pages_are_landscape(ob, product_size)
                        or
                        funcs.all_pages_are_portrait(lic, product_size) and
                        funcs.all_pages_are_portrait(ob, product_size)):

                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rСтраницы документа внутри папки имеют разную ориентацию..\n''')
                    replacer(filename, os.path.join(error, filename))

                else:
                    replacer(filename, os.path.join(other, filename))


            elif DIR and product_size_mm in all_podpis_sizes:

                if color in COLOR_4_0:

                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rПапка Должна иметь двухстороннюю печать. Сейчас её подпись {color}. Направляю в ошибки.\n''')
                    replacer(filename, os.path.join(error, filename))

                elif not (
                        CropBox_equal_special_product_size(lic, product_size) and
                        CropBox_equal_special_product_size(ob, product_size)):

                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rCropBox документа внутри папки не соответствуетразмеру подписи {product_size}.\n''')
                    replacer(filename, os.path.join(error, filename))

                elif not (
                        funcs.all_pages_are_landscape(lic, product_size) and
                        funcs.all_pages_are_landscape(ob, product_size)
                        or
                        funcs.all_pages_are_portrait(lic, product_size) and
                        funcs.all_pages_are_portrait(ob, product_size)):

                    print(f'''[{funcs.get_current_time()}]   {filename}
                    \rСтраницы документа внутри папки имеют разную ориентацию..\n''')
                    replacer(filename, os.path.join(error, filename))

                else:
                    destination = ''
                    for files in data['special files']:
                        if product_size_to_mm(files['podpis']) == product_size_mm:
                            destination = files['folder']

                    replacer(filename, os.path.join(destination, filename))


    except IndexError:
        print(f'[{funcs.get_current_time()}]   Не понимаю имя файла {filename}.\nНаправляю его в папку с ошибками.\n')
        replacer(filename, os.path.join(error, filename))

    except PdfReadError:
        # EmptyFileError
        print(f'''[{funcs.get_current_time()}]   {filename}
        \rОшибка при чтении .pdf - файлика. Направляю в ошибки.\n''')
        replacer(filename, os.path.join(error, filename))

    except Exception as E:
        print(E)
        print(f'[{funcs.get_current_time()}]   Произошла неожиданная ошибка. Повторяю попытку.')
        # traceback.print_exc()

    finally:
        time.sleep(3)

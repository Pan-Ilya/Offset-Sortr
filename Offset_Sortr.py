import os
import re
import shutil
import time
import funcs
from PyPDF2 import PdfReader
from config import directories

COLOR_4_0 = ['1+0', '4+0']
COLOR_4_4 = ['1+1', '4+4']
VILETI = 4


def product_size_to_mm(product_size: str) -> list[int]:
    """ Возвращает список целочисленных значений ВхШ страницы документа. Результат отсортирован по возрастанию. """

    product_size = ''.join('x' if char.isalpha() else char for char in product_size)

    return sorted([int(size) for size in product_size.split('x')])


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

    offset_filename_pattern = r'(?i)(?P<size>\d{2,}[xх]\d{2,}).*?' \
                              r'(?P<color>\d\+\d)'

    result = re.findall(offset_filename_pattern, filename)

    if result:
        product_size, color = result[0]
        return [product_size, color]

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
    for special_file in directories['special files']:
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


# Получить все имена не стандартных папкок и путей к ним из файлика конфигурации .ру
# 1) Имена не стандартных папок (а точнее их] размеры)
all_podpis_sizes = [product_size_to_mm(file['podpis']) for file in directories.get('special files')]

# 2) Пути к стандартным папкам
error = directories['error files']
other = directories['other files']

# Из указанной директории проанализировать все файлы
input_dir = input('Select folder:\n')

while True:

    try:
        os.chdir(input_dir)

        for filename in funcs.get_all_filenames_in_directory(input_dir):

            product_size, color = get_params_from_filename(filename)
            product_size_mm = product_size_to_mm(product_size)

            pdf_file = PdfReader(filename)
            pages = len(pdf_file.pages)

            if product_size_mm not in all_podpis_sizes:

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
                    replacer(filename, os.path.join(other, filename))

            else:
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
                    for files in directories['special files']:
                        if product_size_to_mm(files['podpis']) == product_size_mm:
                            destination = files['folder']

                    replacer(filename, os.path.join(destination, filename))

                # Сначала выполнить все проверки ПДФ файла, затем направить его в соответствующую папку.

    except Exception as E:
        print(E)
    finally:
        time.sleep(3)

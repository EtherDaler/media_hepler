import os
import fnmatch


def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

name = 'Nasiba Abdullaeva - Aarezoo Gom Kardam ⧸ Хиты 80-х в Узбекистане'
print(name.find('⧸'))
print(find(f'{name}*', '.'))
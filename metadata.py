import os
import ffmpeg
import re  # regex - used ot search through text file
import pyheif # for heic files
import exifread # for heic files
import io

from PIL import Image
from PIL.ExifTags import TAGS
from PIL import Image, ExifTags
from pillow_heif import register_heif_opener
from pprint import pprint
from pathlib import Path  # search within directories and subdirectories

logfile = open('imagelog.txt', 'a')  # all files that are not printed out below will logged here

def get_exif_data(ifile):  # if the file is a standard image file
    if re.search(r'jpeg$|bmp$|png$|jpg$', str(ifile), re.IGNORECASE):
        image = Image.open(ifile)
        exifdata = image.getexif()
        for k, v in exifdata.items():
            print(k, v)
        return exifdata.get(271), exifdata.get(272), exifdata.get(36867), ifile

    elif re.search(r'heic$', str(ifile), re.IGNORECASE):  # if an Apple Heic file

        heif_file = pyheif.read_heif(str(ifile))

        for metadata in heif_file.metadata:

            if metadata['type'] == 'Exif':
                fstream = io.BytesIO(metadata['data'][6:])

        tags = exifread.process_file(fstream, details=False)

        for k, v in tags.items():
            print(k, v)

        return str(tags.get("Image Make")), str(tags.get("Image Model")), str(tags.get('EXIF DateTimeOriginal')), ifile

    elif re.search(r'CR2$|NEF$', str(ifile), re.IGNORECASE):  # for raw files. Canon and NIkon is this case.
        f = open(ifile, 'rb')  # open the file in bytes / ro mode

        # Return Exif tags
        tags = exifread.process_file(f, details=False)  # the "False" statement filters out a lot of comment data from
        # device maker
        make = tags['Image Make']
        model = tags['Image Model']
        orig_date = tags['EXIF DateTimeOriginal']

        return make, str(model).partition(' ')[2], str(orig_date)[:10], ifile  # some hoops to get the correct format

    else:
        logfile.write(ifile + " this file is corrupt")


# the routine to print out make , model etc.
def print_results(make, model, date_gen, image_name):
    print("{:20.20} \t {:<20} \t {:10.10} \t {}".format(str(make), str(model), str(date_gen), image_name))


for path in Path('YOUR PATH HERE').rglob('*'):  # the path will be different for a PC
    # uncomment the below if you simply want work specifically with image files
    # if re.search(r'\.jpg$|\.png$|\.bmp$|\.heic$|\.cr2$', str(path), re.IGNORECASE):
    if path.is_file():  # this simply validates that it's a file
        try:
            make, model, orig_date, image_name = get_exif_data(path)
            print_results(make, model, orig_date,
                          os.path.basename(image_name))  # path.baseline strips out file from path

        except:
            logfile.write(str(path) + " may be corrupted or not an image file \n")

logfile.close()  # close the log file

def image_metadata(path_f: str):
    register_heif_opener()

    img = Image.open(path_f)
    info_dict = {
            "Имя файла": os.path.split(path_f)[1],
            "Разрешение изображения": img.size,
            "Высота изображения": img.height,
            "Ширина изображения": img.width,
            "Формат изображения": img.format,
            "Режим изображения": img.mode,
            "Анимированное изображение": getattr(img, "is_animated", False),
            "Кадров в изображении": getattr(img, "n_frames", 1)
        }
    try:
        exif = {ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS}

        print(f'\n[+] Метаданные фото: {os.path.split(path_f)[1]:27}\n')
        for info in exif:
            if info == 'GPSInfo':
                print(f'{info:27}: lat {exif[info][2]} {exif[info][1]} - long {exif[info][4]} {exif[info][3]}')
            else:
                if isinstance(exif[info], bytes):
                    info_d = exif[info].decode()
                    print(f'{info:25}: {info_d}')
                else:
                    print(f'{info:25}: {exif[info]}')
    except AttributeError:
        print(f'\n[+] Информация о фото: {os.path.split(path_f)[1]:27}\n')
        for k, v in info_dict.items():
            print(f"{k:27}: {v}")
        exit(0)

def vid_aud_matadata(path_f: str):
    try:
        print(f'\n[+] Метаданные файла: {os.path.split(path_f)[-1]}\n')
        pprint(ffmpeg.probe(path_f)["streams"])
    except ffmpeg._run.Error:
        print('[-] Неподдерживаемый формат')

def get_metadata(path: str):
    if not os.path.exists(path):
        print('[-] Файла не существует')
    else:
        if path.endswith(".jpg"):
            image_metadata(path)
        elif path.endswith(".jpeg"):
            image_metadata(path)
        elif path.endswith(".heic"):
            image_metadata(path)
        elif path.endswith(".HEIC"):
            image_metadata(path)
        else:
            vid_aud_matadata(path)

# Пример использования

print(
    get_exif_data("IMG_7549.HEIC")
)

print(
    get_exif_data("IMG20241005053328.jpg")
)
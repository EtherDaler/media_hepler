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


def get_exif_data_ios(ifile):  # if the file is a standard image file
    if re.search(r'jpeg$|bmp$|png$|jpg$', str(ifile), re.IGNORECASE):
        image = Image.open(ifile)
        exifdata = image.getexif()
        for k, v in exifdata.items():
            print(k, v)
        return {"make": exifdata.get(271), "model": exifdata.get(272), "gen": exifdata.get(36867), "file": ifile}

    elif re.search(r'heic$', str(ifile), re.IGNORECASE):  # if an Apple Heic file

        heif_file = pyheif.read_heif(str(ifile))

        for metadata in heif_file.metadata:

            if metadata['type'] == 'Exif':
                fstream = io.BytesIO(metadata['data'][6:])

        tags = exifread.process_file(fstream, details=False)

        return tags

    elif re.search(r'CR2$|NEF$', str(ifile), re.IGNORECASE):  # for raw files. Canon and NIkon is this case.
        f = open(ifile, 'rb')  # open the file in bytes / ro mode

        # Return Exif tags
        tags = exifread.process_file(f, details=False)  # the "False" statement filters out a lot of comment data from
        # device maker
        make = tags['Image Make']
        model = tags['Image Model']
        orig_date = tags['EXIF DateTimeOriginal']

        return tags

    else:
        logfile = open('imagelog.txt', 'a')  # all files that are not printed out below will logged here
        logfile.write(ifile + " this file is corrupt")
        logfile.close()


# the routine to print out make , model etc.
def print_results(make, model, date_gen, image_name):
    print("{:20.20} \t {:<20} \t {:10.10} \t {}".format(str(make), str(model), str(date_gen), image_name))


def image_metadata_jpg(path_f: str):
    register_heif_opener()

    img = Image.open(path_f)
    try:
        exif = {ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS}
        info_dict = {}
        print(f'\n[+] Метаданные фото: {os.path.split(path_f)[1]:27}\n')
        for info in exif:
            if info == 'GPSInfo':
                info_dict[info] = f"{exif[info][2]} {exif[info][1]} - long {exif[info][4]} {exif[info][3]}"
                #print(f'{info:27}: lat {exif[info][2]} {exif[info][1]} - long {exif[info][4]} {exif[info][3]}')
            else:
                if isinstance(exif[info], bytes):
                    info_d = exif[info].decode()
                    info_dict[info] = info_d
                    #print(f'{info:25}: {info_d}')
                else:
                    info_dict[info]
                    #print(f'{info:25}: {exif[info]}')
    except AttributeError:
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
        print(f'\n[+] Информация о фото: {os.path.split(path_f)[1]:27}\n')
        for k, v in info_dict.items():
            print(f"{k:27}: {v}")
        exit(0)

def vid_aud_matadata(path_f: str):
    try:
        return ffmpeg.probe(path_f)["streams"]
    except:
        return None

def get_metadata(path: str):
    try:
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            return image_metadata_jpg(path)
        elif path.endswith(".heic") or path.endswith(".CR2") or path.endswith(".NEF"):
            return get_exif_data_ios(path)
        else:
            return vid_aud_matadata(path)
    except:
        return None

"""
print(
    get_exif_data_ios("IMG_7549.HEIC")
)

print(
    get_exif_data_ios("IMG20241005053328.jpg")
)
print(
    image_metadata_jpg("IMG20241005053328.jpg")
)
"""
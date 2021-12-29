from pathlib import Path
from django.contrib.auth.base_user import AbstractBaseUser
from hub.models import FileSharing, ItemPicture
from django.core import files
from io import BytesIO
import requests

import os, re


PRIVATE_PATH = Path(__file__).resolve().parent.parent / 'private'

def user_private_folder(user: AbstractBaseUser) -> Path:
    return PRIVATE_PATH / user.get_username()

def user_image_folder(user: AbstractBaseUser) -> Path:
    return user_private_folder(user) / 'pictures'

def user_files(user: AbstractBaseUser) -> Path:
    return user_private_folder(user).iterdir()

def user_images(user: AbstractBaseUser) -> Path:
    return user_image_folder(user).iterdir()

def user_file_path(user: AbstractBaseUser, file_path) -> Path:
    return user_private_folder(user) / file_path

def user_image_path(user: AbstractBaseUser, image_path) -> Path:
    return user_image_folder(user) / image_path

def is_valid_dataset_file(file) -> bool:
    name, extension = os.path.splitext(file.name)
    return extension == ".json"

def user_can_access_file(user: AbstractBaseUser, file: FileSharing):
    return file.shared_with is None or user.groups.filter(name=file.shared_with.name).exists()

_filename_ascii_strip_re = re.compile(r"[^A-Za-z0-9_.-]")

def secure_filename(filename: str) -> str:
    if isinstance(filename, str):
        from unicodedata import normalize

        filename = normalize("NFKD", filename).encode("ascii", "ignore")
        filename = filename.decode("ascii")
    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")
    filename = str(_filename_ascii_strip_re.sub("", "_".join(filename.split()))).strip("._")

    return filename

def download_images(file_path: Path):
    pics = ItemPicture.objects.filter(item__dataset__src=file_path)
    for pic in pics:
        pic.url
        try:
            resp = requests.get(pic.url)
        except:
            continue
        if resp.status_code != requests.codes.ok:
            print(f"could not reach {pic.url}")
            continue
        fp = BytesIO()
        fp.write(resp.content)
        file_name = pic.url.split("/")[-1]
        pic.photo.save(file_name, files.File(fp))
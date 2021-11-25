from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http.response import FileResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from pathlib import Path

import os, random, urllib, string

from . import utils
from .models import FileSharing


@login_required
def index(req: HttpRequest):
    context = { 'user': req.user }
    return render(req, 'hub/index.html', context)

def dataset(req: HttpRequest, dataset_link: str):
    file_sharing = FileSharing.objects.filter(share_link=dataset_link).first()
    if not utils.user_can_access_file(req.user, file_sharing):
        raise Http404("Not found")
    preloaded_dataset = '{}'
    with open(file_sharing.file_path, "r") as dataset_file:
        preloaded_dataset = dataset_file.read()
    context = { 'preloaded_dataset': preloaded_dataset }
    return render(req, 'hub/dataset.html', context)

def _post_dataset(req: HttpRequest):
    if not 'db-file-upload' in req.FILES:
        raise Exception("Invalid request, missing 'ed-file-upload' parameter.")
    file = req.FILES['db-file-upload']
    if not utils.is_valid_dataset_file(file):
        raise Exception("The provided file is invalid. Only Hazo dataset files are allowed.")
    else:
        file_name = utils.secure_filename(file.name)
        file_path = utils.user_file_path(req.user, file_name)
        default_storage.save(str(file_path), file)

@login_required
def databases(req: HttpRequest):
    if not utils.user_private_folder(req.user).exists():
        os.makedirs(utils.user_private_folder(req.user))
        os.makedirs(utils.user_image_folder(req.user))
    status = "ko"
    error_msg = ""
    if 'btn-upload' in req.POST:
        try:
            _post_dataset(req)
            status = "ok"
        except Exception as e:
            error_msg = str(e) 
    elif 'btn-delete' in req.POST:
        file_name = req.POST['btn-delete']
        file_path = utils.user_file_path(req.user, file_name)
        if file_path.exists():
            FileSharing.objects.filter(file_path=str(file_path)).delete()
            file_path.unlink()
            status = "ok"
        else:
            error_msg = f"file {file_name} does not exist"
    elif 'btn-share' in req.POST:
        file_name = req.POST['btn-share']
        file_full_path = utils.user_file_path(req.user, file_name)
        if not file_full_path.exists():
            error_msg = f"file '{file_name}' doesn't exist"
        else:
            share_link = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(48))
            file_sharing = FileSharing(owner=req.user, share_link=share_link, file_path=str(file_full_path))
            file_sharing.save()
    elif 'btn-unshare' in req.POST:
        file_name = req.POST['btn-unshare']
        file_full_path = utils.user_file_path(req.user, file_name)
        FileSharing.objects.filter(file_path=str(file_full_path)).delete()
    shared_files = { file.file_path: file for file in FileSharing.objects.all() }
    personal_files = []
    for file in utils.user_files(req.user):
        if not file.is_dir():
            is_shared = str(file) in shared_files
            link = ""
            if is_shared:
                link = shared_files.get(str(file)).share_link
            personal_files.append({'name': file.name, 'shared': is_shared, 'link': link  })
    context = {
        'status': status,
        'user': req.user,
        'error_msg': error_msg,
        'personal_files': personal_files,
    }
    return render(req, 'hub/databases.html', context)

@login_required
@csrf_exempt
def api_post_dataset(req: HttpRequest):
    try:
        _post_dataset(req)
        return JsonResponse({'status': "ok"})
    except Exception as e:
        return JsonResponse({'status': "ko", 'message': str(e) })

@login_required
@csrf_exempt
def api_upload_image(req: HttpRequest):
    if 'file-url' in req.POST:
        file_url = req.POST['file-url']
        url = urllib.parse.urlparse(file_url)
        file_name = utils.secure_filename(Path(url.path).name)
        file_path = utils.user_image_path(req.user, file_name)
        if not file_path.exists():
            r = urllib.request.Request(file_url, method='GET', headers={
                "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0"})
            # TODO: check file size and mime type
            try:
                with urllib.request.urlopen(r) as res, open(file_path, "wb") as out:
                    out.write(res.read())
            except Exception as e:
                return JsonResponse({"status": "ko", "message": f"Error opening {req.method} {file_url}: {str(e)}"})
        return JsonResponse({"status": "ok", "url": str(Path('picture') / req.user.username / file_name)})
    elif 'file' in req.FILES:
        file = req.FILES['file']
        if not file:
            return JsonResponse({"status": "ko", "message": "The provided file is invalid."})
        else:
            file_name = utils.secure_filename(file.filename)
            file_path = req.user.personal_file_path(file_name)
            file.save(str(file_path))
            return JsonResponse({"status": "ok", "url": str(Path('picture') / req.user.username / file_name)})
    else:
        return JsonResponse({"status": "ko", "message": "no file provided"})

@login_required
def private_files(req: HttpRequest, file_name: str):
    file_path = utils.user_file_path(req.user, file_name)
    if file_path.exists():
        FileResponse
        return FileResponse(open(file_path, "rb"), content_type="application/json", filename=file_name)
    else:
        raise Http404("Not found")

def shared_files(req: HttpRequest, share_link: str):
    file_sharing = FileSharing.objects.filter(share_link=share_link).first()
    if not utils.user_can_access_file(req.user, file_sharing) or file_sharing is None:
        raise Http404("Not found")
    else:
        return FileResponse(open(file_sharing.file_path, "rb"), content_type="application/json", filename=Path(file_sharing.file_path).name)

def picture(req: HttpRequest, username: str, filename: str):
    full_path = utils.PRIVATE_PATH / username / 'pictures' / filename
    if not full_path.exists():
        raise Http404()
    else:
        return FileResponse(open(full_path, "rb"), filename=filename)
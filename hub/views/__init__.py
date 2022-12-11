from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http.response import FileResponse, Http404, JsonResponse
from django.db.models import Count, F
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from pathlib import Path

import urllib

from . import databases, dict, identify, utils
from ..models import Dataset, FileSharing, TaxonState


@login_required
def index(req: HttpRequest):
    context = { 'user': req.user }
    return render(req, 'hub/index.html', context)

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

@login_required
@csrf_exempt
def api_get_states_uses_count(req: HttpRequest, dataset_name: str, state_ref_str: str):
    dataset: Dataset = Dataset.objects.filter(name=dataset_name).first()
    if dataset is None:
        return JsonResponse({ 'status': 'ko' })
    state_refs = state_ref_str.split(",")
    states_taxon_count = TaxonState.objects.filter(state__item__ref__in=state_refs).values('state__item__ref').annotate(num_taxons=Count('taxon'))

    return JsonResponse({ count['state__item__ref']: count['num_taxons'] for count in states_taxon_count })

@login_required
@csrf_exempt
def api_get_taxons_with_states(req: HttpRequest, dataset_name: str, state_ref_str: str):
    dataset: Dataset = Dataset.objects.filter(name=dataset_name).first()
    if dataset is None:
        return JsonResponse({ 'status': 'ko' })
    state_refs = state_ref_str.split(",")
    taxons_with_states = TaxonState.objects.filter(state__item__ref__in=state_refs).annotate(
        state_ref=F('state__item__ref'), 
        taxon_ref=F('taxon__item__ref')).values('state_ref', 'taxon_ref')

    return JsonResponse({ 'status': 'ok', 'taxons': list(taxons_with_states) })
    
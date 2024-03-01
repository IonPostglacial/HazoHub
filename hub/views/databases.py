from io import StringIO
from typing import List

from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import HttpRequest
from django.http.response import Http404, JsonResponse, FileResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from . import utils
from ..codec.hazojson import import_hazo
from ..models import Character, Dataset, DatasetVersion, FileSharing, Taxon, TaxonState

import csv
import os
import random
import string
import datetime
import git


def _post_dataset(req: HttpRequest):
    if not 'db-file-upload' in req.FILES:
        raise Exception("Invalid request, missing 'ed-file-upload' parameter.")
    file = req.FILES['db-file-upload']
    if not utils.is_valid_dataset_file(file):
        raise Exception(
            "The provided file is invalid. Only Hazo dataset files are allowed.")
    else:
        file_name = utils.secure_filename(file.name)
        file_path = utils.user_file_path(req.user, file_name)
        file_path_s = str(file_path)
        if default_storage.exists(file_path_s):
            default_storage.delete(file_path_s)
        default_storage.save(file_path_s, file)
        folder = utils.user_private_folder(req.user)
        repo = git.Repo(folder)
        repo.index.add([file_path_s])
        repo.index.commit(f"changes to dataset {file.name}")


def details(req: HttpRequest, dataset_link: str):
    file_sharing = FileSharing.objects.filter(share_link=dataset_link).first()
    if not utils.user_can_access_file(req.user, file_sharing):
        raise Http404("Not found")
    preloaded_dataset = '{}'
    with open(file_sharing.file_path, "r") as dataset_file:
        preloaded_dataset = dataset_file.read()
    context = {'preloaded_dataset': preloaded_dataset}
    return render(req, 'hub/dataset_details.html', context)


@login_required
def list_view(req: HttpRequest):
    if not utils.user_private_folder(req.user).exists():
        private_folder = utils.user_private_folder(req.user)
        os.makedirs(private_folder)
        git.Repo.init(private_folder)
        os.makedirs(utils.user_image_folder(req.user))
    status = "ko"
    error_msg = ""
    if 'btn-upload' in req.POST:
        try:
            _post_dataset(req)
            status = "ok"
        except Exception as e:
            error_msg = str(e)
    elif 'btn-reimport' in req.POST:
        file_name = req.POST['btn-reimport']
        file_path = utils.user_file_path(req.user, file_name)
        import_hazo(file_path)
    elif 'btn-import' in req.POST:
        file_name = req.POST['btn-import']
        file_path = utils.user_file_path(req.user, file_name)
        import_hazo(file_path)
    elif 'btn-download-img' in req.POST:
        file_name = req.POST['btn-download-img']
        file_path = utils.user_file_path(req.user, file_name)
        utils.download_images(file_path)
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
    sort_key = req.POST.get('set-sort-by', req.POST.get('sort-by'))
    print("sort_key", sort_key)
    if sort_key not in ('last_mod', 'name'):
        sort_key = 'name'
    shared_files = { file.file_path: file for file in FileSharing.objects.all() }
    imported_files = { path for path in Dataset.objects.all().values_list('src', flat=True) }
    personal_files = []
    for file in utils.user_files(req.user):
        if not file.is_dir():
            is_imported = str(file) in imported_files
            is_shared = str(file) in shared_files
            link = ""
            if is_shared:
                link = shared_files.get(str(file)).share_link
            personal_files.append({ 'last_mod': datetime.datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M"), 'name': file.name, 'shared': is_shared, 'imported': is_imported, 'link': link })
    personal_files.sort(key=lambda f: f[sort_key].lower())
    context = {
        'status': status,
        'user': req.user,
        'sort_key': sort_key,
        'error_msg': error_msg,
        'personal_files': personal_files,
    }
    return render(req, 'hub/dataset_list.html', context)


def _filter_by_charids(obj, char_ids: List[str]):
    for id in char_ids:
        obj = obj.filter(state__character__item__id=id)
    return obj

def _commit_date(commit):
    return datetime.datetime.fromtimestamp(commit.authored_date).strftime("%Y-%m-%d %H:%M")

@login_required
def versions(req: HttpRequest, file_name: str):
    file_path = utils.user_file_path(req.user, file_name)
    folder = utils.user_private_folder(req.user)
    repo = git.Repo(folder)
    if 'revert' in req.POST:
        revision = req.POST['revert']
        repo.git.checkout(revision, file_path)
        repo.index.add([file_path])
        commit = repo.commit(revision)
        repo.index.commit(f"revert {file_name} to version from {_commit_date(commit)}: '{commit.message}'")
    last_commits = []
    for commit in repo.iter_commits(None, file_path, max_count=50):
        last_commits.append({ 
            'date': _commit_date(commit), 
            'message': commit.message,
            'hexsha': commit.hexsha
        })

    return render(req, 'hub/versions.html', {
        'dataset_name': file_path.stem,
        'file_name': file_name,
        'file_path': file_path,
        'last_commits': last_commits,
    })

@login_required
def summary(req: HttpRequest, file_name: str):
    file_path = utils.user_file_path(req.user, file_name)
    dataset: Dataset = Dataset.objects.filter(src=file_path).first()
    if dataset is None:
        raise Http404(f"There is no dataset named {file_path}")
    version = DatasetVersion.last_for_dataset()
    characters = Character.from_dataset_version(version)
    selected_character_ids = list(map(int, req.POST.getlist('character')))
    if selected_character_ids:
        states_taxon_count = _filter_by_charids(TaxonState.objects, selected_character_ids)
        states_taxon_count = states_taxon_count.values('state__item__name').annotate(num_taxons=Count('taxon'))
    else:
        states_taxon_count = []

    return render(req, 'hub/dataset_summary.html', {
        'dataset_name': file_path.stem,
        'file_name': file_name,
        'characters': characters,
        'selected_character_ids': selected_character_ids,
        'selected_character_ids_query': f"?{'&'.join(f'charid={id}' for id in selected_character_ids)}" if selected_character_ids else '',
        'states_taxon_count': states_taxon_count,
    })


@login_required
def summary_csv(req: HttpRequest, file_name: str):
    if 'charid' in req.GET:
        selected_character_ids = [int(id) for id in req.GET.getlist('charid')]
    else:
        selected_character_ids = []
    file_path = utils.user_file_path(req.user, file_name)
    dataset: Dataset = Dataset.objects.filter(src=file_path).first()
    if dataset is None:
        raise Http404(f"There is no dataset named {file_path}")
    states_taxons = _filter_by_charids(TaxonState.objects, selected_character_ids).select_related('state__item', 'taxon__item').prefetch_related('taxon__item__itemname_set')
    buffer = StringIO()
    w = csv.writer(buffer)
    w.writerow(['taxon', 'author', 'NV'])
    for state_taxon in states_taxons:
        names = {
            name.lang.code: name.text for name in state_taxon.taxon.item.itemname_set.all()}
        w.writerow([state_taxon.taxon.item.name,
                   state_taxon.taxon.author, names.get('V')])
    return FileResponse(buffer.getvalue())


@login_required
def taxon(req: HttpRequest, id: str):
    taxon = Taxon.objects.select_related(
        'item').prefetch_related('item__pictures').get(item_id=id)
    if not taxon:
        return Http404("There is no taxon with this id")
    return render(req, 'hub/dataset_taxon.html', {
        'taxon': taxon
    })


@login_required
@csrf_exempt
def api_post_dataset(req: HttpRequest):
    try:
        _post_dataset(req)
        return JsonResponse({'status': "ok"})
    except Exception as e:
        return JsonResponse({'status': "ko", 'message': str(e)})

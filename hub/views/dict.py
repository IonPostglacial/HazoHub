import io
from django.core.paginator import Page, Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http.response import HttpResponseBadRequest
from django.shortcuts import redirect, render

import codecs
from ..codec import dictionarycsv
from ..models import DictionaryEntry, DictionaryEntryByLang, DictionaryOrgan, Language


def _filtered_entry_list(req: HttpRequest):
    if 'filter' in req.GET:
        dictionary_entries = DictionaryEntryByLang.objects.order_by('entry').filter(name__startswith=req.GET['filter'])
    else:
        dictionary_entries = DictionaryEntryByLang.objects.order_by('entry').all()
    paginator = Paginator(dictionary_entries, 25*3)
    page_number = req.GET.get('page')
    page_obj = paginator.get_page(page_number)
    entries = []
    last_entry = None
    for entry_by_lang in page_obj.object_list:
        if last_entry is None or last_entry['id'] != entry_by_lang.entry.id:
            last_entry = {
                'id': entry_by_lang.entry.id,
                'number': entry_by_lang.entry.number if entry_by_lang.entry.number is not None else '',
                'names': {},
            }
            entries.append(last_entry)
        last_entry['names'][entry_by_lang.lang.code] = entry_by_lang.name
    return entries, page_obj

def _entry_details(req: HttpRequest, id):
    entry = DictionaryEntry.objects.get(id=id)
    organs = DictionaryOrgan.objects.all()
    names = {}
    definitions = {}
    for entry_lang in entry.dictionaryentrybylang_set.all():
        names[entry_lang.lang.code] = entry_lang.name
        definitions[entry_lang.lang.code] = entry_lang.definition
    return {
        'organs': organs,
        'entry': {
            'id': id,
            'names': names,
            'illustration': entry.url,
            'organ': entry.organ,
            'number': entry.number,
            'definitions': definitions,
        }
    }

@login_required
def entry_list(req: HttpRequest):
    if 'add-entry' in req.POST and 'new-entry' in req.POST:
        new_entry_name = req.POST['new-entry']
        new_entry = DictionaryEntry.objects.create()
        DictionaryEntryByLang.objects.create(entry=new_entry, lang=Language(code="EN"), name=new_entry_name)
        DictionaryEntryByLang.objects.create(entry=new_entry, lang=Language(code="FR"), name="")
        DictionaryEntryByLang.objects.create(entry=new_entry, lang=Language(code="CN"), name="")
        return redirect('dictentrydetails', new_entry.id)
    elif 'import-csv' in req.POST:
        try:
            if not 'csv-file' in req.FILES:
                return HttpResponseBadRequest("Invalid request, missing 'csv-file' parameter.")
            file = codecs.EncodedFile(req.FILES['csv-file'], "utf-8")
            with io.TextIOWrapper(file, encoding="utf-8") as text_file:
                dictionarycsv.load(text_file)
        except Exception as e:
            return HttpResponseBadRequest(e)
    elif 'edit-entry' in req.POST:
        entry_id = req.POST['edit-entry']
        entry = DictionaryEntry.objects.get(id=entry_id)
        entry.url = req.POST.get('illustration', "")
        organ_id = req.POST.get('organ')
        entry.organ = DictionaryOrgan(id=organ_id) if organ_id is not None else None
        try:
            nb = int(req.POST['number'])
        except:
            nb = None
        entry.number = nb
        entry.save()
        for lang in ("CN", "EN", "FR"):
            DictionaryEntryByLang.objects.filter(entry=entry, lang=Language(code=lang)).update(
                name=req.POST.get(f'name-{lang}', ""),
                definition=req.POST.get(f'def-{lang}', ""))
    elif 'del-entry' in req.POST:
        DictionaryEntry.objects.filter(id=req.POST['del-entry']).delete()

    entries, page_obj = _filtered_entry_list(req)
    filter = req.GET.get('filter')
    return render(req, 'hub/dict_entry_list.html', {
        'entries': entries,
        'page_obj': page_obj,
        'filter': f'&filter={filter}' if filter is not None else '',
    })

@login_required
def filtered_list(req: HttpRequest):
    entries, page_obj = _filtered_entry_list(req)
    filter = req.GET.get('filter')
    return render(req, 'hub/fragments/dict_list.html', {
        'entries': entries,
        'page_obj': page_obj,
        'filter': f'&filter={filter}' if filter is not None else '',
    })

@login_required
def entry_details(req: HttpRequest, id):
    entry_details = _entry_details(req, id)
    return render(req, 'hub/dict_entry_details.html', entry_details)

@login_required
def entry_details_fragment(req: HttpRequest, id):
    entry_details = _entry_details(req, id)
    return render(req, 'hub/fragments/dict_details.html', entry_details)
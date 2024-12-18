import io
from django.core.paginator import Page, Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http.response import HttpResponseBadRequest, FileResponse
from django.shortcuts import redirect, render

import codecs
import dataclasses
from ..codec import dictionarycsv
from ..models import DictionaryEntry, DictionaryEntryByLang, DictionaryOrgan, Language


@dataclasses.dataclass
class Entry:
    id: int
    number: str
    names: dict

def _filtered_entry_list(req: HttpRequest):
    dict_entries = DictionaryEntry.objects.prefetch_related('translations').order_by('number')
    if 'filter' in req.GET:
        dictionary_entries = dict_entries.filter(translations__name__startswith=req.GET['filter']).distinct()
    else:
        dictionary_entries = dict_entries.distinct()
    paginator = Paginator(dictionary_entries, 250)
    page_number = req.GET.get('page')
    page_obj = paginator.get_page(page_number)
    entries = []
    for entry in page_obj.object_list:
        entries.append(Entry(
            id=entry.id, 
            number=entry.number if entry.number is not None else '',
            names={ t.lang.code: t.name for t in entry.translations.all() }
        ))
    return entries, page_obj

def _entry_details(req: HttpRequest, entry_id):
    entry = DictionaryEntry.objects.prefetch_related('translations').get(id=entry_id)
    organs = DictionaryOrgan.objects.all()
    languages = Language.objects.all()
    names = {}
    definitions = {}
    for lang in languages:
        names[lang.code] = ""
        definitions[lang.code] = ""
    for entry_lang in entry.translations.all():
        names[entry_lang.lang.code] = entry_lang.name
        definitions[entry_lang.lang.code] = entry_lang.definition

    return {
        'organs': organs,
        'entry': {
            'id': entry_id,
            'names': names,
            'illustration': entry.url,
            'organ': entry.organ,
            'number': entry.number,
            'definitions': definitions,
        }
    }

@login_required
def export(req: HttpRequest):
    return FileResponse(dictionarycsv.export(), content_type="text/csv", filename="export.csv")

@login_required
def entry_list(req: HttpRequest):
    if 'add-entry' in req.POST and 'new-entry' in req.POST:
        new_entry_name = req.POST['new-entry']
        new_entry = DictionaryEntry.objects.create()
        DictionaryEntryByLang.objects.create(entry=new_entry, lang=Language(code="S"), name=new_entry_name)
        DictionaryEntryByLang.objects.create(entry=new_entry, lang=Language(code="V"), name="")
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
    elif 'replace-csv' in req.POST:
        try:
            if not 'csv-file' in req.FILES:
                return HttpResponseBadRequest("Invalid request, missing 'csv-file' parameter.")
            file = codecs.EncodedFile(req.FILES['csv-file'], "utf-8")
            with io.TextIOWrapper(file, encoding="utf-8") as text_file:
                dictionarycsv.replace(text_file)
        except Exception as e:
            return HttpResponseBadRequest(e)
    elif 'edit-entry' in req.POST:
        languages = Language.objects.all()
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
        for lang in languages:
            entry_name = DictionaryEntryByLang.objects.filter(entry=entry, lang=Language(code=lang.code))
            name_for_lang = req.POST.get(f'name{lang.code}', "")
            definition_for_lang = req.POST.get(f'def-{lang.code}', "")
            if entry_name.count() > 0:
                entry_name.update(
                    name=name_for_lang,
                    definition=definition_for_lang)
            else:
                DictionaryEntryByLang.objects.create(
                    entry=entry, 
                    lang=Language(code=lang.code),
                    name=name_for_lang,
                    definition=definition_for_lang)
    elif 'del-entry' in req.POST:
        DictionaryEntry.objects.filter(id=req.POST['del-entry']).delete()

    entries, page_obj = _filtered_entry_list(req)
    filter = req.GET.get('filter')
    return render(req, 'hub/dict_entry_list.html', {
        'entries': entries,
        'page_obj': page_obj,
        'filter': f'&filter={filter}' if filter is not None else '',
    })

def _filtered_list(req: HttpRequest, template):
    entries, page_obj = _filtered_entry_list(req)
    filter = req.GET.get('filter')
    return render(req, template, {
        'entries': entries,
        'page_obj': page_obj,
        'filter': f'&filter={filter}' if filter is not None else '',
    })

@login_required
def filtered_list(req: HttpRequest):
    return _filtered_list(req, 'hub/fragments/dict_list.html')

@login_required
def filtered_list_entries(req: HttpRequest):
    return _filtered_list(req, 'hub/fragments/dict_list_entries.html')

@login_required
def delete_from_list(req: HttpRequest, id):
    DictionaryEntry.objects.filter(id=id).delete()
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
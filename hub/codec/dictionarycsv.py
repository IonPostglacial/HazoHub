import csv
from io import StringIO

from datetime import datetime
from django.core.files.base import File
from django.db.models.aggregates import Max
from hub.models import DictionaryEntry, DictionaryEntryByLang, DictionaryVersion, Language

def replace(input: File):
    DictionaryEntry.objects.all().delete()
    load(input)

def load(input: File):
    r = csv.reader(input, delimiter=',', quotechar='"')
    entries_by_lang = []
    current_version = DictionaryVersion.objects.aggregate(Max('number'))
    new_version = DictionaryVersion.objects.create(number=(current_version['number__max'] or 0) + 1, created_on=datetime.now())
    for i, line in enumerate(r):
        if i > 0:
            [nbr, V, S, FR, EN, CN, defV, defS, defFR, defEN, defCN, organ, url] = line
            try:
                nbr_int = int(nbr)
            except:
                nbr_int = None
            new_entry = DictionaryEntry.objects.create(creation_version=new_version, url=url, number=nbr_int)
            entries_by_lang.append(DictionaryEntryByLang(entry=new_entry,lang=Language(code="V"), name=V, definition=defV))
            entries_by_lang.append(DictionaryEntryByLang(entry=new_entry,lang=Language(code="S"), name=S, definition=defS))
            entries_by_lang.append(DictionaryEntryByLang(entry=new_entry,lang=Language(code="EN"), name=EN, definition=defEN))
            entries_by_lang.append(DictionaryEntryByLang(entry=new_entry, lang=Language(code="CN"), name=CN, definition=defCN))
            entries_by_lang.append(DictionaryEntryByLang(entry=new_entry, lang=Language(code="FR"), name=FR, definition=defFR))
    DictionaryEntryByLang.objects.bulk_create(entries_by_lang)

def export():
    buffer = StringIO()
    w = csv.writer(buffer)
    w.writerow(['nbr', 'V', 'S', 'FR', 'EN', 'CN', 'defV', 'defS', 'defFR', 'defEN', 'defCN', 'organ', 'url'])
    for entry in DictionaryEntry.objects.prefetch_related('translations').prefetch_related('translations__lang'):
        nameV, nameS, nameFR, nameEN, nameCN = "", "", "", "", ""
        defV, defS, defCN, defEN, defFR = "", "", "", "", ""
        for tr in entry.translations.all():
            print(tr.lang, tr.name, tr.definition)
            match tr.lang.code:
                case "V":
                    nameV = tr.name
                    defV = tr.definition
                case "S":
                    nameS = tr.name
                    defS = tr.definition
                case "FR":
                    nameFR = tr.name
                    defFR = tr.definition
                case "EN":
                    nameEN = tr.name
                    defEN = tr.definition
                case "CN":
                    nameCN = tr.name
                    defCN = tr.definition
        w.writerow([entry.number, nameV, nameS, nameFR, nameEN, nameCN, defV, defS, defFR, defEN, defCN, entry.organ, entry.url])
    return buffer.getvalue()
import csv

from datetime import datetime
from django.core.files.base import File
from django.db.models.aggregates import Max
from hub.models import DictionaryEntry, DictionaryEntryByLang, DictionaryVersion, Language


def load(input: File):
    r = csv.reader(input, delimiter=',', quotechar='"')
    entries_by_lang = []
    current_version = DictionaryVersion.objects.aggregate(Max('number'))
    new_version = DictionaryVersion.objects.create(number=current_version['number__max'] + 1, created_on=datetime.now())
    for i, line in enumerate(r):
        if i > 0:
            [nbr, organ, FR, EN, CN, defCN, defEN, defFR, url] = line
            try:
                nbr_int = int(nbr)
            except:
                nbr_int = None
            new_entry = DictionaryEntry.objects.create(creation_version=new_version, url=url, number=nbr_int)
            entries_by_lang.append(DictionaryEntryByLang(entry=new_entry,lang=Language(code="EN"), name=EN, definition=defEN))
            entries_by_lang.append(DictionaryEntryByLang(entry=new_entry, lang=Language(code="CN"), name=CN, definition=defCN))
            entries_by_lang.append(DictionaryEntryByLang(entry=new_entry, lang=Language(code="FR"), name=FR, definition=defFR))
    DictionaryEntryByLang.objects.bulk_create(entries_by_lang)
from django.contrib import admin
from .models import Book, Dataset, DictionaryEntry, DictionaryEntryByLang, DictionaryOrgan, DictionaryVersion, ExtraField, FileSharing, Icon, Language


admin.site.register(Dataset)
admin.site.register(FileSharing)
admin.site.register(Language)
admin.site.register(Icon)
admin.site.register(ExtraField)
admin.site.register(Book)
admin.site.register(DictionaryVersion)
admin.site.register(DictionaryEntry)
admin.site.register(DictionaryEntryByLang)
admin.site.register(DictionaryOrgan)
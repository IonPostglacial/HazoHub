from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import FileResponse
from django.shortcuts import render
from . import utils


@login_required
def bibtex(req: HttpRequest):
    if 'bibtex-file' in req.FILES:
        file = req.FILES['bibtex-file']
        csvcontent = utils.bibtex_to_csv(file)
        return FileResponse(csvcontent, filename="biblio.csv", content_type="text/csv")
    else:
        return render(req, 'biblio/biblio.html', {})

@login_required
def texcite(req: HttpRequest):
    if 'bibtex-file' in req.FILES and 'word-text' in req.POST:
        file = req.FILES['bibtex-file']
        text = req.POST['word-text']
        text = utils.auto_cite(file, text)
    else:
        text = "Enter biblio and text."
    return render(req, 'biblio/texcite.html', { 'text': text })
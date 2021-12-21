from django.urls import path
from . import views

urlpatterns= [
    path('to-tex', views.bibtex, name="bibtex"),
    path('autocite', views.texcite, name="autocite"),
]
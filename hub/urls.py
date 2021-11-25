from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('databases', views.databases, name="databases"),
    path('dataset/<str:dataset_link>', views.dataset, name="dataset"),
    path('api/datasets', views.api_post_dataset, name="postdataset"),
    path('api/upload-img', views.api_upload_image, name="uploadimage"),
    path('private/<str:file_name>', views.private_files, name="privatefiles"),
    path('shared/<str:share_link>', views.shared_files, name="sharedfiles"),
    path('picture/<str:username>/<str:filename>', views.picture, name="picture"),
]
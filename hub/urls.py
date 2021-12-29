from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('databases', views.databases, name="databases"),
    path('summary/<str:file_name>', views.dataset_summary, name="summary"),
    path('identify/<str:file_name>/characters-list', views.characters_list, name="characterslist"),
    path('identify/<str:file_name>/characters-list/<int:in_character>', views.characters_list, name="characterslistin"),
    path('identify/<str:file_name>/states-list/<int:in_character>', views.states_list, name="stateslist"),
    path('dataset/<str:dataset_link>', views.dataset, name="dataset"),
    path('api/datasets', views.api_post_dataset, name="postdataset"),
    path('api/upload-img', views.api_upload_image, name="uploadimage"),
    path('api/states-taxons-num/<str:dataset_name>/<str:state_ref_str>', views.api_get_states_uses_count, name="statesuses"),
    path('api/taxons-with-states/<str:dataset_name>/<str:state_ref_str>', views.api_get_taxons_with_states, name="taxonswithstate"),
    path('private/<str:file_name>', views.private_files, name="privatefiles"),
    path('shared/<str:share_link>', views.shared_files, name="sharedfiles"),
    path('picture/<str:username>/<str:filename>', views.picture, name="picture"),
]
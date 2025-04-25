from django.urls import path
from . import views
# from views import characters, dataset, dict


urlpatterns = [
    path('', views.index, name="index"),
    path('databases', views.databases.list_view, name="datasetlist"),
    path('taxon/<int:id>', views.databases.taxon, name="taxon"),
    path('versions/<str:file_name>', views.databases.versions, name="versions"),
    path('summary/<str:file_name>', views.databases.summary, name="summary"),
    path('summary/<str:file_name>/export-csv', views.databases.summary_csv, name="summarycsv"),
    path('dictionary', views.dict.entry_list, name="dictentrylist"),
    path('dictionary/delete/<int:id>', views.dict.delete_from_list, name="dictentrydeletefromlist"),
    path('dictionary-export.csv', views.dict.export, name="dictionaryexport"),
    path('dictionary-filtered-list', views.dict.filtered_list, name="dictentryfilteredlist"),
    path('dictionary-filtered-list-entries', views.dict.filtered_list_entries, name="dictentryfilteredlistentries"),
    path('dictionary/<int:id>', views.dict.entry_details, name="dictentrydetails"),
    path('dictionary/<int:id>/fragment', views.dict.entry_details_fragment, name="dictentrydetailsfragment"),
    path('identify/<str:file_name>/characters-list', views.identify.list_view, name="charlist"),
    path('identify/<str:file_name>/characters-list/<int:in_character>', views.identify.list_view, name="charlistin"),
    path('identify/<str:file_name>/characters-states-list/<int:in_character>', views.identify.states_list, name="charstateslist"),
    path('api/datasets', views.databases.api_post_dataset, name="postdataset"),
    path('api/upload-img', views.api_upload_image, name="uploadimage"),
    path('api/states-taxons-num/<str:dataset_name>/<str:state_ref_str>', views.api_get_states_uses_count, name="statesuses"),
    path('api/taxons-with-states/<str:dataset_name>/<str:state_ref_str>', views.api_get_taxons_with_states, name="taxonswithstate"),
    path('private/<str:file_name>', views.private_files, name="privatefiles"),
    path('shared/<str:share_link>', views.shared_files, name="sharedfiles"),
    path('picture/<str:username>/<str:filename>', views.picture, name="picture"),
]
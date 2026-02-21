"""
URL routing for the data transformation wizard.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.wizard_view, name='data_transformation'),
    path('upload/', views.upload_files, name='dt_upload'),
    path('start-blast/', views.start_blast_search, name='dt_start_blast'),
    path('blast-results/<str:task_id>/', views.get_blast_results, name='dt_blast_results'),
    path('step2/', views.get_step2_form, name='dt_step2'),
    path('upload-groups/', views.upload_group_json, name='dt_upload_groups'),
    path('submit-groups/', views.submit_groups, name='dt_submit_groups'),
    path('skip-groups/', views.skip_groups, name='dt_skip_groups'),
    path('step3/', views.get_step3_form, name='dt_step3'),
    path('start-uniprot/', views.start_uniprot_fetch, name='dt_start_uniprot'),
    path('save-uniprot/', views.save_uniprot_results, name='dt_save_uniprot'),
    path('submit-proteins/', views.submit_protein_decisions, name='dt_submit_proteins'),
    path('download-protein-map/', views.download_protein_map, name='dt_download_protein_map'),
    path('upload-protein-map/', views.upload_protein_map, name='dt_upload_protein_map'),
    path('skip-proteins/', views.skip_protein_mapping, name='dt_skip_proteins'),
    path('process/', views.process_data, name='dt_process'),
    path('view/<str:export_type>/', views.view_export, name='dt_view'),
    path('download/<str:export_type>/', views.download_export, name='dt_download'),
    path('cleanup/', views.cleanup, name='dt_cleanup'),
]

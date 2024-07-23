from django.urls import include, re_path, path
from django.contrib import admin
from . import views

urlpatterns = [
    re_path(r'^$', views.peptide_search, name='index'),
    re_path(r'^pepex/$', views.pepex_tool, name='pepex'),
    re_path(r'^add_proteins/$', views.add_proteins_tool, name='add_proteins'),
    re_path(r'^download_fasta_file/$', views.download_fasta_file, name='download_fasta_file'),
    re_path(r'^tsv_search_results/', views.tsv_search_results, name='tsv_search_results'),
    re_path(r'^peptide_db_csv/$', views.peptide_db_csv, name='peptide_db_csv'),
    re_path(r'^peptide_search/$', views.peptide_search, name='peptide_search'),
    re_path(r'^about_us/$', views.about_us, name='about_us'),
    re_path(r'^test/$', views.test_page, name='test_page'),
    re_path(r'^admin/', admin.site.urls),
    re_path('get_protein_list/', views.get_protein_list_view, name='get_protein_list'),
    path('start-work/', views.start_work, name='start_work'),
    path('check-progress/<str:task_id>/', views.check_progress, name='check_progress'),
]

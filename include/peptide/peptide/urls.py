from django.urls import include, re_path
from django.contrib import admin
from peptide import views

urlpatterns = [
    re_path(r'^$', views.peptide_search, name='index'),
    #re_path(r'^homology_search/$', views.homology_search, name='homology_search'),
    re_path(r'^pepex/$', views.pepex_tool, name='pepex'),
    re_path(r'^add_proteins/$', views.add_proteins_tool, name='add_proteins'),
    re_path(r'^protein_headers/$', views.protein_headers, name='protein_headers'),
    re_path(r'^tsv_search_results/', views.tsv_search_results, name='tsv_search_results'),
    #re_path(r'^peptide_db/$', views.peptide_db, name='peptide_db'),
    re_path(r'^peptide_db_csv/$', views.peptide_db_csv, name='peptide_db_csv'),
    re_path(r'^peptide_search/$', views.peptide_search, name='peptide_search'),
    #re_path(r'^peptide_multi_search/$', views.peptide_multi_search, name='peptide_multi_search'),
    #re_path(r'^contact/$', views.contact, name='contact'),
    re_path(r'^about_us/$', views.about_us, name='about_us'),
    re_path(r'^admin/', admin.site.urls),

]

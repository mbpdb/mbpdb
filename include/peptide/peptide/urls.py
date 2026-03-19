from django.urls import include, re_path, path
from django.contrib import admin
from . import views
import uuid
urlpatterns = [
    re_path(r'^$', views.peptide_search, name='index'),
    re_path(r'^pepex/$', views.pepex_tool, name='pepex'),
    re_path(r'^add_proteins/$', views.add_proteins_tool, name='add_proteins'),
    re_path(r'^download_fasta_file/$', views.download_fasta_file, name='download_fasta_file'),
    re_path(r'^tsv_search_results/', views.tsv_search_results, name='tsv_search_results'),
    re_path(r'^peptide_db_csv/$', views.peptide_db_csv, name='peptide_db_csv'),
    re_path(r'^peptide_search/$', views.peptide_search, name='peptide_search'),
    re_path(r'^about_us/$', views.about_us, name='about_us'),
    path('results-section/<uuid:task_id>/', views.results_section, name='results_section'),
    re_path(r'^test/$', views.test, name='test_page'),
    re_path(r'^admin/', admin.site.urls),
    re_path('get_protein_list/', views.get_protein_list_view, name='get_protein_list'),
    path('start-work/', views.start_work, name='start_work'),
    path('check-progress/<str:task_id>/', views.check_progress, name='check_progress'),
    path('get-active-tasks/', views.get_active_tasks, name='get_active_tasks'),
    path('return_render_results/<uuid:task_id>/', views.return_render_results, name='return_render_results'),
    path('heatmap/', include('peptide.heatmap_viz.urls', namespace='heatmap_viz')),
    path('data_transformation/', include('peptide.data_transformation.urls')),
    path('data_analysis/', include('peptide.data_analysis.urls', namespace='data_analysis')),
    path('all-peptides/', views.all_peptides_view, name='all_peptides'),
    path('bioactivity-viz/proteins/', views.bioactivity_viz_proteins, name='bioactivity_viz_proteins'),
    path('bioactivity-viz/plot/', views.bioactivity_viz_plot, name='bioactivity_viz_plot'),
    path('peptiline/', views.peptiline_landing, name='peptiline_landing'),
    path('supplementals_tables_and_figures/', views.supplementals_tables_and_figures, name='supplementals_tables_and_figures'),
    path('zukaitis_2026/', views.zukaitis_2026, name='zukaitis_2026'),
]


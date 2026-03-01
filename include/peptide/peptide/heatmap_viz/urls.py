from django.urls import path
from . import views

app_name = 'heatmap_viz'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload, name='upload'),
    path('fetch-sequence/', views.fetch_sequence, name='fetch_sequence'),
    path('get-specific-options/', views.get_specific_options, name='get_specific_options'),
    path('plot/', views.plot, name='plot'),
    path('download-plot/', views.download_plot, name='download_plot'),
]

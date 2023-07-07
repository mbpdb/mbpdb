from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', 'peptide.views.peptide_search', name='index'),
    url(r'^homology_search/$', 'peptide.views.homology_search', name='homology_search'),
    url(r'^skyline/$', 'peptide.views.skyline', name='skyline'),
    url(r'^skyline_auto/$', 'peptide.views.skyline_auto', name='skyline_auto'),
    url(r'^remove_domains_tool/$', 'peptide.views.remove_domains_tool', name='remove_domains_tool'),
    url(r'^pepex/$', 'peptide.views.pepex_tool', name='pepex'),
    url(r'^add_proteins/$', 'peptide.views.add_proteins_tool', name='add_proteins'),
    url(r'^protein_headers/$', 'peptide.views.protein_headers', name='protein_headers'),
    url(r'^tsv_search_results/', 'peptide.views.tsv_search_results', name='tsv_search_results'),
    url(r'^peptide_db/$', 'peptide.views.peptide_db', name='peptide_db'),
    url(r'^peptide_db_csv/$', 'peptide.views.peptide_db_csv', name='peptide_db_csv'),
    url(r'^peptide_search/$', 'peptide.views.peptide_search', name='peptide_search'),
    url(r'^peptide_multi_search/$', 'peptide.views.peptide_multi_search', name='peptide_multi_search'),
    url(r'^contact/$', 'peptide.views.contact', name='contact'),
    url(r'^admin/', include(admin.site.urls)),
)

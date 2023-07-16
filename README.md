# Milk Bioactive Peptide Database  
## https://mbpdb.nws.oregonstate.edu/  
# Software versions of the original application   
## Old versions:  
-SQLite 3.7.17  
-CentOS 7.1.1503 server.  
-Python 2.7.5   
-Django 1.9.7   
-Apache 2.4.6.   
-Blast+ 2.5.0.  

## Package    Version  
---------- -------  
-biopython  1.70  
-chardet    4.0.0  
-Django     1.9.7  
-django-sendfile 0.3.11  
-numpy      1.16.6  
-pip        20.3.4  
-setuptools 44.1.1  
-unicodecsv 0.14.1  
-wheel      0.37.1  



# Primary Updates to back-end software  
## Packages:  
sqlite3 --version  
3.37.2 2022-01-06 13:25:41 872ba256cbf61d9290b571c0e6d82a20c224ca3ad82971edc46b29818d5dalt1  

update sqlite  
	downloaded newest version sqlite-amalgamation-3420000.zip  
	cd sqlite-amalgamation-3420000  
	gcc -o sqlite3 shell.c sqlite3.c -lpthread -ldl  
	./sqlite3 -version  
	which sqlite3  
	sudo mv ./sqlite3 /usr/bin/sqlite3  
	sqlite3 -version  
		3.42.0 2023-05-16 12:36:15 831d0fb2836b71c9bc51067c49fee4b8f18047814f2ff22d817d25195cf350b0  
update python  
	sudo apt upgrade python3  

update virtual enviroment  
	 python3.10 -m venv ~/newenv  
	 source ~/newenv/bin/activate  
update packages:  
	pip install unicodecsv  

Perl is up to date:  
	 perl --version  
  
This is perl 5, version 34,  
	--5.38 is most recent  

update django  
	pip install django  
	django-admin --version  
	4.2.3  
update unicodecsv   
	pip install unicodecsv BAD  
		0.14.1  
	pip install biopython  
		1.81  
	pip install chardet  
		chardet-5.1.0  
	pip install django-sendfile  
		0.3.11  
	pip install pip  
		 ALREADY UP TO DATE 22.0.2  
	pip install numpy  
		 ALREADY UP TO DATE 1.25.0  
	pip install setup tools  
		 ALREADY UP TO DATE 59.6.0  
	pip install wheel  
		0.40.0  
	pip install dos2unix  
		7.4.2-2  
	sudo apt install recode  
		recode (3.6-24build2)   

  
# Updates to code from transition:  
## \include\peptide\peptide\models.py  
	added class ProteinVariant(models.Model):  
    			# Other fields...  
     			Protein = models.ForeignKey(ProteinInfo, on_delete=models.CASCADE, related_name="orig_proteins")  
		class PeptideInfo(models.Model):   
    			#peptide = models.CharField(max_length=300)  
   			protein = models.ForeignKey(ProteinInfo, on_delete=models.CASCADE, related_name="proteins")  
## \include\peptide\peptide\admin.py  
	updated with a .models  
		from peptide.models import PeptideInfo, Submission, Counter, ProteinInfo, ProteinVariant, protein_pid  
		from peptide.toolbox import...  
	 
## \include\peptide\peptide\toolbox.py  
	from django.conf import settings  
	import csv  
	from .models import ....  
	out = open(output_path, 'w', encoding='utf-8')  
	writer = csv.writer(out, delimiter='\t')  
	unicdoe -> str  

	replace def handle_uploaded_file(f,path):  
    	with open(path, 'w') as destination:  
        for chunk in f.chunks():  
        destination.write(chunk.decode('utf-8'))   
        pep = pep.decode('utf-8').rstrip('\n')  
     

	from django.urls import include, re_path  
	from django.contrib import admin  
	from peptide import views  

  
	with open(input_tsv_path, 'r', encoding='utf-8') as pepfile:  
            data = csv.DictReader(pepfile, dialect='pep_dialect')  


## \newenv\lib\python3.10\site-packages\sendfile\__init__.py  
	replace force_unicode with from django.utils.encoding import force_str as force_text  
	replace urlquote with quote  
		if ascii_filename != attachment_filename:  
                from django.utils.http import quote  
                quoted_filename = quote(attachment_filename)  
 
## \include\peptide\peptide\urls.py  
	urlpatterns = [  
	    re_path(r'^$', views.peptide_search, name='index'),  
	    re_path(r'^homology_search/$', views.homology_search, name='homology_search'),   
	    re_path(r'^skyline/$', views.skyline, name='skyline'),  
	    re_path(r'^skyline_auto/$', views.skyline_auto, name='skyline_auto'),    
    	re_path(r'^remove_domains_tool/$', views.remove_domains_tool, name='remove_domains_tool'),  
   	 re_path(r'^pepex/$', views.pepex_tool, name='pepex'),  
   	 re_path(r'^add_proteins/$', views.add_proteins_tool, name='add_proteins'),  
   	 re_path(r'^protein_headers/$', views.protein_headers, name='protein_headers'),  
   	 re_path(r'^tsv_search_results/', views.tsv_search_results, name='tsv_search_results'),  
   	 re_path(r'^peptide_db/$', views.peptide_db, name='peptide_db'),  
   	 re_path(r'^peptide_db_csv/$', views.peptide_db_csv, name='peptide_db_csv'),  
    	re_path(r'^peptide_search/$', views.peptide_search, name='peptide_search'),  
    	re_path(r'^peptide_multi_search/$', views.peptide_multi_search, name='peptide_multi_search'),  
    	re_path(r'^contact/$', views.contact, name='contact'),  
    	re_path(r'^admin/', admin.site.urls),  
	]  
  
## \include\peptide\peptide\views.py  
	from .toolbox import  
	from .model import  
       except CalledProcessError as e:  
		replace 11 instances of   

## \include\peptide\peptide\settings.py  

	ALLOWED_HOSTS = ['128.193.11.196', '127.0.0.1', 'localhost']  


	MIDDLEWARE = [  
    'django.contrib.sessions.middleware.SessionMiddleware',  
    'django.middleware.common.CommonMiddleware',  
    'django.middleware.csrf.CsrfViewMiddleware',  
    'django.contrib.auth.middleware.AuthenticationMiddleware',  
    'django.contrib.messages.middleware.MessageMiddleware',  
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  
	]  

	TEMPLATES = [  
    {  
        # other settings  
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  
        # other settings  
    },  
	]  
  
	DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'  

##  /include/peptide/peptide/templates/peptide$ 
updated all HTML files with the folloing 
{% load staticfiles %} got replaced by {% load static %}  

- add_proteins.html  
- contact.html  
- pepex.html  
- peptide_multi_search.html  
- skyline.html  
- base.html  
- homology_search.html  
- peptide_db.html  
- peptide_search.html  
- skyline_auto.html  
- base.html~  
- index.html  
- peptide_db_csv.html  
- remove_domains_tool.html  


# SQL table information:  
/include/peptide/db.sqlite3  
## Tables  
sqlite> .tables   
- auth_group                      
- auth_group_permissions           
- auth_permission                 
- auth_user                       
- auth_user_groups               
- auth_user_user_permissions      
- django_admin_log                
- django_content_type             
- django_migrations    
- django_session   
- peptide_counter  
- peptide_function  
- peptide_peptideinfo  
- peptide_proteinvariant  
- peptide_reference  
- peptide_submission  

### auth_user  
sqlite> SELECT * FROM auth_user LIMIT 10;  
1|pbkdf2_sha256$12000$c2EfcHud3ME5$3T+ADB5kMAos8BNleYv1DlN9JLXkicpH8q7z+R/eFCA=|2014-11-24 22:46:53|0|||amschaal@ucdavis.edu|1|1|2014-11-24 22:46:53|adam  
2|pbkdf2_sha256$24000$ucEO0EwNCHhW$RHdVVDYxTzCy94P8bjcIoIo6Ro89vHegl4IfJKgvKmI=|2018-03-01 09:30:25.321274|1|||najoshi@ucdavis.edu|1|1|2017-03-27 22:54:51|joshi  
3|pbkdf2_sha256$24000$8JaUoEua9cFF$ogn4yB+MZn4zwwrykQnoui38/M/DlDRZQlRBJjJPWxA=|2022-02-25 21:54:37.819441|1|Soeren|Nielsen|sdrudn2@gmail.com|1|1|2017-04-20 10:04:29|nielsen  
4|pbkdf2_sha256$24000$baK95dAwK1bD$nl+Be0pjPUSHdjZXrHYQbrGjFjkocEPDqVoMBeqnXD4=|2020-02-19 20:28:45.716484|0|||Dave.Dallas@oregonstate.edu|1|1|2020-02-19 20:26:09|David  
 

### peptide_peptideinfo  
sqlite> SELECT * FROM peptide_peptideinfo LIMIT 10;  
2976|VA|28020|2|Dairy|96-97, 114-115, 168-169, 225-226, 275-276, 357-358, 457-458, 561-562, 687-688||2018-03-01 09:26:29.411842  
2977|FL|28020|2|Dairy|5-6, 10-11, 154-155, 707-708||2018-03-01 09:26:29.411842  
2978|AL|28020|2|Dairy|13-14, 401-402, 524-525, 591-592||2018-03-01 09:26:29.411842  
 
### auth_user_user_permissions  
sqlite> SELECT * FROM auth_user_user_permissions;  
1|4|1  
2|4|2  
3|4|3  
.....  
38|4|38  
 
sqlite> PRAGMA table_info(auth_user_user_permissions);  
0|id|INTEGER|1||1  
1|user_id|INTEGER|1||0  
2|permission_id|INTEGER|1||0  


### django_admin_log  
sqlite> SELECT * FROM django_admin_log LIMIT 3;  
1|2|joshi|2|Changed username.|4|2|2017-04-07 23:12:15.902193  
2|7426|Submission object|3||11|2|2017-04-15 05:28:44.488750  
3|1|adam|2|Changed is_superuser.|4|2|2017-04-20 00:32:26.633660  


### django_migrations   
sqlite> SELECT * FROM django_migrations LIMIT 3;  
1|contenttypes|0001_initial|2014-11-24 22:46:12.044994  
2|auth|0001_initial|2014-11-24 22:46:12.370643  
3|admin|0001_initial|2014-11-24 22:46:12.638026  


### django_session
sqlite> SELECT * FROM django_session LIMIT 3;  
cqp08z0z7ae5k83wxrdzipp0t55qej30|NDU4ZGRkZDFmNzM3NDI3NTFmZjgxOTljMTNkMWRhYzA3Njc4Zjk2ZDp7fQ==|2014-12-08 22:46:58.039742  

sqlite> PRAGMA table_info(django_session);  
0|session_key|varchar(40)|1||1  
1|session_data|TEXT|1||0  
2|expire_date|datetime|1||0  


### peptide_counter  
sqlite> SELECT * FROM peptide_counter LIMIT 3;  
1|128.120.143.72|2017-05-11 22:58:04.658556|peptide search  
2|138.194.36.16|2017-05-12 01:51:29.390784|peptide search  
3|138.194.36.16|2017-05-12 01:52:01.931930|peptide search  

sqlite> SELECT COUNT(*) FROM peptide_counter;  
68414 -> 2022  
232186 -> 2023  
sqlite> SELECT * FROM peptide_counter WHERE id = 68414;  
68414|152.57.240.17|2022-03-24 15:37:15.364333|peptide search  

sqlite> PRAGMA table_info(peptide_counter);  
0|id|INTEGER|1||1  
1|ip|varchar(40)|1||0  
2|access_time|datetime|1||0  
3|page|varchar(40)|1||0  

### peptide_function  
sqlite> SELECT * FROM peptide_function LIMIT 3;  
1|DPP-IV Inhibitory|2976  
2|DPP-IV Inhibitory|2977  
3|DPP-IV Inhibitory|2978  
sqlite> PRAGMA table_info(peptide_function);  
0|id|INTEGER|1||1  
1|function|varchar(400)|1||0  
2|pep_id|INTEGER|1||0  


### peptide_peptideinfo  
sqlite> PRAGMA table_info(peptide_peptideinfo);  
0|id|INTEGER|1||1  
1|peptide|varchar(300)|1||0  
2|protein_id|INTEGER|1||0  
3|length|INTEGER|1||0  
4|category|varchar(50)|1||0  
5|intervals|varchar(100)|1||0  
6|protein_variants|varchar(100)|1||0  
7|time_approved|datetime|1||0  


### peptide_proteininfo  
sqlite> PRAGMA table_info(peptide_proteininfo);  
0|id|INTEGER|1||1   
1|pid|varchar(30)|1||0  
2|desc|varchar(500)|1||0  
3|species|varchar(70)|1||0  
4|header|varchar(1000)|1||0  
5|seq|varchar(5000)|1||0  


### peptide_proteinvariant  
sqlite> PRAGMA table_info(peptide_proteininfo);  
0|id|INTEGER|1||1  
1|pid|varchar(30)|1||0  
2|desc|varchar(500)|1||0   
3|species|varchar(70)|1||0  
4|header|varchar(1000)|1||0  
5|seq|varchar(5000)|1||0  


### peptide_reference  
sqlite> PRAGMA table_info(peptide_reference);  
0|id|INTEGER|1||1  
1|authors|varchar(300)|1||0   
2|abstract|varchar(1000)|1||0  
3|func_id|INTEGER|1||0  
4|doi|varchar(100)|1||0  
5|title|varchar(300)|1||0  
6|secondary_func|varchar(400)|1||0  
7|ptm|varchar(200)|1||0  


### peptide_submission  
sqlite> SELECT * FROM peptide_submission;  


### peptide_submission  
sqlite> PRAGMA table_info(peptide_submission);  
0|id|INTEGER|1||1  
1|protein_id|varchar(30)|1||0   
2|peptide|varchar(300)|1||0  
3|category|varchar(50)|1||0  
4|function|varchar(400)|1||0  
5|secondary_function|varchar(400)|1||0  
6|title|varchar(300)|1||0  
7|authors|varchar(300)|1||0  
8|abstract|varchar(1000)|1||0  
9|doi|varchar(100)|1||0  
10|time_submitted|datetime|1||0  
11|length|INTEGER|1||0  
12|intervals|varchar(100)|1||0  
13|ptm|varchar(200)|1||0  
14|protein_variants|varchar(30)|1||0  


### peptide_reference
sqlite> PRAGMA table_info(peptide_reference);  
0|id|INTEGER|1||1  
1|authors|varchar(300)|1||0   
2|abstract|varchar(1000)|1||0  
3|func_id|INTEGER|1||0  
4|doi|varchar(100)|1||0  
5|title|varchar(300)|1||0   
6|secondary_func|varchar(400)|1||0   
7|ptm|varchar(200)|1||0  

  
# Tree of application:  
## Removed folders with excess non-important files
.
├── README.md
├── bin
│   ├── activate
│   ├── activate.csh
│   ├── activate.fish
│   ├── activate_this.py
│   ├── django-admin
│   ├── django-admin.py
│   ├── easy_install
│   ├── easy_install-2.7
│   ├── pip
│   ├── pip-2.7
│   └── python
├── include
│   ├── peptide
│   │   ├── db.sqlite3
│   │   ├── envname
│   │   │   ├── bin
│   │   │   │   ├── __pycache__
│   │   │   │   │   └── django-admin.cpython-310.pyc
│   │   │   │   ├── activate
│   │   │   │   ├── activate.csh
│   │   │   │   ├── activate.fish
│   │   │   │   ├── activate.nu
│   │   │   │   ├── activate.ps1
│   │   │   │   ├── activate_this.py
│   │   │   │   ├── django-admin
│   │   │   │   ├── django-admin.py
│   │   │   │   ├── pip
│   │   │   │   ├── pip-3.10
│   │   │   │   ├── pip3
│   │   │   │   ├── pip3.10
│   │   │   │   ├── wheel
│   │   │   │   ├── wheel-3.10
│   │   │   │   ├── wheel3
│   │   │   │   └── wheel3.10
│   │   │   ├── lib
│   │   │   │   └── python3.10
│   │   │   │       └── site-packages
│   │   │   ├── peptide - Shortcut.lnk
│   │   │   └── pyvenv.cfg
│   │   ├── manage.py
│   │   ├── peptide
│   │   │   ├── __init__.py
│   │   │   ├── __init__.pyc
│   │   │   ├── __pycache__
│   │   │   │   ├── __init__.cpython-310.pyc
│   │   │   │   ├── __init__.cpython-39.pyc
│   │   │   │   ├── admin.cpython-310.pyc
│   │   │   │   ├── models.cpython-310.pyc
│   │   │   │   ├── settings.cpython-310.pyc
│   │   │   │   ├── settings.cpython-39.pyc
│   │   │   │   ├── toolbox.cpython-310.pyc
│   │   │   │   ├── urls.cpython-310.pyc
│   │   │   │   ├── views.cpython-310.pyc
│   │   │   │   └── wsgi.cpython-310.pyc
│   │   │   ├── admin.py
│   │   │   ├── admin.pyc
│   │   │   ├── forms.py
│   │   │   ├── migrations
│   │   │   │   ├── 0001_initial.py
│   │   │   │   ├── 0001_initial.pyc
│   │   │   │   ├── __init__.py
│   │   │   │   ├── __init__.pyc
│   │   │   │   └── __pycache__
│   │   │   ├── models.py
│   │   │   ├── models.pyc
│   │   │   ├── settings.py
│   │   │   ├── settings.pyc
│   │   │   ├── static
│   │   │   │   └── peptide
│   │   │   │       ├── Help-48-black.png
│   │   │   │       ├── MBPDB_Help.html
│   │   │   │       ├── MBPDB_Help.pdf
│   │   │   │       ├── example
│   │   │   │       ├── favicon.ico
│   │   │   │       ├── question-mark-in-a-blue-circle-8959-small.png
│   │   │   │       ├── question-mark-in-a-blue-circle-8959-tiny.png
│   │   │   │       ├── scripts
│   │   │   │       ├── theme
│   │   │   │       └── vendor
│   │   │   ├── templates
│   │   │   │   └── peptide
│   │   │   │       ├── add_proteins.html
│   │   │   │       ├── base.html
│   │   │   │       ├── contact.html
│   │   │   │       ├── homology_search.html
│   │   │   │       ├── index.html
│   │   │   │       ├── pepex.html
│   │   │   │       ├── peptide_db.html
│   │   │   │       ├── peptide_db2.html
│   │   │   │       ├── peptide_db_csv.html
│   │   │   │       ├── peptide_multi_search.html
│   │   │   │       ├── peptide_search.html
│   │   │   │       ├── remove_domains_tool.html
│   │   │   │       ├── skyline.html
│   │   │   │       └── skyline_auto.html
│   │   │   ├── toolbox.py
│   │   │   ├── toolbox.pyc
│   │   │   ├── urls.py
│   │   │   ├── urls.pyc.  
├── README.md  
├── bin  
│   ├── activate  
│   ├── activate.csh  
│   ├── activate.fish  
│   ├── activate_this.py  
│   ├── django-admin  
│   ├── django-admin.py  
│   ├── easy_install  
│   ├── easy_install-2.7  
│   ├── pip  
│   ├── pip-2.7  
│   └── python  
├── include  
│   ├── peptide  
│   │   ├── db.sqlite3  
│   │   ├── envname  
│   │   │   ├── bin  
│   │   │   │   ├── __pycache__  
│   │   │   │   │   └── django-admin.cpython-310.pyc  
│   │   │   │   ├── activate  
│   │   │   │   ├── activate.csh  
│   │   │   │   ├── activate.fish  
│   │   │   │   ├── activate.nu  
│   │   │   │   ├── activate.ps1  
│   │   │   │   ├── activate_this.py  
│   │   │   │   ├── django-admin  
│   │   │   │   ├── django-admin.py  
│   │   │   │   ├── pip  
│   │   │   │   ├── pip-3.10  
│   │   │   │   ├── pip3  
│   │   │   │   ├── pip3.10  
│   │   │   │   ├── wheel  
│   │   │   │   ├── wheel-3.10  
│   │   │   │   ├── wheel3  
│   │   │   │   └── wheel3.10  
│   │   │   ├── lib  
│   │   │   │   └── python3.10  
│   │   │   │       └── site-packages  
│   │   │   ├── peptide - Shortcut.lnk  
│   │   │   └── pyvenv.cfg  
│   │   ├── manage.py  
│   │   ├── peptide  
│   │   │   ├── __init__.py  
│   │   │   ├── __init__.pyc  
│   │   │   ├── __pycache__  
│   │   │   │   ├── __init__.cpython-310.pyc  
│   │   │   │   ├── __init__.cpython-39.pyc  
│   │   │   │   ├── admin.cpython-310.pyc  
│   │   │   │   ├── models.cpython-310.pyc  
│   │   │   │   ├── settings.cpython-310.pyc  
│   │   │   │   ├── settings.cpython-39.pyc  
│   │   │   │   ├── toolbox.cpython-310.pyc  
│   │   │   │   ├── urls.cpython-310.pyc  
│   │   │   │   ├── views.cpython-310.pyc  
│   │   │   │   └── wsgi.cpython-310.pyc  
│   │   │   ├── admin.py  
│   │   │   ├── admin.pyc  
│   │   │   ├── forms.py  
│   │   │   ├── migrations  
│   │   │   │   ├── 0001_initial.py  
│   │   │   │   ├── 0001_initial.pyc  
│   │   │   │   ├── 0002_auto_20160630_1703.py  
│   │   │   │   ├── 0002_auto_20160630_1703.pyc  
│   │   │   │   ├── 0003_auto_20160701_1729.py  
│   │   │   │   ├── 0003_auto_20160701_1729.pyc  
│   │   │   │   ├── 0004_reference_doi.py  
│   │   │   │   ├── 0004_reference_doi.pyc  
│   │   │   │   ├── 0005_auto_20160711_1649.py  
│   │   │   │   ├── 0005_auto_20160711_1649.pyc  
│   │   │   │   ├── 0006_auto_20160712_1522.py  
│   │   │   │   ├── 0006_auto_20160712_1522.pyc  
│   │   │   │   ├── 0007_remove_reference_citation.py  
│   │   │   │   ├── 0007_remove_reference_citation.pyc  
│   │   │   │   ├── 0008_proteininfo.py  
│   │   │   │   ├── 0008_proteininfo.pyc  
│   │   │   │   ├── 0009_proteininfo_header.py  
│   │   │   │   ├── 0009_proteininfo_header.pyc  
│   │   │   │   ├── 0010_auto_20161205_2012.py  
│   │   │   │   ├── 0010_auto_20161205_2012.pyc  
│   │   │   │   ├── 0011_auto_20161205_2139.py  
│   │   │   │   ├── 0011_auto_20161205_2139.pyc  
│   │   │   │   ├── 0012_auto_20161205_2149.py  
│   │   │   │   ├── 0012_auto_20161205_2149.pyc  
│   │   │   │   ├── 0013_function_secondary_func.py  
│   │   │   │   ├── 0013_function_secondary_func.pyc  
│   │   │   │   ├── 0014_auto_20161206_1748.py  
│   │   │   │   ├── 0014_auto_20161206_1748.pyc  
│   │   │   │   ├── 0015_auto_20170127_1417.py  
│   │   │   │   ├── 0015_auto_20170127_1417.pyc  
│   │   │   │   ├── 0016_auto_20170127_1445.py  
│   │   │   │   ├── 0016_auto_20170127_1445.pyc  
│   │   │   │   ├── 0017_remove_peptideinfo_aa_after_peptide.py  
│   │   │   │   ├── 0017_remove_peptideinfo_aa_after_peptide.pyc  
│   │   │   │   ├── 0018_remove_peptideinfo_species.py  
│   │   │   │   ├── 0018_remove_peptideinfo_species.pyc  
│   │   │   │   ├── 0019_peptideinfo_category.py  
│   │   │   │   ├── 0019_peptideinfo_category.pyc  
│   │   │   │   ├── 0020_auto_20170315_1516.py  
│   │   │   │   ├── 0020_auto_20170315_1516.pyc  
│   │   │   │   ├── 0021_auto_20170316_0049.py  
│   │   │   │   ├── 0021_auto_20170316_0049.pyc  
│   │   │   │   ├── 0022_auto_20170316_1549.py  
│   │   │   │   ├── 0022_auto_20170316_1549.pyc  
│   │   │   │   ├── 0023_peptideinfo_time_submitted.py  
│   │   │   │   ├── 0023_peptideinfo_time_submitted.pyc  
│   │   │   │   ├── 0024_auto_20170407_1654.py  
│   │   │   │   ├── 0024_auto_20170407_1654.pyc  
│   │   │   │   ├── 0025_auto_20170413_1725.py  
│   │   │   │   ├── 0025_auto_20170413_1725.pyc  
│   │   │   │   ├── 0026_auto_20170502_1519.py  
│   │   │   │   ├── 0026_auto_20170502_1519.pyc  
│   │   │   │   ├── 0027_auto_20170502_1620.py  
│   │   │   │   ├── 0027_auto_20170502_1620.pyc  
│   │   │   │   ├── 0028_counter.py  
│   │   │   │   ├── 0028_counter.pyc  
│   │   │   │   ├── 0029_counter_page.py  
│   │   │   │   ├── 0029_counter_page.pyc  
│   │   │   │   ├── 0030_auto_20170526_0225.py  
│   │   │   │   ├── 0030_auto_20170526_0225.pyc  
│   │   │   │   ├── 0031_auto_20170901_1642.py  
│   │   │   │   ├── 0031_auto_20170901_1642.pyc  
│   │   │   │   ├── 0032_auto_20180301_0126.py  
│   │   │   │   ├── 0032_auto_20180301_0126.pyc  
│   │   │   │   ├── 0033_auto_20230629_0821.py  
│   │   │   │   ├── 0033_auto_20230629_0821.pyc  
│   │   │   │   ├── 0034_auto_20230629_0913.py  
│   │   │   │   ├── 0034_auto_20230629_0913.pyc  
│   │   │   │   ├── 0035_auto_20230629_0950.py  
│   │   │   │   ├── 0035_auto_20230629_0950.pyc  
│   │   │   │   ├── 0036_auto_20230629_1010.py  
│   │   │   │   ├── 0036_auto_20230629_1010.pyc  
│   │   │   │   ├── 0037_alter_counter_id_alter_function_id_and_more.py  
│   │   │   │   ├── 0038_remove_reference_ic50_remove_submission_ic50.py  
│   │   │   │   ├── __init__.py  
│   │   │   │   ├── __init__.pyc  
│   │   │   │   └── __pycache__  
│   │   │   │       ├── 0001_initial.cpython-310.pyc  
│   │   │   │       ├── 0002_auto_20160630_1703.cpython-310.pyc  
│   │   │   │       ├── 0003_auto_20160701_1729.cpython-310.pyc  
│   │   │   │       ├── 0004_reference_doi.cpython-310.pyc  
│   │   │   │       ├── 0005_auto_20160711_1649.cpython-310.pyc  
│   │   │   │       ├── 0006_auto_20160712_1522.cpython-310.pyc  
│   │   │   │       ├── 0007_remove_reference_citation.cpython-310.pyc  
│   │   │   │       ├── 0008_proteininfo.cpython-310.pyc  
│   │   │   │       ├── 0009_proteininfo_header.cpython-310.pyc  
│   │   │   │       ├── 0010_auto_20161205_2012.cpython-310.pyc  
│   │   │   │       ├── 0011_auto_20161205_2139.cpython-310.pyc  
│   │   │   │       ├── 0012_auto_20161205_2149.cpython-310.pyc  
│   │   │   │       ├── 0013_function_secondary_func.cpython-310.pyc  
│   │   │   │       ├── 0014_auto_20161206_1748.cpython-310.pyc  
│   │   │   │       ├── 0015_auto_20170127_1417.cpython-310.pyc  
│   │   │   │       ├── 0016_auto_20170127_1445.cpython-310.pyc  
│   │   │   │       ├── 0017_remove_peptideinfo_aa_after_peptide.cpython-310.pyc  
│   │   │   │       ├── 0018_remove_peptideinfo_species.cpython-310.pyc  
│   │   │   │       ├── 0019_peptideinfo_category.cpython-310.pyc  
│   │   │   │       ├── 0020_auto_20170315_1516.cpython-310.pyc  
│   │   │   │       ├── 0021_auto_20170316_0049.cpython-310.pyc  
│   │   │   │       ├── 0022_auto_20170316_1549.cpython-310.pyc  
│   │   │   │       ├── 0023_peptideinfo_time_submitted.cpython-310.pyc  
│   │   │   │       ├── 0024_auto_20170407_1654.cpython-310.pyc  
│   │   │   │       ├── 0025_auto_20170413_1725.cpython-310.pyc  
│   │   │   │       ├── 0026_auto_20170502_1519.cpython-310.pyc  
│   │   │   │       ├── 0027_auto_20170502_1620.cpython-310.pyc  
│   │   │   │       ├── 0028_counter.cpython-310.pyc  
│   │   │   │       ├── 0029_counter_page.cpython-310.pyc  
│   │   │   │       ├── 0030_auto_20170526_0225.cpython-310.pyc  
│   │   │   │       ├── 0031_auto_20170901_1642.cpython-310.pyc  
│   │   │   │       ├── 0032_auto_20180301_0126.cpython-310.pyc  
│   │   │   │       ├── 0033_auto_20230629_0821.cpython-310.pyc  
│   │   │   │       ├── 0034_auto_20230629_0913.cpython-310.pyc  
│   │   │   │       ├── 0035_auto_20230629_0950.cpython-310.pyc  
│   │   │   │       ├── 0036_auto_20230629_1010.cpython-310.pyc  
│   │   │   │       ├── 0037_alter_counter_id_alter_function_id_and_more.cpython-310.pyc  
│   │   │   │       ├── 0038_remove_reference_ic50_remove_submission_ic50.cpython-310.pyc  
│   │   │   │       └── __init__.cpython-310.pyc  
│   │   │   ├── models.py  
│   │   │   ├── models.pyc  
│   │   │   ├── settings.py  
│   │   │   ├── settings.pyc  
│   │   │   ├── static  
│   │   │   │   └── peptide  
│   │   │   │       ├── Help-48-black.png  
│   │   │   │       ├── MBPDB_Help.html  
│   │   │   │       ├── MBPDB_Help.pdf  
│   │   │   │       ├── example  
│   │   │   │       ├── favicon.ico  
│   │   │   │       ├── question-mark-in-a-blue-circle-8959-small.png  
│   │   │   │       ├── question-mark-in-a-blue-circle-8959-tiny.png  
│   │   │   │       ├── scripts  
│   │   │   │       ├── theme  
│   │   │   │       └── vendor  
│   │   │   ├── templates  
│   │   │   │   └── peptide  
│   │   │   │       ├── add_proteins.html  
│   │   │   │       ├── base.html  
│   │   │   │       ├── contact.html  
│   │   │   │       ├── homology_search.html  
│   │   │   │       ├── index.html  
│   │   │   │       ├── pepex.html  
│   │   │   │       ├── peptide_db.html  
│   │   │   │       ├── peptide_db2.html  
│   │   │   │       ├── peptide_db_csv.html  
│   │   │   │       ├── peptide_multi_search.html  
│   │   │   │       ├── peptide_search.html  
│   │   │   │       ├── remove_domains_tool.html  
│   │   │   │       ├── skyline.html  
│   │   │   │       └── skyline_auto.html  
│   │   │   ├── toolbox.py  
│   │   │   ├── toolbox.pyc  
│   │   │   ├── urls.py  
│   │   │   ├── urls.pyc  
│   │   │   ├── views.py  
│   │   │   ├── views.pyc  
│   │   │   ├── wsgi.py  
│   │   │   └── wsgi.pyc  
│   │   ├── peptide.wsgi  
│   │   ├── scripts  
│   │   │   ├── combine.pl  
│   │   │   ├── create_fasta_input.pl  
│   │   │   ├── create_fasta_lib.pl  
│   │   │   ├── create_pepex_input.pl  
│   │   │   ├── fasta_files  
│   │   │   │   └── protein_database.fasta  
│   │   │   ├── fasta_files.old  
│   │   │   │   ├── CowMilkProteinLibrary.fasta  
│   │   │   │   ├── CowMilkProteinLibrary_SODN.fasta  
│   │   │   │   ├── HumanMilk_18022012.fasta  
│   │   │   │   ├── PigMilkProteinLibrary.fasta  
│   │   │   │   └── Sheep_proteome.fasta  
│   │   │   ├── fix_weird_chars.pl  
│   │   │   ├── pepex.pl  
│   │   │   ├── pySamplewiseSequenceAligner_v1.2  
│   │   │   │   ├── pySamplewiseSequenceAligner.py  
│   │   │   │   ├── readSamplewiseSequenceAlignerConfigXml.py  
│   │   │   │   └── testScript.py  
│   │   │   ├── remove_domains_xml.pl  
│   │   │   ├── skyline_combine.pl  
│   │   │   ├── skyline_combine_peptides_with_same_mods.pl  
│   │   │   ├── skyline_combine_rearranged.pl  
│   │   │   ├── skyline_edit_columns.pl  
│   │   │   ├── skyline_filter.pl  
│   │   │   ├── try  
│   │   │   │   ├── BLOSUM62.txt  
│   │   │   │   ├── IDENTITY  
│   │   │   │   ├── README  
│   │   │   │   ├── pd.fasta  
│   │   │   │   ├── pd.fasta.phr  
│   │   │   │   ├── pd.fasta.pin  
│   │   │   │   ├── pd.fasta.psq  
│   │   │   │   ├── pd2.fasta  
│   │   │   │   ├── pd2.fasta.phr  
│   │   │   │   ├── pd2.fasta.pin  
│   │   │   │   ├── pd2.fasta.psq  
│   │   │   │   ├── pd3.fasta  
│   │   │   │   ├── pd3.fasta.phr  
│   │   │   │   ├── pd3.fasta.pin  
│   │   │   │   ├── pd3.fasta.psq  
│   │   │   │   ├── pepdb.fasta  
│   │   │   │   ├── pepdb.fasta.phr  
│   │   │   │   ├── pepdb.fasta.pin  
│   │   │   │   ├── pepdb.fasta.psq  
│   │   │   │   ├── protein_database.fasta  
│   │   │   │   ├── protein_database.fasta.phr  
│   │   │   │   ├── protein_database.fasta.pin  
│   │   │   │   ├── protein_database.fasta.psq  
│   │   │   │   ├── sql.out  
│   │   │   │   ├── try.fasta  
│   │   │   │   ├── try10.fasta  
│   │   │   │   ├── try11.fasta  
│   │   │   │   ├── try12.fasta  
│   │   │   │   ├── try13.fasta  
│   │   │   │   ├── try2.fasta  
│   │   │   │   ├── try3.fasta  
│   │   │   │   ├── try4.fasta  
│   │   │   │   ├── try5.fasta  
│   │   │   │   ├── try6.fasta  
│   │   │   │   ├── try7.fasta  
│   │   │   │   ├── try8.fasta  
│   │   │   │   └── try9.fasta  
│   │   │   └── xlsx_to_tsv.pl  
│   │   ├── static_files  
│   │   │   ├── admin  
│   │   │   │   ├── css  
│   │   │   │   │   ├── base.css  
│   │   │   │   │   ├── changelists.css  
│   │   │   │   │   ├── dashboard.css  
│   │   │   │   │   ├── fonts.css  
│   │   │   │   │   ├── forms.css  
│   │   │   │   │   ├── ie.css  
│   │   │   │   │   ├── login.css  
│   │   │   │   │   ├── rtl.css  
│   │   │   │   │   └── widgets.css  
│   │   │   │   ├── fonts  
│   │   │   │   │   ├── LICENSE.txt  
│   │   │   │   │   ├── README.txt  
│   │   │   │   │   ├── Roboto-Bold-webfont.woff  
│   │   │   │   │   ├── Roboto-Light-webfont.woff  
│   │   │   │   │   └── Roboto-Regular-webfont.woff  
│   │   │   │   ├── img  
│   │   │   │   │   ├── LICENSE  
│   │   │   │   │   ├── README.txt  
│   │   │   │   │   ├── calendar-icons.svg  
│   │   │   │   │   ├── changelist-bg.gif  
│   │   │   │   │   ├── changelist-bg_rtl.gif  
│   │   │   │   │   ├── default-bg-reverse.gif  
│   │   │   │   │   ├── default-bg.gif  
│   │   │   │   │   ├── deleted-overlay.gif  
│   │   │   │   │   ├── gis  
│   │   │   │   │   ├── icon-addlink.svg  
│   │   │   │   │   ├── icon-alert.svg  
│   │   │   │   │   ├── icon-calendar.svg  
│   │   │   │   │   ├── icon-changelink.svg  
│   │   │   │   │   ├── icon-clock.svg  
│   │   │   │   │   ├── icon-deletelink.svg  
│   │   │   │   │   ├── icon-no.gif  
│   │   │   │   │   ├── icon-no.svg  
│   │   │   │   │   ├── icon-unknown-alt.svg  
│   │   │   │   │   ├── icon-unknown.gif  
│   │   │   │   │   ├── icon-unknown.svg  
│   │   │   │   │   ├── icon-yes.gif  
│   │   │   │   │   ├── icon-yes.svg  
│   │   │   │   │   ├── icon_addlink.gif  
│   │   │   │   │   ├── icon_alert.gif  
│   │   │   │   │   ├── icon_calendar.gif  
│   │   │   │   │   ├── icon_changelink.gif  
│   │   │   │   │   ├── icon_clock.gif  
│   │   │   │   │   ├── icon_deletelink.gif  
│   │   │   │   │   ├── icon_error.gif  
│   │   │   │   │   ├── icon_searchbox.png  
│   │   │   │   │   ├── icon_success.gif  
│   │   │   │   │   ├── inline-delete-8bit.png  
│   │   │   │   │   ├── inline-delete.png  
│   │   │   │   │   ├── inline-delete.svg  
│   │   │   │   │   ├── inline-restore-8bit.png  
│   │   │   │   │   ├── inline-restore.png  
│   │   │   │   │   ├── inline-splitter-bg.gif  
│   │   │   │   │   ├── nav-bg-grabber.gif  
│   │   │   │   │   ├── nav-bg-reverse.gif  
│   │   │   │   │   ├── nav-bg-selected.gif  
│   │   │   │   │   ├── nav-bg.gif  
│   │   │   │   │   ├── search.svg  
│   │   │   │   │   ├── selector-icons.gif  
│   │   │   │   │   ├── selector-icons.svg  
│   │   │   │   │   ├── selector-search.gif  
│   │   │   │   │   ├── sorting-icons.gif  
│   │   │   │   │   ├── sorting-icons.svg  
│   │   │   │   │   ├── tooltag-add.png  
│   │   │   │   │   ├── tooltag-add.svg  
│   │   │   │   │   ├── tooltag-arrowright.png  
│   │   │   │   │   └── tooltag-arrowright.svg  
│   │   │   │   └── js  
│   │   │   │       ├── LICENSE-JQUERY.txt  
│   │   │   │       ├── SelectBox.js  
│   │   │   │       ├── SelectFilter2.js  
│   │   │   │       ├── actions.js  
│   │   │   │       ├── actions.min.js  
│   │   │   │       ├── admin  
│   │   │   │       ├── calendar.js  
│   │   │   │       ├── cancel.js  
│   │   │   │       ├── change_form.js  
│   │   │   │       ├── collapse.js  
│   │   │   │       ├── collapse.min.js  
│   │   │   │       ├── core.js  
│   │   │   │       ├── inlines.js  
│   │   │   │       ├── inlines.min.js  
│   │   │   │       ├── jquery.init.js  
│   │   │   │       ├── jquery.js  
│   │   │   │       ├── jquery.min.js  
│   │   │   │       ├── popup_response.js  
│   │   │   │       ├── prepopulate.js  
│   │   │   │       ├── prepopulate.min.js  
│   │   │   │       ├── prepopulate_init.js  
│   │   │   │       ├── timeparse.js  
│   │   │   │       ├── urlify.js  
│   │   │   │       └── vendor  
│   │   │   └── peptide  
│   │   │       ├── Help-48-black.png  
│   │   │       ├── MBPDB_Help.html  
│   │   │       ├── MBPDB_Help.pdf  
│   │   │       ├── example  
│   │   │       │   ├── ExampleFunctionalPeptideLibrary.xlsx  
│   │   │       │   ├── ExamplePeptideInput.xlsx  
│   │   │       │   ├── ExampleSkylineInput.tsv  
│   │   │       │   ├── multiple_peptide_example.txt  
│   │   │       │   ├── peptide_db_input_file_example.tsv  
│   │   │       │   └── peptide_multi_search_input_file_example.tsv  
│   │   │       ├── favicon.ico  
│   │   │       ├── question-mark-in-a-blue-circle-8959-small.png  
│   │   │       ├── question-mark-in-a-blue-circle-8959-tiny.png  
│   │   │       ├── scripts  
│   │   │       │   └── page  
│   │   │       ├── theme  
│   │   │       │   ├── LICENSE  
│   │   │       │   ├── README.md  
│   │   │       │   ├── css  
│   │   │       │   ├── fonts  
│   │   │       │   ├── index.html  
│   │   │       │   └── js  
│   │   │       └── vendor  
│   │   │           ├── angular-file-upload  
│   │   │           └── angular.min.js  
│   │   ├── test.py  
│   │   └── uploads  
│   │       └── temp  
│   └── tree.txt  
├── lib  
│   └── python2.7  
│       ├── UserDict.pyc  
│       ├── _abcoll.pyc  
│       ├── _weakrefset.pyc  
│       ├── abc.pyc  
│       ├── codecs.pyc  
│       ├── copy_reg.pyc  
│       ├── distutils  
│       │   ├── __init__.py  
│       │   ├── __init__.pyc  
│       │   └── distutils.cfg  
│       ├── fnmatch.pyc  
│       ├── genericpath.pyc  
│       ├── linecache.pyc  
│       ├── no-global-site-packages.txt  
│       ├── orig-prefix.txt  
│       ├── os.pyc  
│       ├── posixpath.pyc  
│       ├── re.pyc  
│       ├── site-packages  
│       │   ├── Django-1.9.7-py2.7.egg-info  
│       │   │   ├── PKG-INFO  
│       │   │   ├── SOURCES.txt  
│       │   │   ├── dependency_links.txt  
│       │   │   ├── entry_points.txt  
│       │   │   ├── installed-files.txt  
│       │   │   ├── not-zip-safe  
│       │   │   ├── requires.txt  
│       │   │   └── top_level.txt  
│       │   ├── _markerlib  
│       │   │   ├── __init__.py  
│       │   │   ├── __init__.pyc  
│       │   │   ├── markers.py  
│       │   │   └── markers.pyc  
│       │   ├── django  
│       │   │   ├── __init__.py  
│       │   │   ├── __init__.pyc  
│       │   │   ├── __main__.py  
│       │   │   ├── __main__.pyc  
│       │   │   ├── apps  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── config.py  
│       │   │   │   ├── config.pyc  
│       │   │   │   ├── registry.py  
│       │   │   │   └── registry.pyc  
│       │   │   ├── bin  
│       │   │   │   ├── django-admin.py  
│       │   │   │   └── django-admin.pyc  
│       │   │   ├── conf  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── app_template  
│       │   │   │   ├── global_settings.py  
│       │   │   │   ├── global_settings.pyc  
│       │   │   │   ├── project_template  
│       │   │   │   └── urls  
│       │   │   ├── contrib  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── admin  
│       │   │   │   ├── admindocs  
│       │   │   │   ├── auth  
│       │   │   │   ├── contenttypes  
│       │   │   │   ├── flatpages  
│       │   │   │   ├── gis  
│       │   │   │   ├── humanize  
│       │   │   │   ├── messages  
│       │   │   │   ├── postgres  
│       │   │   │   ├── redirects  
│       │   │   │   ├── sessions  
│       │   │   │   ├── sitemaps  
│       │   │   │   ├── sites  
│       │   │   │   ├── staticfiles  
│       │   │   │   ├── syndication  
│       │   │   │   └── webdesign  
│       │   │   ├── core  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── cache  
│       │   │   │   ├── checks  
│       │   │   │   ├── context_processors.py  
│       │   │   │   ├── context_processors.pyc  
│       │   │   │   ├── exceptions.py  
│       │   │   │   ├── exceptions.pyc  
│       │   │   │   ├── files  
│       │   │   │   ├── handlers  
│       │   │   │   ├── mail  
│       │   │   │   ├── management  
│       │   │   │   ├── paginator.py  
│       │   │   │   ├── paginator.pyc  
│       │   │   │   ├── serializers  
│       │   │   │   ├── servers  
│       │   │   │   ├── signals.py  
│       │   │   │   ├── signals.pyc  
│       │   │   │   ├── signing.py  
│       │   │   │   ├── signing.pyc  
│       │   │   │   ├── urlresolvers.py  
│       │   │   │   ├── urlresolvers.pyc  
│       │   │   │   ├── validators.py  
│       │   │   │   ├── validators.pyc  
│       │   │   │   ├── wsgi.py  
│       │   │   │   └── wsgi.pyc  
│       │   │   ├── db  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── backends  
│       │   │   │   ├── migrations  
│       │   │   │   ├── models  
│       │   │   │   ├── transaction.py  
│       │   │   │   ├── transaction.pyc  
│       │   │   │   ├── utils.py  
│       │   │   │   └── utils.pyc  
│       │   │   ├── dispatch  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── dispatcher.py  
│       │   │   │   ├── dispatcher.pyc  
│       │   │   │   ├── license.python.txt  
│       │   │   │   ├── license.txt  
│       │   │   │   ├── weakref_backports.py  
│       │   │   │   └── weakref_backports.pyc  
│       │   │   ├── forms  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── boundfield.py  
│       │   │   │   ├── boundfield.pyc  
│       │   │   │   ├── extras  
│       │   │   │   ├── fields.py  
│       │   │   │   ├── fields.pyc  
│       │   │   │   ├── forms.py  
│       │   │   │   ├── forms.pyc  
│       │   │   │   ├── formsets.py  
│       │   │   │   ├── formsets.pyc  
│       │   │   │   ├── models.py  
│       │   │   │   ├── models.pyc  
│       │   │   │   ├── utils.py  
│       │   │   │   ├── utils.pyc  
│       │   │   │   ├── widgets.py  
│       │   │   │   └── widgets.pyc  
│       │   │   ├── http  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── cookie.py  
│       │   │   │   ├── cookie.pyc  
│       │   │   │   ├── multipartparser.py  
│       │   │   │   ├── multipartparser.pyc  
│       │   │   │   ├── request.py  
│       │   │   │   ├── request.pyc  
│       │   │   │   ├── response.py  
│       │   │   │   ├── response.pyc  
│       │   │   │   ├── utils.py  
│       │   │   │   └── utils.pyc  
│       │   │   ├── middleware  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── cache.py  
│       │   │   │   ├── cache.pyc  
│       │   │   │   ├── clickjacking.py  
│       │   │   │   ├── clickjacking.pyc  
│       │   │   │   ├── common.py  
│       │   │   │   ├── common.pyc  
│       │   │   │   ├── csrf.py  
│       │   │   │   ├── csrf.pyc  
│       │   │   │   ├── gzip.py  
│       │   │   │   ├── gzip.pyc  
│       │   │   │   ├── http.py  
│       │   │   │   ├── http.pyc  
│       │   │   │   ├── security.py  
│       │   │   │   └── security.pyc  
│       │   │   ├── shortcuts.py  
│       │   │   ├── shortcuts.pyc  
│       │   │   ├── template  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── backends  
│       │   │   │   ├── base.py  
│       │   │   │   ├── base.pyc  
│       │   │   │   ├── context.py  
│       │   │   │   ├── context.pyc  
│       │   │   │   ├── context_processors.py  
│       │   │   │   ├── context_processors.pyc  
│       │   │   │   ├── defaultfilters.py  
│       │   │   │   ├── defaultfilters.pyc  
│       │   │   │   ├── defaulttags.py  
│       │   │   │   ├── defaulttags.pyc  
│       │   │   │   ├── engine.py  
│       │   │   │   ├── engine.pyc  
│       │   │   │   ├── exceptions.py  
│       │   │   │   ├── exceptions.pyc  
│       │   │   │   ├── library.py  
│       │   │   │   ├── library.pyc  
│       │   │   │   ├── loader.py  
│       │   │   │   ├── loader.pyc  
│       │   │   │   ├── loader_tags.py  
│       │   │   │   ├── loader_tags.pyc  
│       │   │   │   ├── loaders  
│       │   │   │   ├── response.py  
│       │   │   │   ├── response.pyc  
│       │   │   │   ├── smartif.py  
│       │   │   │   ├── smartif.pyc  
│       │   │   │   ├── utils.py  
│       │   │   │   └── utils.pyc  
│       │   │   ├── templatetags  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── cache.py  
│       │   │   │   ├── cache.pyc  
│       │   │   │   ├── future.py  
│       │   │   │   ├── future.pyc  
│       │   │   │   ├── i18n.py  
│       │   │   │   ├── i18n.pyc  
│       │   │   │   ├── l10n.py  
│       │   │   │   ├── l10n.pyc  
│       │   │   │   ├── static.py  
│       │   │   │   ├── static.pyc  
│       │   │   │   ├── tz.py  
│       │   │   │   └── tz.pyc  
│       │   │   ├── test  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── client.py  
│       │   │   │   ├── client.pyc  
│       │   │   │   ├── html.py  
│       │   │   │   ├── html.pyc  
│       │   │   │   ├── runner.py  
│       │   │   │   ├── runner.pyc  
│       │   │   │   ├── signals.py  
│       │   │   │   ├── signals.pyc  
│       │   │   │   ├── testcases.py  
│       │   │   │   ├── testcases.pyc  
│       │   │   │   ├── utils.py  
│       │   │   │   └── utils.pyc  
│       │   │   ├── utils  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── _os.py  
│       │   │   │   ├── _os.pyc  
│       │   │   │   ├── archive.py  
│       │   │   │   ├── archive.pyc  
│       │   │   │   ├── autoreload.py  
│       │   │   │   ├── autoreload.pyc  
│       │   │   │   ├── baseconv.py  
│       │   │   │   ├── baseconv.pyc  
│       │   │   │   ├── cache.py  
│       │   │   │   ├── cache.pyc  
│       │   │   │   ├── checksums.py  
│       │   │   │   ├── checksums.pyc  
│       │   │   │   ├── crypto.py  
│       │   │   │   ├── crypto.pyc  
│       │   │   │   ├── datastructures.py  
│       │   │   │   ├── datastructures.pyc  
│       │   │   │   ├── dateformat.py  
│       │   │   │   ├── dateformat.pyc  
│       │   │   │   ├── dateparse.py  
│       │   │   │   ├── dateparse.pyc  
│       │   │   │   ├── dates.py  
│       │   │   │   ├── dates.pyc  
│       │   │   │   ├── datetime_safe.py  
│       │   │   │   ├── datetime_safe.pyc  
│       │   │   │   ├── deconstruct.py  
│       │   │   │   ├── deconstruct.pyc  
│       │   │   │   ├── decorators.py  
│       │   │   │   ├── decorators.pyc  
│       │   │   │   ├── deprecation.py  
│       │   │   │   ├── deprecation.pyc  
│       │   │   │   ├── duration.py  
│       │   │   │   ├── duration.pyc  
│       │   │   │   ├── encoding.py  
│       │   │   │   ├── encoding.pyc  
│       │   │   │   ├── feedgenerator.py  
│       │   │   │   ├── feedgenerator.pyc  
│       │   │   │   ├── formats.py  
│       │   │   │   ├── formats.pyc  
│       │   │   │   ├── functional.py  
│       │   │   │   ├── functional.pyc  
│       │   │   │   ├── glob.py  
│       │   │   │   ├── glob.pyc  
│       │   │   │   ├── html.py  
│       │   │   │   ├── html.pyc  
│       │   │   │   ├── html_parser.py  
│       │   │   │   ├── html_parser.pyc  
│       │   │   │   ├── http.py  
│       │   │   │   ├── http.pyc  
│       │   │   │   ├── inspect.py  
│       │   │   │   ├── inspect.pyc  
│       │   │   │   ├── ipv6.py  
│       │   │   │   ├── ipv6.pyc  
│       │   │   │   ├── itercompat.py  
│       │   │   │   ├── itercompat.pyc  
│       │   │   │   ├── jslex.py  
│       │   │   │   ├── jslex.pyc  
│       │   │   │   ├── log.py  
│       │   │   │   ├── log.pyc  
│       │   │   │   ├── lorem_ipsum.py  
│       │   │   │   ├── lorem_ipsum.pyc  
│       │   │   │   ├── lru_cache.py  
│       │   │   │   ├── lru_cache.pyc  
│       │   │   │   ├── module_loading.py  
│       │   │   │   ├── module_loading.pyc  
│       │   │   │   ├── numberformat.py  
│       │   │   │   ├── numberformat.pyc  
│       │   │   │   ├── regex_helper.py  
│       │   │   │   ├── regex_helper.pyc  
│       │   │   │   ├── safestring.py  
│       │   │   │   ├── safestring.pyc  
│       │   │   │   ├── six.py  
│       │   │   │   ├── six.pyc  
│       │   │   │   ├── synch.py  
│       │   │   │   ├── synch.pyc  
│       │   │   │   ├── termcolors.py  
│       │   │   │   ├── termcolors.pyc  
│       │   │   │   ├── text.py  
│       │   │   │   ├── text.pyc  
│       │   │   │   ├── timesince.py  
│       │   │   │   ├── timesince.pyc  
│       │   │   │   ├── timezone.py  
│       │   │   │   ├── timezone.pyc  
│       │   │   │   ├── translation  
│       │   │   │   ├── tree.py  
│       │   │   │   ├── tree.pyc  
│       │   │   │   ├── version.py  
│       │   │   │   ├── version.pyc  
│       │   │   │   ├── xmlutils.py  
│       │   │   │   └── xmlutils.pyc  
│       │   │   └── views  
│       │   │       ├── __init__.py  
│       │   │       ├── __init__.pyc  
│       │   │       ├── csrf.py  
│       │   │       ├── csrf.pyc  
│       │   │       ├── debug.py  
│       │   │       ├── debug.pyc  
│       │   │       ├── decorators  
│       │   │       ├── defaults.py  
│       │   │       ├── defaults.pyc  
│       │   │       ├── generic  
│       │   │       ├── i18n.py  
│       │   │       ├── i18n.pyc  
│       │   │       ├── static.py  
│       │   │       └── static.pyc  
│       │   ├── django_sendfile-0.3.10-py2.7.egg-info  
│       │   │   ├── PKG-INFO  
│       │   │   ├── SOURCES.txt  
│       │   │   ├── dependency_links.txt  
│       │   │   ├── installed-files.txt  
│       │   │   ├── requires.txt  
│       │   │   ├── top_level.txt  
│       │   │   └── zip-safe  
│       │   ├── easy_install.py  
│       │   ├── easy_install.pyc  
│       │   ├── pip  
│       │   │   ├── __init__.py  
│       │   │   ├── __init__.pyc  
│       │   │   ├── __main__.py  
│       │   │   ├── __main__.pyc  
│       │   │   ├── backwardcompat  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── ssl_match_hostname.py  
│       │   │   │   └── ssl_match_hostname.pyc  
│       │   │   ├── basecommand.py  
│       │   │   ├── basecommand.pyc  
│       │   │   ├── baseparser.py  
│       │   │   ├── baseparser.pyc  
│       │   │   ├── cacert.pem  
│       │   │   ├── cmdoptions.py  
│       │   │   ├── cmdoptions.pyc  
│       │   │   ├── commands  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── bundle.py  
│       │   │   │   ├── bundle.pyc  
│       │   │   │   ├── completion.py  
│       │   │   │   ├── completion.pyc  
│       │   │   │   ├── freeze.py  
│       │   │   │   ├── freeze.pyc  
│       │   │   │   ├── help.py  
│       │   │   │   ├── help.pyc  
│       │   │   │   ├── install.py  
│       │   │   │   ├── install.pyc  
│       │   │   │   ├── list.py  
│       │   │   │   ├── list.pyc  
│       │   │   │   ├── search.py  
│       │   │   │   ├── search.pyc  
│       │   │   │   ├── show.py  
│       │   │   │   ├── show.pyc  
│       │   │   │   ├── uninstall.py  
│       │   │   │   ├── uninstall.pyc  
│       │   │   │   ├── unzip.py  
│       │   │   │   ├── unzip.pyc  
│       │   │   │   ├── wheel.py  
│       │   │   │   ├── wheel.pyc  
│       │   │   │   ├── zip.py  
│       │   │   │   └── zip.pyc  
│       │   │   ├── download.py  
│       │   │   ├── download.pyc  
│       │   │   ├── exceptions.py  
│       │   │   ├── exceptions.pyc  
│       │   │   ├── index.py  
│       │   │   ├── index.pyc  
│       │   │   ├── locations.py  
│       │   │   ├── locations.pyc  
│       │   │   ├── log.py  
│       │   │   ├── log.pyc  
│       │   │   ├── pep425tags.py  
│       │   │   ├── pep425tags.pyc  
│       │   │   ├── req.py  
│       │   │   ├── req.pyc  
│       │   │   ├── runner.py  
│       │   │   ├── runner.pyc  
│       │   │   ├── status_codes.py  
│       │   │   ├── status_codes.pyc  
│       │   │   ├── util.py  
│       │   │   ├── util.pyc  
│       │   │   ├── vcs  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── bazaar.py  
│       │   │   │   ├── bazaar.pyc  
│       │   │   │   ├── git.py  
│       │   │   │   ├── git.pyc  
│       │   │   │   ├── mercurial.py  
│       │   │   │   ├── mercurial.pyc  
│       │   │   │   ├── subversion.py  
│       │   │   │   └── subversion.pyc  
│       │   │   ├── vendor  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── distlib  
│       │   │   │   ├── html5lib  
│       │   │   │   ├── six.py  
│       │   │   │   └── six.pyc  
│       │   │   ├── wheel.py  
│       │   │   └── wheel.pyc  
│       │   ├── pip-1.4.1-py2.7.egg-info  
│       │   │   ├── PKG-INFO  
│       │   │   ├── SOURCES.txt  
│       │   │   ├── dependency_links.txt  
│       │   │   ├── entry_points.txt  
│       │   │   ├── not-zip-safe  
│       │   │   ├── requires.txt  
│       │   │   └── top_level.txt  
│       │   ├── pkg_resources.py  
│       │   ├── pkg_resources.pyc  
│       │   ├── sendfile  
│       │   │   ├── __init__.py  
│       │   │   ├── __init__.pyc  
│       │   │   ├── backends  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── _internalredirect.py  
│       │   │   │   ├── _internalredirect.pyc  
│       │   │   │   ├── development.py  
│       │   │   │   ├── development.pyc  
│       │   │   │   ├── mod_wsgi.py  
│       │   │   │   ├── mod_wsgi.pyc  
│       │   │   │   ├── nginx.py  
│       │   │   │   ├── nginx.pyc  
│       │   │   │   ├── simple.py  
│       │   │   │   ├── simple.pyc  
│       │   │   │   ├── xsendfile.py  
│       │   │   │   └── xsendfile.pyc  
│       │   │   ├── models.py  
│       │   │   ├── models.pyc  
│       │   │   ├── tests.py  
│       │   │   └── tests.pyc  
│       │   ├── setuptools  
│       │   │   ├── __init__.py  
│       │   │   ├── __init__.pyc  
│       │   │   ├── _backport  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   └── hashlib  
│       │   │   ├── archive_util.py  
│       │   │   ├── archive_util.pyc  
│       │   │   ├── command  
│       │   │   │   ├── __init__.py  
│       │   │   │   ├── __init__.pyc  
│       │   │   │   ├── alias.py  
│       │   │   │   ├── alias.pyc  
│       │   │   │   ├── bdist_egg.py  
│       │   │   │   ├── bdist_egg.pyc  
│       │   │   │   ├── bdist_rpm.py  
│       │   │   │   ├── bdist_rpm.pyc  
│       │   │   │   ├── bdist_wininst.py  
│       │   │   │   ├── bdist_wininst.pyc  
│       │   │   │   ├── build_ext.py  
│       │   │   │   ├── build_ext.pyc  
│       │   │   │   ├── build_py.py  
│       │   │   │   ├── build_py.pyc  
│       │   │   │   ├── develop.py  
│       │   │   │   ├── develop.pyc  
│       │   │   │   ├── easy_install.py  
│       │   │   │   ├── easy_install.pyc  
│       │   │   │   ├── egg_info.py  
│       │   │   │   ├── egg_info.pyc  
│       │   │   │   ├── install.py  
│       │   │   │   ├── install.pyc  
│       │   │   │   ├── install_egg_info.py  
│       │   │   │   ├── install_egg_info.pyc  
│       │   │   │   ├── install_lib.py  
│       │   │   │   ├── install_lib.pyc  
│       │   │   │   ├── install_scripts.py  
│       │   │   │   ├── install_scripts.pyc  
│       │   │   │   ├── register.py  
│       │   │   │   ├── register.pyc  
│       │   │   │   ├── rotate.py  
│       │   │   │   ├── rotate.pyc  
│       │   │   │   ├── saveopts.py  
│       │   │   │   ├── saveopts.pyc  
│       │   │   │   ├── sdist.py  
│       │   │   │   ├── sdist.pyc  
│       │   │   │   ├── setopt.py  
│       │   │   │   ├── setopt.pyc  
│       │   │   │   ├── test.py  
│       │   │   │   ├── test.pyc  
│       │   │   │   ├── upload.py  
│       │   │   │   ├── upload.pyc  
│       │   │   │   ├── upload_docs.py  
│       │   │   │   └── upload_docs.pyc  
│       │   │   ├── compat.py  
│       │   │   ├── compat.pyc  
│       │   │   ├── depends.py  
│       │   │   ├── depends.pyc  
│       │   │   ├── dist.py  
│       │   │   ├── dist.pyc  
│       │   │   ├── extension.py  
│       │   │   ├── extension.pyc  
│       │   │   ├── package_index.py  
│       │   │   ├── package_index.pyc  
│       │   │   ├── py24compat.py  
│       │   │   ├── py24compat.pyc  
│       │   │   ├── py27compat.py  
│       │   │   ├── py27compat.pyc  
│       │   │   ├── sandbox.py  
│       │   │   ├── sandbox.pyc  
│       │   │   ├── script template (dev).py  
│       │   │   ├── script template (dev).pyc  
│       │   │   ├── script template.py  
│       │   │   ├── script template.pyc  
│       │   │   ├── site-patch.py  
│       │   │   ├── site-patch.pyc  
│       │   │   ├── ssl_support.py  
│       │   │   ├── ssl_support.pyc  
│       │   │   └── tests  
│       │   │       ├── __init__.py  
│       │   │       ├── __init__.pyc  
│       │   │       ├── doctest.py  
│       │   │       ├── doctest.pyc  
│       │   │       ├── py26compat.py  
│       │   │       ├── py26compat.pyc  
│       │   │       ├── server.py  
│       │   │       ├── server.pyc  
│       │   │       ├── test_bdist_egg.py  
│       │   │       ├── test_bdist_egg.pyc  
│       │   │       ├── test_build_ext.py  
│       │   │       ├── test_build_ext.pyc  
│       │   │       ├── test_develop.py  
│       │   │       ├── test_develop.pyc  
│       │   │       ├── test_dist_info.py  
│       │   │       ├── test_dist_info.pyc  
│       │   │       ├── test_easy_install.py  
│       │   │       ├── test_easy_install.pyc  
│       │   │       ├── test_egg_info.py  
│       │   │       ├── test_egg_info.pyc  
│       │   │       ├── test_markerlib.py  
│       │   │       ├── test_markerlib.pyc  
│       │   │       ├── test_packageindex.py  
│       │   │       ├── test_packageindex.pyc  
│       │   │       ├── test_resources.py  
│       │   │       ├── test_resources.pyc  
│       │   │       ├── test_sandbox.py  
│       │   │       ├── test_sandbox.pyc  
│       │   │       ├── test_sdist.py  
│       │   │       ├── test_sdist.pyc  
│       │   │       ├── test_test.py  
│       │   │       ├── test_test.pyc  
│       │   │       ├── test_upload_docs.py  
│       │   │       └── test_upload_docs.pyc  
│       │   ├── setuptools-0.9.8-py2.7.egg-info  
│       │   │   ├── PKG-INFO  
│       │   │   ├── SOURCES.txt  
│       │   │   ├── dependency_links.txt  
│       │   │   ├── entry_points.txt  
│       │   │   ├── entry_points.txt.orig  
│       │   │   ├── requires.txt  
│       │   │   ├── top_level.txt  
│       │   │   └── zip-safe  
│       │   ├── unicodecsv  
│       │   │   ├── __init__.py  
│       │   │   ├── __init__.pyc  
│       │   │   ├── py2.py  
│       │   │   ├── py2.pyc  
│       │   │   ├── py3.py  
│       │   │   ├── py3.pyc  
│       │   │   ├── test.py  
│       │   │   └── test.pyc  
│       │   └── unicodecsv-0.14.1-py2.7.egg-info  
│       │       ├── PKG-INFO  
│       │       ├── SOURCES.txt  
│       │       ├── dependency_links.txt  
│       │       ├── installed-files.txt  
│       │       └── top_level.txt  
│       ├── site.py  
│       ├── site.pyc  
│       ├── sre_compile.pyc  
│       ├── sre_constants.pyc  
│       ├── sre_parse.pyc  
│       ├── stat.pyc  
│       ├── types.pyc  
│       └── warnings.pyc  
├── lib64 -> lib  

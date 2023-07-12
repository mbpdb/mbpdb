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

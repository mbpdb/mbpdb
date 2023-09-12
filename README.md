# Milk Bioactive Peptide Database  
## Current live version
### https://mbpdb.nws.oregonstate.edu/  

## Updated demo version 
### https://mbpdbcontainer.lemonisland-71b15397.westus3.azurecontainerapps.io/

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
- peptide_proteininfo  
- peptide_proteinvariant  
- peptide_reference  
- peptide_submission  

### auth_user  
sqlite> PRAGMA table_info(auth_user);  
0|id|INTEGER|1||1  
1|password|varchar(128)|1||0  
2|last_login|datetime|0||0  
3|is_superuser|bool|1||0  
4|username|varchar(150)|1||0  
5|last_name|varchar(150)|1||0  
6|email|varchar(254)|1||0  
7|is_staff|bool|1||0  
8|is_active|bool|1||0  
9|date_joined|datetime|1||0  
10|first_name|varchar(150)|1||0  

sqlite> SELECT * FROM auth_user LIMIT 10;  
1|pbkdf2_sha256$12000$c2EfcHud3ME5$3T+ADB5kMAos8BNleYv1DlN9JLXkicpH8q7z+R/eFCA=|2014-11-24 22:46:53|0|adam||amschaal@ucdavis.edu|1|1|2014-11-24 22:46:53|  
2|pbkdf2_sha256$24000$ucEO0EwNCHhW$RHdVVDYxTzCy94P8bjcIoIo6Ro89vHegl4IfJKgvKmI=|2018-03-01 09:30:25.321274|1|joshi||najoshi@ucdavis.edu|1|1|2017-03-27 22:54:51|  
3|pbkdf2_sha256$24000$8JaUoEua9cFF$ogn4yB+MZn4zwwrykQnoui38/M/DlDRZQlRBJjJPWxA=|2023-07-19 21:10:13.939510|1|nielsen|Nielsen|sdrudn2@gmail.com|1|1|2017-04-20 10:04:29|Soeren  
4|pbkdf2_sha256$24000$baK95dAwK1bD$nl+Be0pjPUSHdjZXrHYQbrGjFjkocEPDqVoMBeqnXD4=|2020-02-19 20:28:45.716484|0|David||Dave.Dallas@oregonstate.edu|1|1|2020-02-19 20:26:09|  
5|pbkdf2_sha256$24000$p0U0rsXf9dQS$PC7h+l6SBejXO38C+TkSvMc4Sa8Rs1N8z4rCTJUoCQ4=||1|nielsen2|||1|1|2023-01-12 10:40:29|  
6|pbkdf2_sha256$600000$7aUDkfk6hGY0XwSW6UwAJH$S1eWyWkUcmAohPBh9a9cFlx8w75EAarcNNpY6TsM97M=|2023-09-05 18:18:42.459196|1|rusty||kuhfeldr@oregonstate.edu|1|1|2023-08-21 17:07:01.992304|  
 

### auth_user_user_permissions  
sqlite> PRAGMA table_info(auth_user_user_permissions);  
0|id|INTEGER|1||1  
1|user_id|INTEGER|1||0  
2|permission_id|INTEGER|1||0  


### django_admin_log  
sqlite> PRAGMA table_info(django_admin_log);  
0|id|INTEGER|1||1  
1|object_id|TEXT|0||0  
2|object_repr|varchar(200)|1||0  
3|action_flag|smallint unsigned|1||0  
4|change_message|TEXT|1||0  
5|content_type_id|INTEGER|0||0  
6|user_id|INTEGER|1||0  
7|action_time|datetime|1||0  


### django_migrations   
sqlite> PRAGMA table_info(django_migrations);  
1|contenttypes|0001_initial|2014-11-24 22:46:12.044994  
2|auth|0001_initial|2014-11-24 22:46:12.370643  
3|admin|0001_initial|2014-11-24 22:46:12.638026  


### django_session
sqlite> PRAGMA table_info(django_session);  
0|session_key|varchar(40)|1||1  
1|session_data|TEXT|1||0  
2|expire_date|datetime|1||0  


### peptide_counter  
sqlite> SELECT COUNT(*) FROM peptide_counter;  
68414 -> 2022  
232186 -> 2023  


sqlite> PRAGMA table_info(peptide_counter);  
0|id|INTEGER|1||1  
1|ip|varchar(40)|1||0  
2|access_time|datetime|1||0  
3|page|varchar(40)|1||0  

### peptide_function  
sqlite> SELECT COUNT(*) FROM peptide_function;  
916  
sqlite> SELECT * FROM peptide_function LIMIT 3;  
1|DPP-IV Inhibitory|2976  
2|DPP-IV Inhibitory|2977  
3|DPP-IV Inhibitory|2978  

sqlite> PRAGMA table_info(peptide_function);  
0|id|INTEGER|1||1  
1|function|varchar(400)|1||0  
2|pep_id|INTEGER|1||0  


### peptide_peptideinfo  
sqlite> SELECT COUNT(*) FROM peptide_peptideinfo;  
712  

sqlite> PRAGMA table_info(peptide_peptideinfo);  
0|id|INTEGER|1||1  
1|peptide|varchar(300)|1||0  
2|protein_id|INTEGER|1||0  
3|length|INTEGER|1||0  
4|intervals|varchar(100)|1||0  
5|protein_variants|varchar(100)|1||0  
6|time_approved|datetime|1||0  


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
sqlite> SELECT COUNT(*) FROM peptide_reference;  
1087  
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
sqlite> PRAGMA table_info(peptide_submission);  
0|id|INTEGER|0||1  
1|protein_id|varchar(30)|1||0  
2|peptide|varchar(300)|1||0  
3|function|varchar(400)|1||0  
4|secondary_function|varchar(400)|1||0  
5|title|varchar(300)|1||0  
6|authors|varchar(300)|1||0  
7|abstract|varchar(1000)|1||0  
8|doi|varchar(100)|1||0  
9|time_submitted|datetime|1||0  
10|length|INTEGER|1||0  
11|intervals|varchar(100)|1||0  
12|ptm|varchar(200)|1||0  
13|protein_variants|varchar(30)|1||0  

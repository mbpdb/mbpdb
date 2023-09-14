# Milk Bioactive Peptide Database  
## Current live version
### https://mbpdb.nws.oregonstate.edu/  

## Updated demo version 
### https://mbpdbcontainer.lemonisland-71b15397.westus3.azurecontainerapps.io/

# Database infromation:  
### Database file: /include/peptide/db.sqlite3  
### tables:
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
sqlite> SELECT COUNT(*) FROM auth_user;  
6  

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


### auth_user_user_permissions
sqlite> SELECT COUNT(*) FROM auth_user_user_permissions;  
39  

sqlite> PRAGMA table_info(auth_user_user_permissions);  
0|id|INTEGER|1||1  
1|user_id|INTEGER|1||0  
2|permission_id|INTEGER|1||0  


### django_admin_log
sqlite> SELECT COUNT(*) FROM django_admin_log;  
1055    

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
sqlite> SELECT COUNT(*) FROM django_migrations;  
62  

sqlite> PRAGMA table_info(django_migrations);  
1|contenttypes|0001_initial|2014-11-24 22:46:12.044994  
2|auth|0001_initial|2014-11-24 22:46:12.370643  
3|admin|0001_initial|2014-11-24 22:46:12.638026  


### django_session
sqlite> SELECT COUNT(*) FROM django_session;  
127  

sqlite> PRAGMA table_info(django_session);  
0|session_key|varchar(40)|1||1  
1|session_data|TEXT|1||0  
2|expire_date|datetime|1||0  


### peptide_counter
sqlite> SELECT COUNT(*) FROM peptide_counter;  
2022 = 68414  
2023 = 232186  

sqlite> PRAGMA table_info(peptide_counter);  
0|id|INTEGER|1||1  
1|ip|varchar(40)|1||0  
2|access_time|datetime|1||0  
3|page|varchar(40)|1||0  


### peptide_function
sqlite> SELECT COUNT(*) FROM peptide_function;  
916  

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
sqlite> SELECT COUNT(*) FROM peptide_proteininfo;  
120538  

sqlite> PRAGMA table_info(peptide_proteininfo);  
0|id|INTEGER|1||1   
1|pid|varchar(30)|1||0  
2|desc|varchar(500)|1||0  
3|species|varchar(70)|1||0  
4|header|varchar(1000)|1||0  
5|seq|varchar(5000)|1||0  


### peptide_proteinvariant
sqlite> SELECT COUNT(*) FROM peptide_proteinvariant;  
26  

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
sqlite> SELECT COUNT(*) FROM peptide_submission;  
0  

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


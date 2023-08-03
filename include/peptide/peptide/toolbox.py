import subprocess, os
from django.conf import settings
import time
import shutil
import csv
from glob import glob
from Bio import SeqIO
from django.utils import timezone
from .models import PeptideInfo, Reference, Function, ProteinInfo, Submission, ProteinVariant
import re, sys
from collections import defaultdict
from django.db.models import Q
from datetime import datetime
from django.core.mail import send_mail
from django.contrib.auth.models import User
from chardet.universaldetector import UniversalDetector
#from bs4 import UnicodeDammit
import codecs

def create_work_directory(base_dir):
    path = os.path.join(base_dir,'work_%d'%int(round(time.time() * 1000)))
    os.makedirs(path)
    return path

def handle_uploaded_file(request_file, path):
    with open(path, 'wb') as destination:
        for chunk in request_file.chunks():
            destination.write(chunk)
            
def get_tsv_path(request_file,directory_path=None):
    if directory_path is None:
        directory_path = settings.WORK_DIRECTORY
    path = os.path.join(directory_path, request_file.name).replace(' ','_')
    handle_uploaded_file(request_file,path)
    return path


def skyline_pipeline(input_tsv,input_xmls,output_path):
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_tsv_path = os.path.join(work_path, input_tsv.name).replace(' ','_')
    handle_uploaded_file(input_tsv,input_tsv_path)
    input_xml_paths = []
    for input_xml in input_xmls:
        path = os.path.join(work_path, input_xml.name).replace(' ','_')
        handle_uploaded_file(input_xml,path)
        input_xml_paths.append(path)
    output = subprocess.check_output([settings.SKYLINE,input_tsv_path,output_path]+input_xml_paths,stderr=subprocess.STDOUT)
    
def skyline_pipeline_auto(idotp,reduce_columns,only_keep_true,input_tsv,input_xmls):
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_tsv_path = os.path.join(work_path, input_tsv.name).replace(' ','_')
    handle_uploaded_file(input_tsv,input_tsv_path)
    input_xml_paths = []
    for input_xml in input_xmls:
        path = os.path.join(work_path, input_xml.name).replace(' ','_')
        handle_uploaded_file(input_xml,path)
        input_xml_paths.append(path)
    output_path = os.path.join(work_path, "skyline_auto_%s.tsv"%time.strftime('%Y-%m-%d_%H.%M.%S',time.localtime()))
    filter_output_path = os.path.join(work_path, "filtered.tsv")
    auto_output_path = os.path.join(work_path, "auto.tsv")
    edit_output_path = os.path.join(work_path, "edit.tsv")

    # run filter
    subprocess.check_output([settings.FILTER, input_tsv_path, filter_output_path, idotp, only_keep_true], stderr=subprocess.STDOUT)

    # run skyline auto
    output = subprocess.check_output([settings.SKYLINE_AUTO,filter_output_path,auto_output_path]+input_xml_paths,stderr=subprocess.STDOUT)
    # f = open('/tmp/argfile','w')
    # f.write(settings.FILTER + ' ' + filter_output_path + ' ' + idotp + ' ' + only_keep_true + "\n")
    # f.write(settings.SKYLINE_EDIT + ' ' + auto_output_path + ' ' + output_path + ' ' + reduce_columns + "\n")
    # f.close()

    # run combine peptides
    subprocess.check_output([settings.COMBINE_PEPTIDES, auto_output_path, edit_output_path], stderr=subprocess.STDOUT)

    # run edit columns
    subprocess.check_output([settings.SKYLINE_EDIT, edit_output_path, output_path, reduce_columns], stderr=subprocess.STDOUT)
    return output_path

def contact_us(name, email, message):
    suq = User.objects.filter(is_superuser=1)
    email_subject = "MBPDB question/issue from " + name + " <" + email + ">"
    send_mail(email_subject, message + "\n\n" + name + "\n" + email, 'MBPDB contact us <noreply@nws.oregonstate.edu>',[e.email for e in suq])

    return "Message submitted to MBPDB admins. We will get back to you soon."

def peptide_db_call(pep, category, protid, function, secondary_func, ptm, title, authors, abstract, doi):

    try:
        idcheck = ProteinInfo.objects.get(pid=protid)
    except ProteinInfo.DoesNotExist:
        return "Warning: Protein ID "+protid+" not found in database. Entry not submitted. You can use the 'MBPDB add proteins' tool to add the protein to the database."

    prot = idcheck.seq
    intervals = ', '.join([str(m.start()+1) + "-" + str(m.start()+len(pep)) for m in re.finditer(pep, prot)])
    pvid_list=[]
    interval_list=[]

    if not intervals:
        gv_check = ProteinVariant.objects.filter(protein=idcheck)
        for pv in gv_check:
            intervals = ', '.join([str(m.start()+1) + "-" + str(m.start()+len(pep)) for m in re.finditer(pep, pv.seq)])
            if intervals:
                pvid_list.append(pv.pvid)
                interval_list.append(intervals)
        if not pvid_list:
            return "Warning: Peptide "+pep+" not found in protein (or variants). Entry not submitted."

    else:
        interval_list=[intervals]

    tn = datetime.now()
    sub = Submission(protein_id=protid, protein_variants=','.join(pvid_list), peptide=pep, category=category, function=function, secondary_function=secondary_func, ptm=ptm, title=title, authors=authors, abstract=abstract, doi=doi, intervals=':'.join(interval_list), length=len(pep), time_submitted=tn)
    sub.save()

    suq = User.objects.filter(is_superuser=1)
    email_subject = "New Peptide Submission %s" % time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
    send_mail(email_subject, 'There is 1 new peptide submission for the MBPDB.', 'New Peptides <noreply@nws.oregonstate.edu>',[e.email for e in suq])

    return "Entry submitted for approval."


def pepdb_add_csv(csv_file, messages):
    csv.register_dialect('pep_dialect', delimiter='\t')

    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_tsv_path = os.path.join(work_path, csv_file.name).replace(' ','_')
    handle_uploaded_file(csv_file,input_tsv_path)
    records=0

    # remove weird characters from end of fields
    temp_file = os.path.join(work_path, "temp.csv")
    subprocess.check_output(['dos2unix','-q',input_tsv_path], stderr=subprocess.STDOUT)
    subprocess.check_output([settings.FIX_WEIRD_CHARS,input_tsv_path,temp_file], stderr=subprocess.STDOUT)
    subprocess.check_output(['mv',temp_file,input_tsv_path], stderr=subprocess.STDOUT)

    '''
    f1 = open(input_tsv_path,'r')
    filedata = f1.read()
    f1.close()
    f2 = codecs.open(input_tsv_path,'w',encoding='utf-8')
    dammit = UnicodeDammit(filedata,['latin-1'])
    f2.write(dammit.unicode_markup)
    f2.close()
    '''

    # detecting file encoding
    detector = UniversalDetector()
    for line in open(input_tsv_path, 'rb'):
        detector.feed(line)
        if detector.done: break
    detector.close()

    # if file is not UTF-8, attempt to recode to UTF-8
    if detector.result['encoding'].lower() != "utf-8":
        subprocess.check_output(['recode',detector.result['encoding']+'..UTF-8',input_tsv_path], stderr=subprocess.STDOUT)

    try:
        rownum=1
        with open(input_tsv_path, 'r', encoding='utf-8') as pepfile:
            data = csv.DictReader(pepfile, dialect='pep_dialect')
            headers = list(data.fieldnames)
            headers = list(filter(None, headers)) # remove empty column headers
            headers.sort()

            # check if headers are correct
            if headers != ['abstract', 'authors', 'category', 'doi', 'function', 'peptide', 'proteinID', 'ptm', 'secondary_function', 'title']:
                raise subprocess.CalledProcessError(1, cmd="", output="Error: Input file does not have the correct headers (proteinID, peptide, category, function, secondary_function, ptm, title, authors, abstract, and doi).")

            err=0
            for row in data:
                rownum = rownum + 1

                if (row['peptide']=='' or row['proteinID']=='' or row['function']=='' or row['title']=='' or row['authors']=='' or row['doi']==''):
                    messages.append("Error: Line "+str(rownum)+" in file has values that cannot be empty (only abstract, secondary function, ptm, and category can be empty).")
                    err+=1
                    continue

                protid = row['proteinID']

                try:
                    idcheck = ProteinInfo.objects.get(pid=protid)
                except ProteinInfo.DoesNotExist:
                    messages.append("Error: Protein ID "+protid+" not found in database (Line "+str(rownum)+"). Skipping. You can use the Add Fasta Files tool to add the protein to the database.")
                    err+=1
                    continue

                prot = idcheck.seq
    
                # calculate start and stop intervals
                intervals = ', '.join([str(m.start()+1) + "-" + str(m.start()+len(row['peptide'])) for m in re.finditer(row['peptide'], prot)])

                pvid_list=[]

                if not intervals:
                    gv_check = ProteinVariant.objects.filter(protein=idcheck)
                    for pv in gv_check:
                        intervals = ', '.join([str(m.start()+1) + "-" + str(m.start()+len(row['peptide'])) for m in re.finditer(row['peptide'], pv.seq)])
                        if intervals:
                            pvid_list.append(pv.pvid)
                    if not pvid_list:
                        messages.append("Error: Peptide "+row['peptide']+" not found in protein or variants (ID "+protid+", Line "+str(rownum)+").")
                        err+=1
                        continue


            if err == 0:
                with open(input_tsv_path, 'r') as pepfile2:
                    data = csv.DictReader(pepfile2, dialect='pep_dialect')
                    tn = datetime.now()
                    count=0
                    for row in data:
                        idcheck = ProteinInfo.objects.get(pid=row['proteinID'])
                        prot = idcheck.seq

                        intervals = ', '.join([str(m.start()+1) + "-" + str(m.start()+len(row['peptide'])) for m in re.finditer(row['peptide'], prot)])

                        pvid_list=[]
                        interval_list=[]

                        if not intervals:
                            gv_check = ProteinVariant.objects.filter(protein=idcheck)
                            for pv in gv_check:
                                intervals = ', '.join([str(m.start()+1) + "-" + str(m.start()+len(row['peptide'])) for m in re.finditer(row['peptide'], pv.seq)])
                                if intervals:
                                    pvid_list.append(pv.pvid)
                                    interval_list.append(intervals)
                        else:
                            interval_list=[intervals]

                        sub = Submission(protein_id=row['proteinID'], peptide=row['peptide'], category=row['category'], function=row['function'], secondary_function=row['secondary_function'], ptm=row['ptm'], title=row['title'], authors=row['authors'], abstract=row['abstract'], doi=row['doi'], intervals=':'.join(interval_list), protein_variants=','.join(pvid_list), length=len(row['peptide']), time_submitted=tn)
                        sub.save()
                        count += 1

                    suq = User.objects.filter(is_superuser=1)
                    email_subject = "New Peptide Submission %s" % time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
                    send_mail(email_subject, 'There are '+str(count)+' new peptide submissions for the MBPDB.', 'New Peptides <'+settings.NOREPLY_EMAIL+'>',[e.email for e in suq])

                    if detector.result['encoding'].lower() != "utf-8":
                        messages.append("Warning: Detected encoding for input file was not UTF-8 (It was detected as "+detector.result['encoding']+"). Recoding was attempted but if this is not the correct original encoding, then non-standard characters may not have been recoded correctly.")
                    messages.append("No errors found. "+str(count)+" entries have been submitted for approval.")
            else:
                errbit = "errors" if err > 1 else "error"
                messages.append(str(err)+" "+errbit+" found. Please correct and resubmit the file.")

    except UnicodeDecodeError:
        raise subprocess.CalledProcessError(1, cmd="", output="Error: File needs to use Unicode (UTF-8) encoding. Conversion failed.")

    return messages



def pepdb_approve(queryset):

    messages=[]
    records=0
    for e in queryset:
        try:
            idcheck = ProteinInfo.objects.get(pid=e.protein_id)
        except ProteinInfo.DoesNotExist:
            messages.append("Error: Protein ID "+e.protein_id+" not found in database for peptide "+e.peptide+". Skipping. You can use the Add Fasta Files tool to add the protein to the database.")
            continue

        try:
            pepcheck = PeptideInfo.objects.get(peptide=e.peptide)
        except PeptideInfo.DoesNotExist:
            tn = datetime.now()
            pepinfo = PeptideInfo(peptide=e.peptide, protein_variants=e.protein_variants, category=e.category, protein=idcheck, length=e.length, intervals=e.intervals, time_approved=tn)
            pepinfo.save()
            f = Function(pep=pepinfo, function=e.function)
            f.save()
            r = Reference(func=f, title=e.title, authors=e.authors, abstract=e.abstract, doi=e.doi, secondary_func=e.secondary_function, ptm=e.ptm)
            r.save()
            records = records + 1
            e.delete()
            continue

        try:
            fcheck = Function.objects.get(pep=pepcheck, function=e.function)
        except Function.DoesNotExist:
            f = Function(pep=pepcheck, function=e.function)
            f.save()
            r = Reference(func=f, title=e.title, authors=e.authors, abstract=e.abstract, doi=e.doi, secondary_func=e.secondary_function, ptm=e.ptm)
            r.save()
            records = records + 1
            e.delete()
            continue

        try:
            doi_check = Reference.objects.get(func=fcheck, doi=e.doi)
            if (doi_check.secondary_func != '' and e.secondary_function != '') or (doi_check.ptm != '' and e.ptm != ''):
                if doi_check.secondary_func != '' and e.secondary_function != '':
                    doi_check.secondary_func = e.secondary_function
                    doi_check.save()
                    messages.append("Peptide "+e.peptide+" with Function '"+e.function+"' and DOI '"+e.doi+"' found. Updated secondary function to '"+e.secondary_function+"'.")

                if doi_check.ptm != '' and e.ptm != '':
                    doi_check.ptm = e.ptm
                    doi_check.save()
                    messages.append("Peptide "+e.peptide+" with Function '"+e.function+"' and DOI '"+e.doi+"' found. Updated PTM to '"+e.ptm+"'.")

                e.delete()
                records = records + 1
                continue
        except Reference.DoesNotExist:
            r = Reference(func=fcheck, title=e.title, authors=e.authors, abstract=e.abstract, doi=e.doi, secondary_func=e.secondary_function, ptm=e.ptm)
            r.save()
            records = records + 1
            e.delete()
            continue

        messages.append("Warning: Peptide "+e.peptide+" with Function '"+e.function+"' and DOI '"+e.doi+"' already exists in DB.")
        e.delete()
        continue

    messages.append("Added "+str(records)+" submissions to database.")
    return messages


def run_blastp(q,peptide,matrix):
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    query_path = os.path.join(work_path, "query.fasta")
    fasta_db_path = os.path.join(work_path, "db.fasta")
    output_path = os.path.join(work_path, "blastp_short.out")
    fasta_db_file = open(fasta_db_path, "w")
    for info in q:
        fasta_db_file.write(">"+str(info.id)+"\n"+info.peptide+"\n")
    fasta_db_file.close()

    query_file = open(query_path, "w")
    query_file.write(">pep_query\n"+peptide+"\n")
    query_file.close()

    make_blast_db(fasta_db_path)
    subprocess.check_output(["blastp","-query",query_path,"-db",fasta_db_path,"-outfmt","6 std ppos qcovs qlen slen positive","-evalue","1000","-word_size","2","-matrix",matrix,"-threshold","1","-task","blastp-short","-out",output_path], stderr=subprocess.STDOUT)

    csv.register_dialect('blast_dialect', delimiter='\t')
    output_file = open(output_path, "r")
    data = csv.DictReader(output_file, fieldnames=['query','subject','percid','align_len','mismatches','gaps','qstart','qend','sstart','send','evalue','bitscore','ppos','qcov','qlen','slen','numpos'], dialect='blast_dialect')

    return data



def pepdb_search_tsv_line(writer, peptide, peptide_option, seqsim, matrix, extra, pid, function, species, category):
    #(peptide,peptide_option,pid,function,seqsim,matrix,extra,species,category)
    results = ''
    extra_info = defaultdict(list)
    q = PeptideInfo.objects.all()

    if pid != "":
        try:
            protid_check = ProteinInfo.objects.get(pid__iexact=pid)
        except ProteinInfo.DoesNotExist:
            writer.writerow(["Protein ID "+pid+" does not exist in database."])
            results += "<h3>Protein ID "+pid+" does not exist in database.</h3>"
            return results

        q = PeptideInfo.objects.filter(protein=protid_check)

    if species != "":
        # if species is "cow" or "pig" etc., then also search for scientific names

        spec_list=[]
        for l in settings.TRANSLATE_LIST:
            if species.lower() in l:
                spec_list = list(l)

        if spec_list:
            q_obj = Q(species__iexact = spec_list[0])
            for s in spec_list[1:]:
                q_obj = q_obj | Q(species__iexact = s)
                #print str(q_obj)

            proteins = ProteinInfo.objects.filter(q_obj)
            protein_ids = [proobj.id for proobj in proteins]
            tempids = PeptideInfo.objects.filter(protein__in=protein_ids)
            search_ids = [pepobj.id for pepobj in tempids]
            q = q.filter(id__in=search_ids)
        else:
            q = q.filter(protein__species__icontains=species)

    if category != "":
        q = q.filter(category__icontains=category)

    if peptide != "":
        if peptide_option == "sequence":
            if (len(peptide) < 4 or (seqsim == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__iexact=peptide)
            else:
                data = run_blastp(q,peptide,matrix)
                search_ids=[]
                for row in data:
                    tlen = float(row['slen']) if float(row['slen']) > float(row['qlen']) else float(row['qlen'])
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / tlen)
                    if simcalc >= seqsim:
                        search_ids.append(row['subject'])
                        extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

                q = q.filter(id__in=search_ids)

        elif peptide_option == "truncated":
            if (len(peptide) < 4 or (seqsim == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__icontains=peptide)
            else:
                data = run_blastp(q,peptide,matrix)
                search_ids=[]
                for row in data:
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / float(row['qlen']))
                    if simcalc >= seqsim:
                        search_ids.append(row['subject'])
                        extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

                q = q.filter(id__in=search_ids)

        elif peptide_option == "precursor":
            search_ids=[]
            # select * from peptide_peptideinfo where 'LLFFVAPLL' LIKE '%' || peptide_peptideinfo.peptide || '%';
            tempids = PeptideInfo.objects.raw("select id from peptide_peptideinfo where %s LIKE '%%' || peptide_peptideinfo.peptide || '%%'", [peptide]);
            search_ids = [pepobj.id for pepobj in tempids]

            data = run_blastp(q,peptide,matrix)
            for row in data:
                simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / float(row['qlen']))
                if (simcalc >= seqsim and int(row['qlen']) > int(row['slen'])):
                    search_ids.append(row['subject'])
                    extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

            q = q.filter(id__in=search_ids)


    if function != "":
        q = q.filter(functions__function__icontains=function)

    if (q.count() == 0):
        writer.writerow(["No records found for search."])
        results += "<h3>No records found for search.</h3>"
        return results
        #raise subprocess.CalledProcessError(1, cmd="", output="No records found for search. Protein: '"+protein+"', Peptide: '"+peptide+"', query: "+str(q.query))

    if extra:
        writer.writerow (('proteinID','peptide','category','protein description','species','intervals','function','secondary function','ptm','title','authors','abstract','doi','% alignment','query start','query end','subject start','subject end','e-value','alignment length','mismatches','gap opens'))
        results += '<tr><th style="padding:10px;">proteinID</th><th style="padding:10px;" width="200px">peptide</th><th style="padding:10px;">category</th><th style="padding:10px;">protein description</th><th style="padding:10px;">species</th><th style="padding:10px;">intervals</th><th style="padding:10px;">function</th><th style="padding:10px;">secondary function</th><th style="padding:10px;">ptm</th><th style="padding:10px;">title</th><th style="padding:10px;">authors</th><th style="padding:10px;">abstract</th><th style="padding:10px;">doi</th><th>% alignment</th><th style="padding:10px;">query start</th><th style="padding:10px;">query end</th><th style="padding:10px;">subject start</th><th style="padding:10px;">subject end</th><th style="padding:10px;">e-value</th><th style="padding:10px;">alignment length</th><th style="padding:10px;">mismatches</th><th style="padding:10px;">gap opens</th></tr><tr><td>\n'
    else:
        writer.writerow (('proteinID','peptide','category','protein description','species','intervals','function','secondary function','ptm','title','authors','abstract','doi'))
        results += '<tr><th style="padding:10px;">proteinID</th><th style="padding:10px;" width="200px">peptide</th><th style="padding:10px;">category</th><th style="padding:10px;">protein description</th><th style="padding:10px;">species</th><th style="padding:10px;">intervals</th><th style="padding:10px;">function</th><th style="padding:10px;">secondary function</th><th style="padding:10px;">ptm</th><th style="padding:10px;">title</th><th style="padding:10px;">authors</th><th style="padding:10px;">abstract</th><th style="padding:10px;">doi</th></tr><tr><td>\n'


    for info in q:

        if function != "":
            fcheck = Function.objects.filter(pep=info, function__icontains=function)
        else:
            fcheck = Function.objects.filter(pep=info)

        for func in fcheck:

            temprow2=[]
            pp = info.protein.pid
            pd = info.protein.desc
            if info.protein_variants:
                pp = pp + " Genetic Variant " + info.protein_variants
                pd = pd + " Genetic Variant " + info.protein_variants
            temprow = [pp,info.peptide,info.category,pd,info.protein.species,info.intervals]
            if peptide_option == "truncated":
                temprow2 = [pp,info.peptide.replace(peptide,"<b>"+peptide+"</b>"),info.category,pd,info.protein.species,info.intervals]

            refs = Reference.objects.filter(func=func)
            titles=[]
            authors=[]
            abstracts=[]
            dois=[]
            sf=[]
            ptms=[]
            titnum=1
            for ref in refs:
                if ref.title != '': titles.append("("+str(titnum)+") "+ref.title+". ")
                if ref.secondary_func != '': sf.append("("+str(titnum)+") "+ref.secondary_func+". ")
                if ref.ptm != '': ptms.append("("+str(titnum)+") "+ref.ptm+". ")
                titnum+=1
                if ref.authors != '': authors.append(ref.authors)
                if ref.abstract != '': abstracts.append(ref.abstract)
                dois.append(ref.doi)

            temprow.extend((func.function,', '.join(sf),', '.join(ptms),', '.join(titles),', '.join(authors),', '.join(abstracts),', '.join(dois)))
            if peptide_option == "truncated":
                temprow2.extend((func.function,', '.join(sf),', '.join(ptms),', '.join(titles),', '.join(authors),', '.join(abstracts),', '.join(dois)))

            if extra:
                if str(info.id) in extra_info:
                    temprow.extend(extra_info[str(info.id)])
                    if peptide_option == "truncated":
                        temprow2.extend(extra_info[str(info.id)])
                else:
                    temprow.extend((u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t'))
                    if peptide_option == "truncated":
                        temprow2.extend((u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t'))

            writer.writerow(temprow)

            if peptide_option == "truncated":
                results += '</td><td style="padding:10px;">'.join(str(v) for v in temprow2)
            else:
                results += '</td><td style="padding:10px;">'.join(str(v) for v in temprow)

            results += '</td><tr><td>\n'

    writer.writerow(('\n'))
    return results

def pepdb_search_tsv_line2(writer, peptide, peptide_option, seqsim, matrix, extra, pid, function, species, category):
    #(peptide,peptide_option,pid,function,seqsim,matrix,extra,species,category)
    results = []
    extra_info = defaultdict(list)
    q = PeptideInfo.objects.all()

    if pid != "":
        try:
            protid_check = ProteinInfo.objects.get(pid__iexact=pid)
        except ProteinInfo.DoesNotExist:
            writer.writerow(["Protein ID "+pid+" does not exist in database."])
            results.append(peptide+"</td><td><h4>Protein ID "+pid+" does not exist in database.</h4>")
            return results

        q = PeptideInfo.objects.filter(protein=protid_check)

    if species != "":
        # if species is "cow" or "pig" etc., then also search for scientific names

        spec_list=[]
        for l in settings.TRANSLATE_LIST:
            if species.lower() in l:
                spec_list = list(l)

        if spec_list:
            q_obj = Q(species__iexact = spec_list[0])
            for s in spec_list[1:]:
                q_obj = q_obj | Q(species__iexact = s)
                #print str(q_obj)

            proteins = ProteinInfo.objects.filter(q_obj)
            protein_ids = [proobj.id for proobj in proteins]
            tempids = PeptideInfo.objects.filter(protein__in=protein_ids)
            search_ids = [pepobj.id for pepobj in tempids]
            q = q.filter(id__in=search_ids)
        else:
            q = q.filter(protein__species__icontains=species)

    if category != "":
        q = q.filter(category__icontains=category)

    if peptide != "":
        if peptide_option == "sequence":
            if (len(peptide) < 4 or (seqsim == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__iexact=peptide)
            else:
                data = run_blastp(q,peptide,matrix)
                search_ids=[]
                for row in data:
                    #use longer sequence for similarity calculation
                    tlen = float(row['slen']) if float(row['slen']) > float(row['qlen']) else float(row['qlen'])
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / tlen)
                    if simcalc >= seqsim:
                        search_ids.append(row['subject'])
                        extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]
                
                q = q.filter(id__in=search_ids)

        elif peptide_option == "truncated":
            if (len(peptide) < 4 or (seqsim == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__icontains=peptide)
            else:
                data = run_blastp(q,peptide,matrix)
                search_ids=[]
                for row in data:
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / float(row['qlen']))
                    if simcalc >= seqsim:
                        search_ids.append(row['subject'])
                        extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

                q = q.filter(id__in=search_ids)

        elif peptide_option == "precursor":
            search_ids=[]
            # select * from peptide_peptideinfo where 'LLFFVAPLL' LIKE '%' || peptide_peptideinfo.peptide || '%';
            tempids = PeptideInfo.objects.raw("select id from peptide_peptideinfo where %s LIKE '%%' || peptide_peptideinfo.peptide || '%%'", [peptide]);
            search_ids = [pepobj.id for pepobj in tempids]

            data = run_blastp(q,peptide,matrix)
            for row in data:
                simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / float(row['qlen']))
                if (simcalc >= seqsim and int(row['qlen']) > int(row['slen'])):
                    search_ids.append(row['subject'])
                    extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

            q = q.filter(id__in=search_ids)


    if function != "":
        q = q.filter(functions__function__icontains=function)

    if (q.count() == 0):
        writer.writerow([peptide,"No records found for this peptide."])
        results.append(peptide+"</td><td><h4>No records found for search.</h4>")
        return results
        #raise subprocess.CalledProcessError(1, cmd="", output="No records found for search. Protein: '"+protein+"', Peptide: '"+peptide+"', query: "+str(q.query))

    for info in q:

        if function != "":
            fcheck = Function.objects.filter(pep=info, function__icontains=function)
        else:
            fcheck = Function.objects.filter(pep=info)

        for func in fcheck:

            temprow2=[]
            pp = info.protein.pid
            pd = info.protein.desc
            if info.protein_variants:
                pp = pp + " Genetic Variant " + info.protein_variants
                pd = pd + " Genetic Variant " + info.protein_variants
            temprow = [peptide,pp,info.peptide,info.category,pd,info.protein.species,info.intervals]
            if peptide_option == "truncated":
                temprow2 = [peptide,pp,info.peptide.replace(peptide,"<b>"+peptide+"</b>"),info.category,pd,info.protein.species,info.intervals]

            refs = Reference.objects.filter(func=func)
            titles=[]
            authors=[]
            abstracts=[]
            dois=[]
            sf=[]
            ptms=[]
            titnum=1

            for ref in refs:
                if ref.title != '': titles.append("("+str(titnum)+") "+ref.title+". ")
                if ref.secondary_func != '': sf.append("("+str(titnum)+") "+ref.secondary_func+". ")
                if ref.ptm != '': ptms.append("("+str(titnum)+") "+ref.ptm+". ")
                titnum+=1
                if ref.authors != '': authors.append(ref.authors)
                if ref.abstract != '': abstracts.append(ref.abstract)
                dois.append(ref.doi)

            temprow.extend((func.function,', '.join(sf),', '.join(ptms),', '.join(titles),', '.join(authors),', '.join(abstracts),', '.join(dois)))
            if peptide_option == "truncated":
                temprow2.extend((func.function,', '.join(sf),', '.join(ptms),', '.join(titles),', '.join(authors),', '.join(abstracts),', '.join(dois)))
                
            if extra:
                if str(info.id) in extra_info:
                    temprow.extend(extra_info[str(info.id)])
                    if peptide_option == "truncated":
                        temprow2.extend(extra_info[str(info.id)])
                else:
                    temprow.extend((u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t'))
                    if peptide_option == "truncated":
                        temprow2.extend((u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t',u'\t'))

            writer.writerow(temprow)

            if peptide_option == "truncated":
                results.append('</td><td style="padding:10px; max-width:300px; word-wrap:break-word;">'.join(str(v) for v in temprow2))
            else:
                results.append('</td><td style="padding:10px; max-width:300px; word-wrap:break-word;">'.join(str(v) for v in temprow))

    return results


def pepdb_multi_search2(peptidefile,peptide_option,pid,function,seqsim,matrix,extra,species,category):
    results = []
    messages = []

    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_pep_path = os.path.join(work_path, peptidefile.name).replace(' ','_')
    handle_uploaded_file(peptidefile,input_pep_path)

    subprocess.check_output(['dos2unix','-q',input_pep_path], stderr=subprocess.STDOUT)

    csv.register_dialect('tsv', delimiter='\t', quoting=csv.QUOTE_NONE, escapechar=' ')
    output_path = os.path.join(work_path, "MBPDB_search_%s.tsv"%time.strftime('%Y-%m-%d_%H.%M.%S',time.localtime()))
    out = open(output_path, 'w', encoding='utf-8')
    writer = csv.writer(out, delimiter='\t')

    if extra:
        writer.writerow (('search peptide','proteinID','peptide','category','protein description','species','intervals','function','secondary function','ptm','title','authors','abstract','doi','% alignment','query start','query end','subject start','subject end','e-value','alignment length','mismatches','gap opens'))
        results.append('<tr><th style="padding:10px;">search peptide</th><th style="padding:10px;">proteinID</th><th style="padding:10px;" width="200px">peptide</th><th style="padding:10px;">category</th><th style="padding:10px;">protein description</th><th style="padding:10px;">species</th><th style="padding:10px;">intervals</th><th style="padding:10px;">function</th><th style="padding:10px;">secondary function</th><th style="padding:10px;">ptm</th><th style="padding:10px;">title</th><th style="padding:10px;">authors</th><th style="padding:10px;">abstract</th><th style="padding:10px;">doi</th><th>% alignment</th><th style="padding:10px;">query start</th><th style="padding:10px;">query end</th><th style="padding:10px;">subject start</th><th style="padding:10px;">subject end</th><th style="padding:10px;">e-value</th><th style="padding:10px;">alignment length</th><th style="padding:10px;">mismatches</th><th style="padding:10px;">gap opens</th></tr><tr><td>')
    else:
        writer.writerow (('search peptide','proteinID','peptide','category','protein description','species','intervals','function','secondary function','ptm','title','authors','abstract','doi'))
        results.append('<tr><th style="padding:10px;">search peptide</th><th style="padding:10px;">proteinID</th><th style="padding:10px;" width="200px">peptide</th><th style="padding:10px;">category</th><th style="padding:10px;">protein description</th><th style="padding:10px;">species</th><th style="padding:10px;">intervals</th><th style="padding:10px;">function</th><th style="padding:10px;">secondary function</th><th style="padding:10px;">ptm</th><th style="padding:10px;">title</th><th style="padding:10px;">authors</th><th style="padding:10px;">abstract</th><th style="padding:10px;">doi</th></tr><tr><td>')

        with open(input_pep_path, 'r') as pepfile:
            for pep in iter(pepfile):
                pep = pep.rstrip('\n')
                results.extend(pepdb_search_tsv_line2(writer, pep, peptide_option, seqsim, matrix, extra, pid, function, species, category))

    return results,output_path


def pepdb_multi_search(tsv_file):
    results = ''
    messages = []
    csv.register_dialect('pep_dialect', delimiter='\t')

    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_tsv_path = os.path.join(work_path, tsv_file.name).replace(' ','_')
    handle_uploaded_file(tsv_file,input_tsv_path)

    # remove weird characters from end of fields
    temp_file = os.path.join(work_path, "temp.csv")
    subprocess.check_output(['dos2unix','-q',input_tsv_path], stderr=subprocess.STDOUT)
    subprocess.check_output([settings.FIX_WEIRD_CHARS,input_tsv_path,temp_file], stderr=subprocess.STDOUT)
    subprocess.check_output(['mv',temp_file,input_tsv_path], stderr=subprocess.STDOUT)

    # detecting file encoding
    detector = UniversalDetector()
    for line in open(input_tsv_path, 'rb'):
        detector.feed(line)
        if detector.done: break
    detector.close()

    # if file is not UTF-8, attempt to recode to UTF-8
    if detector.result['encoding'] != "UTF-8":
        subprocess.check_output(['recode',detector.result['encoding']+'..UTF-8',input_tsv_path], stderr=subprocess.STDOUT)

    csv.register_dialect('tsv', delimiter='\t', quoting=csv.QUOTE_NONE)
    output_path = os.path.join(work_path, "MBPDB_multi_search_%s.tsv"%time.strftime('%Y-%m-%d_%H.%M.%S',time.localtime()))
    out = open(output_path, 'w', encoding='utf-8')
    writer = csv.writer(out, delimiter='\t')

    try:
        err=0
        rownum=1
        with open(input_tsv_path, 'r', encoding='utf-8') as pepfile:
            data = csv.DictReader(pepfile, dialect='pep_dialect')
            headers = list(data.fieldnames)
            headers = list(filter(None, headers)) # remove empty column headers
            headers.sort()

            # check if headers are correct
            if headers != ['category', 'extra_output', 'function', 'peptide', 'protein_id', 'scoring_matrix', 'search_type', 'similarity_threshold', 'species']:
                raise subprocess.CalledProcessError(1, cmd="", output="Error: Input file does not have the correct headers (peptide, search_type, similarity_threshold, scoring_matrix, extra_output, protein_id, function, species, and category).")

            err=0
            for row in data:
                rownum = rownum + 1
                search_type = row['search_type'].lower()
                matrix = row['scoring_matrix'].upper()
                extra = row['extra_output'].lower()

                if (row['peptide']!='' and (row['search_type']=='' or row['similarity_threshold']=='' or row['scoring_matrix']=='' or row['extra_output']=='')):
                    messages.append("Error: Line "+str(rownum)+" in file has values that cannot be empty (if peptide has a value, then so must search_type, similarity_threshold, scoring_matrix, and extra_output).")
                    err+=1

                if row['peptide']!='':
                    if search_type not in ['sequence','truncated','precursor']:
                        messages.append("Error: Line "+str(rownum)+". Search type must be either 'sequence', 'truncated', or 'precursor'.")
                        err+=1

                    try:
                        threshold = float(row['similarity_threshold'])
                    except ValueError:
                        messages.append("Error: Line "+str(rownum)+". Similarity Threshold must be a number.")
                        err+=1

                    if threshold <= 0 or threshold > 100:
                        messages.append("Error: Line "+str(rownum)+". Similarity Threshold must be greater than 0 and less than or equal to 100.")
                        err+=1

                    if matrix not in ['BLOSUM62','IDENTITY']:
                        messages.append("Error: Line "+str(rownum)+". Scoring matrix must be either 'blosum62' or 'identity'.")
                        err+=1

                    if extra not in ['yes','no']:
                        messages.append("Error: Line "+str(rownum)+". Extra Output must be either 'yes' or 'no'.")
                        err+=1


            if err > 0:
                raise subprocess.CalledProcessError(1, cmd="", output='<br/>'.join(messages))
            else:
                csv.register_dialect('tsv', delimiter='\t', quoting=csv.QUOTE_NONE)
                output_path = os.path.join(work_path, "MBPDB_multi_search_%s.tsv"%time.strftime('%Y-%m-%d_%H.%M.%S',time.localtime()))
                out = open(output_path, 'w', encoding='utf-8')
                writer = csv.writer(out, delimiter='\t', escapechar=' ')

                with open(input_tsv_path, 'r', encoding='utf-8') as pepfile2:
                    data = csv.DictReader(pepfile2, dialect='pep_dialect')
                    for row in data:
                        search_type = row['search_type'].lower()
                        matrix = row['scoring_matrix'].upper()
                        extra = row['extra_output'].lower()

                        results += "<br/><h3>Search parameters: peptide: "+row['peptide']+", search_type: "+search_type+", similarity_threshold: "+str(threshold)+", scoring_matrix: "+matrix+", extra_output: "+extra+", protein_id: "+row['protein_id']+", function: "+row['function']+", species: "+row['species']+", category: "+row['category']+"</h3><table border=\"1\">"
                        writer.writerow(["Search parameters: peptide: "+row['peptide']+", search_type: "+search_type+", similarity_threshold: "+str(threshold)+", scoring_matrix: "+matrix+", extra_output: "+extra+", protein_id: "+row['protein_id']+", function: "+row['function']+", species: "+row['species']+", category: "+row['category']])
                        results += pepdb_search_tsv_line(writer, row['peptide'], search_type, threshold, matrix, 0 if extra in ["no",""] else 1, row['protein_id'], row['function'], row['species'], row['category'])
                        results += "</td></tr></table><br/>\n"

    except UnicodeDecodeError:
        raise subprocess.CalledProcessError(1, cmd="", output="Error: File needs to use Unicode (UTF-8) encoding. Conversion failed.")

    return results,output_path


def pepdb_search(peptide,peptide_option,pid,function,seqsim,matrix,extra,species,category):
    results = []
    extra_info = defaultdict(list)
    q = PeptideInfo.objects.all()

    if pid != "":
        try:
            protid_check = ProteinInfo.objects.get(pid__iexact=pid)
        except ProteinInfo.DoesNotExist:
            raise subprocess.CalledProcessError(1, cmd="", output="Protein ID "+pid+" does not exist in database.")

        q = PeptideInfo.objects.filter(protein=protid_check)

    if species != "":
        # if species is "cow" or "pig" etc., then also search for scientific names
        spec_list=[]
        for l in settings.TRANSLATE_LIST:
            if species.lower() in l:
                spec_list = list(l)

        if spec_list:
            q_obj = Q(species__iexact = spec_list[0])
            for s in spec_list[1:]:
                q_obj = q_obj | Q(species__iexact = s)
                #print str(q_obj)

            proteins = ProteinInfo.objects.filter(q_obj)
            protein_ids = [proobj.id for proobj in proteins]
            tempids = PeptideInfo.objects.filter(protein__in=protein_ids)
            search_ids = [pepobj.id for pepobj in tempids]
            q = q.filter(id__in=search_ids)
        else:
            q = q.filter(protein__species__icontains=species)

    if category != "":
        q = q.filter(category__icontains=category)

    if peptide != "":
        if peptide_option == "sequence":
            if (len(peptide) < 4 or (seqsim == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__iexact=peptide)
            else:
                data = run_blastp(q,peptide,matrix)
                search_ids=[]
                for row in data:
                    #choose the longer of the two seqs to calculate similarity
                    tlen = float(row['slen']) if float(row['slen']) > float(row['qlen']) else float(row['qlen'])
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / tlen)
                    if simcalc >= seqsim:
                        search_ids.append(row['subject'])
                        extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]
                
                q = q.filter(id__in=search_ids)

        elif peptide_option == "truncated":
            if (len(peptide) < 4 or (seqsim == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__icontains=peptide)
            else:
                data = run_blastp(q,peptide,matrix)
                search_ids=[]
                for row in data:
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / float(row['qlen']))
                    if simcalc >= seqsim:
                        search_ids.append(row['subject'])
                        extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

                q = q.filter(id__in=search_ids)

        elif peptide_option == "precursor":
            search_ids=[]
            # select * from peptide_peptideinfo where 'LLFFVAPLL' LIKE '%' || peptide_peptideinfo.peptide || '%';
            tempids = PeptideInfo.objects.raw("select id from peptide_peptideinfo where %s LIKE '%%' || peptide_peptideinfo.peptide || '%%'", [peptide]);
            search_ids = [pepobj.id for pepobj in tempids]

            data = run_blastp(q,peptide,matrix)
            for row in data:
                simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / float(row['qlen']))
                if (simcalc >= seqsim and int(row['qlen']) > int(row['slen'])):
                    search_ids.append(row['subject'])
                    extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

            q = q.filter(id__in=search_ids)


    if function != "":
        q = q.filter(functions__function__icontains=function)

    if (q.count() == 0):
        raise subprocess.CalledProcessError(1, cmd="", output="No records found for search.")
        #raise subprocess.CalledProcessError(1, cmd="", output="No records found for search. Protein: '"+protein+"', Peptide: '"+peptide+"', query: "+str(q.query))

    csv.register_dialect('tsv', delimiter='\t', quoting=csv.QUOTE_NONE, escapechar=' ')
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    output_path = os.path.join(work_path, "MBPDB_search_%s.tsv"%time.strftime('%Y-%m-%d_%H.%M.%S',time.localtime()))

    out = open(output_path, 'w', encoding='utf-8')
    writer = csv.writer(out, delimiter='\t')
    if extra:
        writer.writerow (('proteinID','peptide','category','protein description','species','intervals','function','secondary function','ptm','title','authors','abstract','doi','% alignment','query start','query end','subject start','subject end','e-value','alignment length','mismatches','gap opens'))
        results.append('<tr><td style="padding:10px;">{row_data["proteinID"]}</td><td style="padding:10px;" width="200px">{row_data["peptide"]}</td><td style="padding:10px;">{row_data["category"]}</td><td style="padding:10px;">{row_data["protein description"]}</td><td style="padding:10px;">{row_data["species"]}</td><td style="padding:10px;">{row_data["intervals"]}</td><td style="padding:10px;">{row_data["function"]}</td><td style="padding:10px;">{row_data["secondary function"]}</td><td style="padding:10px;">{row_data["ptm"]}</td><td style="padding:10px;">{row_data["title"]}</td><td style="padding:10px;">{row_data["authors"]}</td><td style="padding:10px;">{row_data["abstract"]}</td><td style="padding:10px;">{row_data["doi"]}</td><td style="padding:10px;">{row_data["% alignment"]}</td><td style="padding:10px;">{row_data["query start"]}</td><td style="padding:10px;">{row_data["query end"]}</td><td style="padding:10px;">{row_data["subject start"]}</td><td style="padding:10px;">{row_data["subject end"]}</td><td style="padding:10px;">{row_data["e-value"]}</td><td style="padding:10px;">{row_data["alignment length"]}</td><td style="padding:10px;">{row_data["mismatches"]}</td><td style="padding:10px;">{row_data["gap opens"]}</td></tr>')
    else:
        writer.writerow (('proteinID','peptide','category','protein description','species','intervals','function','secondary function','ptm','title','authors','abstract','doi'))
        results.append('<tr><th style="padding:10px;">proteinID</th><th style="padding:10px;" width="200px">peptide</th><th style="padding:10px;">category</th><th style="padding:10px;">protein description</th><th style="padding:10px;">species</th><th style="padding:10px;">intervals</th><th style="padding:10px;">function</th><th style="padding:10px;">secondary function</th><th style="padding:10px;">ptm</th><th style="padding:10px;">title</th><th style="padding:10px;">authors</th><th style="padding:10px;">abstract</th><th style="padding:10px;">doi</th></tr><tr><td>')
    for info in q:

        if function != "":
            fcheck = Function.objects.filter(pep=info, function__icontains=function)
        else:
            fcheck = Function.objects.filter(pep=info)

        for func in fcheck:

            temprow2=[]
            pp = info.protein.pid
            pd = info.protein.desc
            if info.protein_variants:
                pp = pp + " Genetic Variant " + info.protein_variants
                pd = pd + " Genetic Variant " + info.protein_variants
            temprow = [pp,info.peptide,info.category,pd,info.protein.species,info.intervals]
            if peptide_option == "truncated":
                temprow2 = [pp,info.peptide.replace(peptide,"<b>"+peptide+"</b>"),info.category,pd,info.protein.species,info.intervals]

            refs = Reference.objects.filter(func=func)
            titles=[]
            authors=[]
            abstracts=[]
            dois=[]
            sf=[]
            ptms=[]
            titnum=1
        
            for ref in refs:
                if ref.title != '': titles.append("("+str(titnum)+") "+ref.title+". ")
                if ref.secondary_func != '': sf.append("("+str(titnum)+") "+ref.secondary_func+". ")
                if ref.ptm != '': ptms.append("("+str(titnum)+") "+ref.ptm+". ")
                titnum+=1
                if ref.authors != '': authors.append(ref.authors)
                if ref.abstract != '': abstracts.append(ref.abstract)
                dois.append(ref.doi)


            temprow.extend((func.function,', '.join(sf),', '.join(ptms),', '.join(titles),', '.join(authors),', '.join(abstracts),', '.join(dois)))
            if peptide_option == "truncated":
                temprow2.extend((func.function,', '.join(sf),', '.join(ptms),', '.join(titles),', '.join(authors),', '.join(abstracts),', '.join(dois)))
                
            if extra:
                if str(info.id) in extra_info:
                    temprow.extend(extra_info[str(info.id)])
                    if peptide_option == "truncated":
                        temprow2.extend(extra_info[str(info.id)])
                else:
                    temprow.extend(('\t','\t','\t','\t','\t','\t','\t','\t','\t','\t'))
                    if peptide_option == "truncated":
                        temprow2.extend(('\t','\t','\t','\t','\t','\t','\t','\t','\t','\t'))

            writer.writerow(temprow)

            if peptide_option == "truncated":
                results.append('</td><td style="padding:10px; max-width:300px; word-wrap:break-word;">'.join(str(v) for v in temprow2))
            else:
                results.append('</td><td style="padding:10px; max-width:300px; word-wrap:break-word;">'.join(str(v) for v in temprow))
        
    return results,output_path


def get_latest_peptides(n):
    dictlist = [dict() for x in range(n)]
    q = PeptideInfo.objects.all().order_by('-id')[0:n]

    i=0
    for pep in q:
        f = Function.objects.filter(pep=pep)
        func_str = ', '.join([func.function for func in f])
        dictlist[i] = {'time_approved':pep.time_approved, 'peptide':pep.peptide, 'pid':pep.protein.pid, 'functions':func_str}
        i+=1

    return dictlist

def remove_domains(input_xmls,remove_all_mods):
    zip_dir = 'remove_domains_%s'%time.strftime('%Y-%m-%d_%H.%M.%S',time.localtime())
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    zip_path = os.path.join(work_path, zip_dir)
    os.mkdir(zip_path)
    input_xml_paths = []
    for input_xml in input_xmls:
        path = os.path.join(zip_path, input_xml.name).replace(' ','_')
        handle_uploaded_file(input_xml,path)
        input_xml_paths.append(path)
    subprocess.check_output([settings.REMOVE_DOMAINS, remove_all_mods]+input_xml_paths,stderr=subprocess.STDOUT)
    os.chdir(work_path)
    xml_outfiles = glob(zip_dir+"/*.domains_removed.xtan.xml")
    output_path = zip_path + ".zip"
    subprocess.check_output(["zip", output_path] + xml_outfiles, stderr=subprocess.STDOUT)
    return output_path


def run_pepex(input_tsv,count_pep):
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_tsv_path = os.path.join(work_path, input_tsv.name).replace(' ','_')
    handle_uploaded_file(input_tsv,input_tsv_path)
    output_path = os.path.join(work_path, "pepex_output_%s.txt"%time.strftime('%Y-%m-%d_%H.%M.%S',time.localtime()))

    # run pepex
    ret = subprocess.check_output([settings.PEPEX, settings.FASTA_FILES_DIR, input_tsv_path, output_path, count_pep], stderr=subprocess.STDOUT)
    if (ret != ""):
        raise subprocess.CalledProcessError(1, cmd=settings.PEPEX, output=ret)

    return output_path

def add_proteins(input_fasta_files, messages):
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    count=0
    for input_fasta_file in input_fasta_files:
        path = os.path.join(work_path, input_fasta_file.name).replace(' ','_')
        handle_uploaded_file(input_fasta_file,path)

        fd = open(path, "rU")
        try:
            for seq_record in SeqIO.parse(fd, "fasta"):
                m = re.search(".+?\|(.+?)\|.+?\s+(.+?)\s+OS=(.+?)\s+(GN|PE)", seq_record.description)
                if not m:
                    messages.append("Warning: Header '"+seq_record.description+"' not parseable. Skipping fasta record.")
                    continue
                protid = m.group(1)
                prot_desc = m.group(2)
                prot_species = m.group(3)

                gvid=''
                gv = re.search("GV=(.+?)\s*$", seq_record.description)
                if gv:
                    gvid = gv.group(1)

                try:
                    idcheck = ProteinInfo.objects.get(pid=protid)
                except ProteinInfo.DoesNotExist:
                    if not gvid:
                        protinfo = ProteinInfo(header=seq_record.description, pid=protid, seq=seq_record.seq, desc=prot_desc, species=prot_species)
                        protinfo.save()
                        count = count + 1

                    else:
                        messages.append("Error: Protein ID "+protid+" not found for variant "+gvid+". You must first add the original protein before adding variants.")
                        continue

                if gvid:
                    gv_check = ProteinVariant.objects.filter(protein=idcheck,pvid=gvid)
                    if gv_check.count() > 0:
                        messages.append("Variant "+gvid+" already exists for protein "+protid+". Skipping.")
                        continue

                    else:
                        pv = ProteinVariant(seq=seq_record.seq, pvid=gvid, protein=idcheck)
                        pv.save()
                        count = count + 1

                else:
                    messages.append("Protein ID "+protid+" already exists (and sequence is not variant). Skipping.")
                    continue

        except AttributeError as e:
            messages.append("Warning: "+input_fasta_file.name+" is an invalid fasta file. Skipping. Error: "+str(sys.exc_info()[0])+", "+str(e)+", "+seq_record.id)
            fd.close()
            continue

        fd.close()

    #create fasta file
    fasta_path = os.path.join(settings.FASTA_FILES_DIR, "protein_database.fasta")
    fd = open(fasta_path, "w")
    for prot_record in ProteinInfo.objects.all():
        fd.write(">"+prot_record.header+"\n"+prot_record.seq+"\n")
    for pv in ProteinVariant.objects.all():
        fd.write(">"+pv.protein.header+" GV="+pv.pvid+"\n"+pv.seq+"\n")
    fd.close()

    messages.append(str(count)+" fasta record(s) added to database.")
    return messages

def blast_pipeline(peptide_library,peptide_input):
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    library_tsv_path = get_tsv_path(peptide_library,work_path)
    library_tsv_path = xlsx_to_tsv(library_tsv_path)
    input_tsv_path = get_tsv_path(peptide_input,work_path)
    output_path = os.path.join(work_path, 'homology_output_%s.tsv'%time.strftime('%Y-%m-%d_%H.%M.%S',time.localtime())).replace(' ','_')
    (library_ids_tsv_path,library_fasta_path) = create_fasta_lib(library_tsv_path)
    (input_ids_tsv_path,input_fasta_path) = create_fasta_input(input_tsv_path)
    make_blast_db(library_fasta_path)
    blast_output_path = os.path.join(work_path, 'pep_to_func.tsv')
    blastp(input_fasta_path,library_fasta_path, blast_output_path)
    combine(input_ids_tsv_path, library_ids_tsv_path, blast_output_path, output_path)
    return output_path

def xlsx_to_tsv(path):
    (root,ext) = os.path.splitext(path)
    tsv_path = root + '.tsv'
    print([settings.XLS_TO_TSV,path,tsv_path])
    #This is NOISY!  Ignore output.
    subprocess.call('%s "%s" "%s" 2> /dev/null' % (settings.XLS_TO_TSV,path,tsv_path),shell=True)
    return tsv_path

def create_fasta_lib(library_tsv_path):
    (root,ext) = os.path.splitext(library_tsv_path)
    with_ids_tsv_path = root + 'with_ids.tsv'
    with_ids_fasta_path = root + 'with_ids.fasta'
    subprocess.check_output([settings.CREATE_FASTA_LIB,library_tsv_path,with_ids_tsv_path,with_ids_fasta_path],stderr=subprocess.STDOUT)
    return (with_ids_tsv_path,with_ids_fasta_path)

def create_fasta_input(input_tsv_path):
    (root,ext) = os.path.splitext(input_tsv_path)
    with_ids_tsv_path = root + 'with_ids.tsv'
    with_ids_fasta_path = root + 'with_ids.fasta'
    subprocess.check_output([settings.CREATE_FASTA_INPUT,input_tsv_path,with_ids_tsv_path,with_ids_fasta_path],stderr=subprocess.STDOUT)
    return (with_ids_tsv_path,with_ids_fasta_path)

def make_blast_db(library_fasta_path):
    print(['makeblastdb','-in', library_fasta_path,'-dbtype','prot'])
    subprocess.check_output(['makeblastdb','-in', library_fasta_path,'-dbtype','prot'],stderr=subprocess.STDOUT)

def blastp(input_fasta_path,library_fasta_path, output_path):
    args = ['blastp', '-query', input_fasta_path, '-db', library_fasta_path, '-out', output_path, '-outfmt', '6 std qlen slen gaps', '-evalue', '0.1']
    subprocess.check_output(args,stderr=subprocess.STDOUT)

def combine(input_ids_tsv_path, library_ids_tsv_path, blast_output_path, output_path):
    subprocess.check_output([settings.COMBINE,input_ids_tsv_path, library_ids_tsv_path, blast_output_path, output_path],stderr=subprocess.STDOUT)
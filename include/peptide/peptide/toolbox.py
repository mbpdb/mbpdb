import subprocess, os
from django.conf import settings
import time
import csv
#from Bio import SeqIO
from .models import PeptideInfo, Reference, Function, ProteinInfo, Submission, ProteinVariant
import re, sys
from collections import defaultdict
from django.db.models import Q
from datetime import datetime
from django.contrib.auth.models import User
from chardet.universaldetector import UniversalDetector
from django.db.models import Count

#Creates temp folder /include/peptide/peptide/upload/temp for storage related to each unique search request
def create_work_directory(base_dir):
    path = os.path.join(base_dir,'work_%d'%int(round(time.time() * 1000)))
    os.makedirs(path)
    return path

#Opens and extracts uploaded file, generic function
def handle_uploaded_file(request_file, path):
    with open(path, 'wb') as destination:
        for chunk in request_file.chunks():
            destination.write(chunk)

#Generic function returns path of uploaded file
def get_tsv_path(request_file,directory_path=None):
    if directory_path is None:
        directory_path = settings.WORK_DIRECTORY
    path = os.path.join(directory_path, request_file.name).replace(' ','_')
    handle_uploaded_file(request_file,path)
    return path

#Uploads csv to sqsqlite3 database
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
            if headers != ['abstract', 'authors', 'doi', 'function', 'peptide', 'proteinID', 'ptm', 'secondary_function', 'title']:
                raise subprocess.CalledProcessError(1, cmd="", output="Error: Input file does not have the correct headers (proteinID, peptide, function, secondary_function, ptm, title, authors, abstract, and doi).")

            err=0
            for row in data:
                rownum = rownum + 1

                if (row['peptide']=='' or row['proteinID']=='' or row['function']=='' or row['title']=='' or row['authors']=='' or row['doi']==''):
                    messages.append("Error: Line "+str(rownum)+" in file has values that cannot be empty (only abstract, secondary function, and ptm can be empty).")
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

                        sub = Submission(protein_id=row['proteinID'], peptide=row['peptide'], function=row['function'], secondary_function=row['secondary_function'], ptm=row['ptm'], title=row['title'], authors=row['authors'], abstract=row['abstract'], doi=row['doi'], intervals=':'.join(interval_list), protein_variants=','.join(pvid_list), length=len(row['peptide']), time_submitted=tn)
                        sub.save()
                        count += 1

                    suq = User.objects.filter(is_superuser=1)
                    #email_subject = "New Peptide Submission %s" % time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
                    #send_mail(email_subject, 'There are '+str(count)+' new peptide submissions for the MBPDB.', 'New Peptides <'+settings.NOREPLY_EMAIL+'>',[e.email for e in suq])

                    if detector.result['encoding'].lower() != "utf-8":
                        messages.append("Warning: Detected encoding for input file was not UTF-8 (It was detected as "+detector.result['encoding']+"). Recoding was attempted but if this is not the correct original encoding, then non-standard characters may not have been recoded correctly.")
                    messages.append("No errors found. "+str(count)+" entries have been submitted for approval.")
            else:
                errbit = "errors" if err > 1 else "error"
                messages.append(str(err)+" "+errbit+" found. Please correct and resubmit the file.")

    except UnicodeDecodeError:
        raise subprocess.CalledProcessError(1, cmd="", output="Error: File needs to use Unicode (UTF-8) encoding. Conversion failed.")
    return messages

#Approved upload of data
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
            pepinfo = PeptideInfo(peptide=e.peptide, protein_variants=e.protein_variants, protein=idcheck, length=e.length, intervals=e.intervals, time_approved=tn)
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

#Primary function referenced in blast search when extra information is requested
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

#2nd function in toolbox data pipeline, handles the input from the pepdb_multi_search_fileupload function
#Return html styled results from  inputed TSV file (Advanced Search TSV file upload) and returns them to pepdb_multi_search_fileupload
def pepdb_search_tsv_line_fileupload(writer, peptide, peptide_option, thershold, matrix, extra, pid, function, species):
    #(peptide,peptide_option,pid,function,seqsim,matrix,extra,species)
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

            proteins = ProteinInfo.objects.filter(q_obj)
            protein_ids = [proobj.id for proobj in proteins]
            tempids = PeptideInfo.objects.filter(protein__in=protein_ids)
            search_ids = [pepobj.id for pepobj in tempids]
            q = q.filter(id__in=search_ids)
        else:
            q = q.filter(protein__species__icontains=species)


    if peptide != "":
        if peptide_option == "sequence":
            if (len(peptide) < 4 or (thershold == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__iexact=peptide)
            else:
                data = run_blastp(q,peptide,matrix)
                search_ids=[]
                for row in data:
                    tlen = float(row['slen']) if float(row['slen']) > float(row['qlen']) else float(row['qlen'])
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / tlen)
                    if simcalc >= thershold:
                        search_ids.append(row['subject'])
                        extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

                q = q.filter(id__in=search_ids)

        elif peptide_option == "truncated":
            if (len(peptide) < 4 or (thershold == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__icontains=peptide)
            else:
                data = run_blastp(q,peptide,matrix)
                search_ids=[]
                for row in data:
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / float(row['qlen']))
                    if simcalc >= thershold:
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
                if (simcalc >= thershold and int(row['qlen']) > int(row['slen'])):
                    search_ids.append(row['subject'])
                    extra_info[row['subject']] = [str(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

            q = q.filter(id__in=search_ids)


    if function != "":
        q = q.filter(functions__function__icontains=function)

    if (q.count() == 0):
        writer.writerow(["No records found for search."])
        results += "<h3>No records found for search.</h3>"
        return results

    if extra:
        writer.writerow (('proteinID','peptide','protein description','species','intervals','function','secondary function','ptm','title','authors','abstract','doi','% alignment','query start','query end','subject start','subject end','e-value','alignment length','mismatches','gap opens'))
        results += '<tr><th style="padding:10px;">proteinID</th><th style="padding:10px;" width="200px">peptide</th><th style="padding:10px;">protein description</th><th style="padding:10px;">species</th><th style="padding:10px;">intervals</th><th style="padding:10px;">function</th><th style="padding:10px;">secondary function</th><th style="padding:10px;">ptm</th><th style="padding:10px;">title</th><th style="padding:10px;">authors</th><th style="padding:10px;">abstract</th><th style="padding:10px;">doi</th><th>% alignment</th><th style="padding:10px;">query start</th><th style="padding:10px;">query end</th><th style="padding:10px;">subject start</th><th style="padding:10px;">subject end</th><th style="padding:10px;">e-value</th><th style="padding:10px;">alignment length</th><th style="padding:10px;">mismatches</th><th style="padding:10px;">gap opens</th></tr><tr><td>\n'
    else:
        writer.writerow (('proteinID','peptide','protein description','species','intervals','function','secondary function','ptm','title','authors','abstract','doi'))
        results += '<tr><th style="padding:10px;">proteinID</th><th style="padding:10px;" width="200px">peptide</th><th style="padding:10px;">protein description</th><th style="padding:10px;">species</th><th style="padding:10px;">intervals</th><th style="padding:10px;">function</th><th style="padding:10px;">secondary function</th><th style="padding:10px;">ptm</th><th style="padding:10px;">title</th><th style="padding:10px;">authors</th><th style="padding:10px;">abstract</th><th style="padding:10px;">doi</th></tr><tr><td>\n'


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
            temprow = [pp,info.peptide,pd,info.protein.species,info.intervals]
            if peptide_option == "truncated":
                temprow2 = [pp,info.peptide.replace(peptide,"<b>"+peptide+"</b>"),pd,info.protein.species,info.intervals]

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

#2nd function in toolbox data pipeline, handles the input from the pepdb_multi_search_manual
#Returns list of string results form inputed peptide list (manual inputs)
def pepdb_search_tsv_line_manual(writer, peptide, peptide_option, seqsim, matrix, extra, pid, function, species):
    #(peptide,peptide_option,pid,function,seqsim,matrix,extra,species)
    results = []
    extra_info = defaultdict(list)
    q = PeptideInfo.objects.all()

    if pid:
        try:
            # Fetch ProteinInfo objects that match any of the provided PIDs
            protid_check = ProteinInfo.objects.filter(pid__in=pid)

            # If none found, write an error
            if not protid_check.exists():
                writer.writerow(["Protein ID " + ', '.join(pid) + " does not exist in database."])
                results.append(
                    peptide + "</td><td><h4>Protein ID " + ', '.join(pid) + " does not exist in database.</h4>")
                return results

            # Fetch primary keys of these ProteinInfo objects
            protein_ids = protid_check.values_list('id', flat=True)

            # Filter PeptideInfo objects based on these protein IDs
            q = PeptideInfo.objects.filter(protein__id__in=protein_ids)

        except Exception as e:  # General exception handler for unexpected issues
            writer.writerow([str(e)])
            results.append(peptide + "</td><td><h4>Error: " + str(e) + "</h4>")
            return results

    if species:
        # Initialize the final list of search IDs
        final_search_ids = []

        # Loop through each species in the list
        for spec in species:
            spec_list = []
            for l in settings.TRANSLATE_LIST:
                if spec.lower() in l:
                    spec_list = list(l)
                    break  # break once the species is found

            search_ids = []
            if spec_list:
                q_obj = Q(species__iexact=spec_list[0])
                for s in spec_list[1:]:
                    q_obj = q_obj | Q(species__iexact=s)

                proteins = ProteinInfo.objects.filter(q_obj)
                protein_ids = [proobj.id for proobj in proteins]
                tempids = PeptideInfo.objects.filter(protein__in=protein_ids)
                search_ids = [pepobj.id for pepobj in tempids]
            else:
                q = q.filter(protein__species__in=spec)
                search_ids = [pepobj.id for pepobj in q]

            # Append the search IDs from this iteration to the final list
            final_search_ids.extend(search_ids)

        # Filter the query using the final list of search IDs
        q = q.filter(id__in=final_search_ids)


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


    if function:
        q = q.filter(functions__function__in=function)
    if (q.count() == 0):
        writer.writerow([peptide,"No records found for this peptide."])
        results.append(peptide+"</td><td><h4>No records found for search.</h4>")
        return results

    for info in q:
        if function:
            fcheck = Function.objects.filter(pep=info, function__in=function)
        else:
            fcheck = Function.objects.filter(pep=info)

        for func in fcheck:

            temprow2=[]
            pp = info.protein.pid
            pd = info.protein.desc
            if info.protein_variants:
                pp = pp + " Genetic Variant " + info.protein_variants
                pd = pd + " Genetic Variant " + info.protein_variants
            temprow = [peptide,pp,info.peptide,pd,info.protein.species,info.intervals]
            if peptide_option == "truncated":
                temprow2 = [peptide,pp,info.peptide.replace(peptide,"<b>"+peptide+"</b>"),pd,info.protein.species,info.intervals]

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
                
            if extra and seqsim != 100: #or matrix=="IDENTITY" perhaps this should be added given orginal code
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

#1st function in toolbox data pipeline when manual data input from peptide_search (views.py, peptide_search.htm)
#major updates rk 8/8/23 from pepfile.txt and returns them to pepdb_multi_search_manual
#creates tsv in uploads/temp folder
def pepdb_multi_search_manual(pepfile_path, peptide_option, pid, function, seqsim, matrix, extra, species):
    results = []
    messages = []
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_pep_path = pepfile_path
    subprocess.check_output(['dos2unix', '-q', input_pep_path], stderr=subprocess.STDOUT)

    csv.register_dialect('tsv', delimiter='\t', quoting=csv.QUOTE_NONE, escapechar=' ')
    output_path = os.path.join(work_path, "MBPDB_search_%s.tsv" % time.strftime('%Y-%m-%d_%H.%M.%S', time.localtime()))
    out = open(output_path, 'w', encoding='utf-8')
    writer = csv.writer(out, delimiter='\t')
    if extra and seqsim != 100:#or matrix=="IDENTITY" perhaps this should be added given orginal code
        writer.writerow(('search peptide', 'proteinID', 'peptide', 'protein description', 'species',
                         'intervals', 'function', 'secondary function', 'ptm', 'title', 'authors', 'abstract', 'doi',
                         '% alignment', 'query start', 'query end', 'subject start', 'subject end', 'e-value',
                         'alignment length', 'mismatches', 'gap opens'))
        results.append(
            '<tr><th style="padding:10px;">search peptide</th><th style="padding:10px;">proteinID</th><th style="padding:10px;" width="200px">peptide</th><th style="padding:10px;">protein description</th><th style="padding:10px;">species</th><th style="padding:10px;">intervals</th><th style="padding:10px;">function</th><th style="padding:10px;">secondary function</th><th style="padding:10px;">ptm</th><th style="padding:10px;">title</th><th style="padding:10px;">authors</th><th style="padding:10px;">abstract</th><th style="padding:10px;">doi</th><th>% alignment</th><th style="padding:10px;">query start</th><th style="padding:10px;">query end</th><th style="padding:10px;">subject start</th><th style="padding:10px;">subject end</th><th style="padding:10px;">e-value</th><th style="padding:10px;">alignment length</th><th style="padding:10px;">mismatches</th><th style="padding:10px;">gap opens</th></tr><tr><td>')
    else:
        writer.writerow(('search peptide', 'proteinID', 'peptide', 'protein description', 'species',
                         'intervals', 'function', 'secondary function', 'ptm', 'title', 'authors', 'abstract', 'doi'))
        results.append(
            '<tr><th style="padding:10px;">search peptide</th><th style="padding:10px;">proteinID</th><th style="padding:10px;" width="200px">peptide</th><th style="padding:10px;">protein description</th><th style="padding:10px;">species</th><th style="padding:10px;">intervals</th><th style="padding:10px;">function</th><th style="padding:10px;">secondary function</th><th style="padding:10px;">ptm</th><th style="padding:10px;">title</th><th style="padding:10px;">authors</th><th style="padding:10px;">abstract</th><th style="padding:10px;">doi</th></tr><tr><td>')

    with open(input_pep_path, 'r') as pepfile:
        content = pepfile.read().strip()

    if not content:  # This will be True for both truly empty files and files with just whitespace or ""

        results.extend(
            pepdb_search_tsv_line_manual(writer, "", peptide_option, seqsim, matrix, extra, pid, function, species))
    else:
        for pep in content.splitlines():
            results.extend(
                pepdb_search_tsv_line_manual(writer, pep, peptide_option, seqsim, matrix, extra, pid, function, species,))
    return results,output_path

#1st function in toolbox data pipeline when TSV from peptide_search (views.py peptide_search.html advanced search is uploaded)
#creates tsv in uploads/temp folder
#Handles when TSV from advanced search is uploaded from peptide_search.html -> views.py peptide_search
def pepdb_multi_search_fileupload(tsv_file):
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
            if headers != ['function', 'peptide', 'protein_id', 'scoring_matrix', 'search_type', 'similarity_threshold', 'species']:
                raise subprocess.CalledProcessError(1, cmd="", output="Error: Input file does not have the correct headers (peptide, search_type, similarity_threshold, scoring_matrix, extra_output, protein_id, function, species).")

            err=0
            for row in data:
                row = {key: value.strip() for key, value in row.items()}
                rownum = rownum + 1
                search_type = row['search_type'].lower().strip()
                matrix = row['scoring_matrix'].upper().strip()
                if (row['peptide']!='' and (row['search_type']=='' or row['similarity_threshold']=='' or row['scoring_matrix']=='')):
                    messages.append("Error: Line "+str(rownum)+" in file has values that cannot be empty (if peptide has a value, then so must search_type, similarity_threshold, and scoring_matrix).")
                    err+=1

                if row['peptide']!='':
                    if search_type not in ['sequence','truncated','precursor']:
                        messages.append("Error: Line "+str(rownum)+". Search type must be either 'sequence', 'truncated', or 'precursor'.")
                        err+=1

                    try:
                        seqsim = float(row['similarity_threshold']) #replaced threshold with seqim to be consistent      RK 8/11/23
                    except ValueError:
                        messages.append("Error: Line "+str(rownum)+". Similarity Threshold must be a number.")
                        err+=1

                    if seqsim <= 0 or seqsim > 100:
                        messages.append("Error: Line "+str(rownum)+". Similarity Threshold must be greater than 0 and less than or equal to 100.")
                        err+=1

                    if matrix not in ['BLOSUM62','IDENTITY']:
                        messages.append("Error: Line "+str(rownum)+". Scoring matrix must be either 'blosum62' or 'identity'.")
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
                        row = {key: value.strip() for key, value in row.items()}
                        search_type = row['search_type'].lower()
                        matrix = row['scoring_matrix'].upper()
                        #added 8/22/23 RK to remove extra_info if 100% or '' similarity is searched also if peptide is < 4 AA
                        if row['similarity_threshold'] != '100' and row['similarity_threshold'] != '' and len(row['peptide']) >= 4:
                            extra = 1
                        else:
                            extra = 0
                        # Create a list to hold the individual pieces of the string to write to file or export to website
                        params_list = []

                        if row['peptide']:
                            params_list.append(" peptide: " + row['peptide'] + ",")
                        if search_type:
                            params_list.append(" search_type: " + search_type + ",")
                        if row['similarity_threshold'] != '':
                            params_list.append(" similarity_threshold: " + str(row['similarity_threshold']) + ",")
                        if matrix:
                            params_list.append(" scoring_matrix: " + matrix + ",")
                        if row['protein_id']:
                            params_list.append(" protein_id: " + row['protein_id'] + ",")
                        if row['function']:
                            params_list.append(" function: " + row['function'] + ",")
                        if row['species']:
                            params_list.append(" species: " + row['species'])

                        # Concatenate the list into a single string
                        params_str = "".join(params_list)
                        # Remove the trailing comma if it exists
                        if params_str[-1] == ',':
                            params_str = params_str[:-1]

                        #writes to file export using params_str
                        writer.writerow([f'Search parameters:\t{params_str}'])
                        #writer.writerow(["Search parameters: peptide: "+row['peptide']+", search_type: "+search_type+", similarity_threshold: "+str(row['similarity_threshold'])+", scoring_matrix: "+matrix+", protein_id: "+row['protein_id']+", function: "+row['function']+", species: "+row['species']])

                        #writes to website using params_str
                        results += "<br/><h3>" "Search parameters: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" + params_str + "</h3><table border=\"1\">"

                        results += pepdb_search_tsv_line_fileupload(writer, row['peptide'], search_type, float(row['similarity_threshold']) if row['similarity_threshold'].strip() != '' else None, matrix, extra, row['protein_id'], row['function'], row['species']) # replace if statement that handled no or yes for extra to simplily 1
                        results += "</td></tr></table><br/>\n"
    except UnicodeDecodeError:
        raise subprocess.CalledProcessError(1, cmd="", output="Error: File needs to use Unicode (UTF-8) encoding. Conversion failed.")

    return results,output_path

#returns date of most recently added peptide, updated on 8/8/23 to only return date
def get_latest_peptides(n):
    dictlist = [dict() for x in range(n)]
    q = PeptideInfo.objects.all().order_by('-id')[0:n]

    i=0
    for pep in q:
        f = Function.objects.filter(pep=pep)
        func_str = ', '.join([func.function for func in f])
        date_approved = pep.time_approved.date() if pep.time_approved else None
        dictlist[i] = {'time_approved': date_approved}
        i+=1

    return dictlist

#Primary function referenced in blast search when extra information is requested
def run_pepex(input_tsv, count_pep):
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_tsv_path = os.path.join(work_path, input_tsv.name).replace(' ','_')
    handle_uploaded_file(input_tsv,input_tsv_path)
    output_path = os.path.join(work_path, "pepex_output_%s.txt"%time.strftime('%Y-%m-%d_%H.%M.%S',time.localtime()))

    # run pepex
    command = [settings.PEPEX, settings.FASTA_FILES_DIR, input_tsv_path, output_path, count_pep]
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        # The command failed. Raise an exception with the output and error message.
        raise subprocess.CalledProcessError(result.returncode, cmd=command, output=result.stdout, stderr=result.stderr)

    # The command succeeded. Return the output path.
    return output_path

#adds proteins to database, Only used by site admin not user
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

#Secondary function used in the blast search when extra infor is requested
def xlsx_to_tsv(path):
    (root,ext) = os.path.splitext(path)
    tsv_path = root + '.tsv'
    #This is NOISY!  Ignore output.
    subprocess.call('%s "%s" "%s" 2> /dev/null' % (settings.XLS_TO_TSV,path,tsv_path),shell=True)
    return tsv_path

#Secondary function used in the blast search when extra infor is requested
def create_fasta_lib(library_tsv_path):
    (root,ext) = os.path.splitext(library_tsv_path)
    with_ids_tsv_path = root + 'with_ids.tsv'
    with_ids_fasta_path = root + 'with_ids.fasta'
    subprocess.check_output([settings.CREATE_FASTA_LIB,library_tsv_path,with_ids_tsv_path,with_ids_fasta_path],stderr=subprocess.STDOUT)
    return (with_ids_tsv_path,with_ids_fasta_path)

#Secondary function used in the blast search when extra infor is requested
def create_fasta_input(input_tsv_path):
    (root,ext) = os.path.splitext(input_tsv_path)
    with_ids_tsv_path = root + 'with_ids.tsv'
    with_ids_fasta_path = root + 'with_ids.fasta'
    subprocess.check_output([settings.CREATE_FASTA_INPUT,input_tsv_path,with_ids_tsv_path,with_ids_fasta_path],stderr=subprocess.STDOUT)
    return (with_ids_tsv_path,with_ids_fasta_path)

#Secondary function used in the blast search when extra infor is requested
def make_blast_db(library_fasta_path):
    subprocess.check_output(['makeblastdb','-in', library_fasta_path,'-dbtype','prot'],stderr=subprocess.STDOUT)

#Secondary function used in the blast search when extra infor is requested
def blastp(input_fasta_path,library_fasta_path, output_path):
    args = ['blastp', '-query', input_fasta_path, '-db', library_fasta_path, '-out', output_path, '-outfmt', '6 std qlen slen gaps', '-evalue', '0.1']
    subprocess.check_output(args,stderr=subprocess.STDOUT)

#Secondary function used in the blast search when extra infor is requested
def combine(input_ids_tsv_path, library_ids_tsv_path, blast_output_path, output_path):
    subprocess.check_output([settings.COMBINE,input_ids_tsv_path, library_ids_tsv_path, blast_output_path, output_path],stderr=subprocess.STDOUT)

#pulls a list of pids and descriptors from the database to popluate the search dropdown list
def pro_list(request):
    # Fetching protein IDs that are referenced in PeptideInfo
    protein_ids_linked_to_peptides = PeptideInfo.objects.values_list('protein_id', flat=True).distinct()

    # Fetching protein descriptions and PIDs for the proteins linked to peptides
    proteins = ProteinInfo.objects.filter(id__in=protein_ids_linked_to_peptides).values('desc', 'pid')

    # Using Python to group by 'desc' and aggregate PIDs
    description_to_pid = {}
    for protein in proteins:
        if protein['desc'] in description_to_pid:
            description_to_pid[protein['desc']].append(protein['pid'])
        else:
            description_to_pid[protein['desc']] = [protein['pid']]
    return description_to_pid

#pulls a list of functions from the database to popluate the search dropdown list
def func_list(request):
    # Aggregating and ordering the functions based on their occurrence
    functions = Function.objects.values('function').annotate(count=Count('function')).order_by('-count')

    # Extracting only the unique functions in descending order of their occurrence
    unique_func = [func['function'] for func in functions]
    return unique_func

#Added RK 8/22/23 returns list of species to the html page from settings.translatelist
def spec_list(request):
    common_to_sci = {}
    for entry in settings.TRANSLATE_LIST:
        common_name, sci_name = entry
        if common_name in common_to_sci:
            common_to_sci[common_name].append(sci_name)
        else:
            common_to_sci[common_name] = [sci_name]

    return common_to_sci

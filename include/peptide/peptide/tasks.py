# tasks.py
from django.shortcuts import render
import os, re, sys, csv
from .toolbox import blastp, make_blast_db,create_work_directory, func_list, clear_temp_directory, spec_list, pro_list, run_pepex, add_proteins, pepdb_add_csv, get_latest_peptides, append_with_titnum

import subprocess
from subprocess import CalledProcessError
from .models import PeptideInfo, Reference, Function, ProteinInfo, Submission, ProteinVariant
from django.utils import timezone
from django.http import FileResponse, HttpResponse, JsonResponse
from django.conf import settings

from celery import shared_task
from django.core.cache import cache
import time

from collections import defaultdict
from django.db.models import Q
from datetime import datetime
from django.contrib.auth.models import User
from chardet.universaldetector import UniversalDetector
from django.db.models import Count
from django.http import HttpResponse
import shutil
from Bio import SeqIO


#2nd function in toolbox data pipeline, handles the input from the pepdb_multi_search_manual
#major updates rk 8/8/24 incoperated into celery tasks
#Returns list of string results form inputed peptide list (manual inputs)
def pepdb_search_tsv_line_manual(writer, q, peptide, peptide_option, seqsim, matrix, extra, pid, function, species, no_pep, results_headers):
    results = []
    extra_info = defaultdict(list)
    if peptide != "":
        if "sequence" in peptide_option:
            if (len(peptide) < 4 or (seqsim == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__iexact=peptide)
            else:
                data = run_blastp(peptide, matrix)

                search_ids=[]
                for row in data:
                    #use longer sequence for similarity calculation
                    tlen = float(row['slen']) if float(row['slen']) > float(row['qlen']) else float(row['qlen'])
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / tlen)
                    if simcalc >= seqsim:
                        search_ids.append(row['subject'])
                        extra_info[row['subject']] = ["{:.2f}".format(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

                q = q.filter(id__in=search_ids)

        elif "truncated" in peptide_option:
            if (len(peptide) < 4 or (seqsim == 100 and matrix=="IDENTITY")):
                q = q.filter(peptide__icontains=peptide)
            else:
                data = run_blastp(peptide,matrix)
                search_ids=[]
                for row in data:
                    simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / float(row['qlen']))
                    if simcalc >= seqsim:
                        search_ids.append(row['subject'])
                        extra_info[row['subject']] = ["{:.2f}".format(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

                q = q.filter(id__in=search_ids)

        elif "precursor" in peptide_option:
            search_ids=[]
            # select * from peptide_peptideinfo where 'LLFFVAPLL' LIKE '%' || peptide_peptideinfo.peptide || '%';
            tempids = PeptideInfo.objects.raw("select id from peptide_peptideinfo where %s LIKE '%%' || peptide_peptideinfo.peptide || '%%'", [peptide]);
            search_ids = [pepobj.id for pepobj in tempids]

            data = run_blastp(peptide,matrix)
            for row in data:
                simcalc = 100 * ((float(row['numpos']) - float(row['gaps'])) / float(row['qlen']))
                if (simcalc >= seqsim and int(row['qlen']) > int(row['slen'])):
                    search_ids.append(row['subject'])
                    extra_info[row['subject']] = ["{:.2f}".format(simcalc),row['qstart'],row['qend'],row['sstart'],row['send'],row['evalue'],row['align_len'],row['mismatches'],row['gaps']]

            q = q.filter(id__in=search_ids)

    if (q.count() == 0):
        peptide_db_list = list(PeptideInfo.objects.values_list('peptide', flat=True))
        if peptide in peptide_db_list:
            #results.append("<h4>WARNING: Peptide: " + ''.join(peptide) + " does not meet other search critera.</h4>")
            results.append("<h4>Peptide: " + ''.join(peptide) + " does not meet other search critera.</h4>")
            writer.writerow(["Peptide: " + ''.join(peptide) + " does not meet other search critera."])
            return results
        else:
            #results.append("<h4>WARNING: Peptide: " + ''.join(peptide) + " does not exist in database.</h4>")
            results.append("<h4>Peptide: " + ''.join(peptide) + " does not exist in database.</h4>")
            writer.writerow(["Peptide: " + ''.join(peptide) + "  does not exist in database."])
            return results

    for info in q:
        if function:
            # Filters peptides mapped to function
            fcheck = Function.objects.filter(pep=info, function__in=function)
        else:
            fcheck = Function.objects.filter(pep=info)

        for func in fcheck:
            pp = info.protein.pid
            pd = info.protein.desc
            if info.protein_variants:
                pp = pp + " Genetic Variant " + info.protein_variants
                pd = pd + " Genetic Variant " + info.protein_variants
            refs = Reference.objects.filter(func=func)
            titles=[]
            authors=[]
            abstracts=[]
            dois=[]
            ad=[]
            ic=[]
            it=[]
            im=[]
            ptms=[]
            titnum=1

            for ref in refs:
                if ref.title != '':
                    append_with_titnum(titles, ref.title, titnum)
                if ref.additional_details != '':
                    append_with_titnum(ad, ref.additional_details, titnum)
                if ref.ic50 != '' and ref.ic50 is not None:
                    append_with_titnum(ic, str(ref.ic50), titnum)
                if ref.inhibition_type != '':
                    append_with_titnum(it, ref.inhibition_type, titnum)
                if ref.inhibited_microorganisms != '':
                    append_with_titnum(im, ref.inhibited_microorganisms, titnum)
                if ref.ptm != '':
                    append_with_titnum(ptms, ref.ptm, titnum)
                if ref.authors != '':
                    append_with_titnum(authors, ref.authors, titnum)
                if ref.abstract != '':
                    append_with_titnum(abstracts, ref.abstract, titnum)
                if ref.doi != '':
                    append_with_titnum(dois, ref.doi, titnum)
                titnum += 1
                #if ref.authors != '': authors.append(ref.authors)
                #if ref.abstract != '': abstracts.append(ref.abstract)
                #dois.append(ref.doi)
            # Determine the initial_peptide string based on whether "truncated" is in peptide_option
            initial_peptide = info.peptide.replace(peptide,"<b>" + peptide + "</b>") if "truncated" in peptide_option else info.peptide

            # Create two different rows for web display and file writing
            temprow = ([peptide] if not no_pep else []) + [pp, initial_peptide, pd, info.protein.species,
                                                               info.intervals]

            # Common fields that will be extended to both rows
            common_fields = [
                func.function,
                ',<br>'.join(ad),
                ',<br>'.join(ic),
                ',<br>'.join(it),
                ',<br>'.join(im),
                ',<br>'.join(ptms),
                ',<br>'.join(titles),
                ',<br>'.join(authors),
                ',<br>'.join(abstracts),
                ',<br>'.join(dois)
            ]

            # Extend temprow with common_fields
            temprow.extend(common_fields)

              # Add peptide_option to temprowif no_pep is False
            if not no_pep:
                temprow.append(peptide_option)
                temprow.append(matrix)

            # Extend temprowwith extra_info if conditions are met
            if extra and seqsim != 100:  # or matrix == "IDENTITY" perhaps this should be added given original code
                if str(info.id) in extra_info:
                    temprow.extend(extra_info[str(info.id)])
                else:
                    temprow.extend([u'\t'] * 9)  # Add nine tab characters
            #removes none from ic50
            temprow = ['' if x == 'None' else x for x in temprow]

            # Iterate through common_fields to replace <br> with \n for file_temprow
            file_temprow = []
            for field in temprow:
                if isinstance(field, str):
                    clean_field = field.replace('<br>', '\n').replace('<b>', '').replace('</b>', '')
                elif isinstance(field, list):
                    # Convert list to string (e.g., by joining its elements with a space)
                    clean_field = ' '.join(field).replace('<br>', '\n').replace('<b>', '').replace('</b>', '')
                else:
                    # For other types, you can decide how you want to handle them
                    clean_field = str(field)
                file_temprow.append(clean_field)
            # Write the row to the file (using the version without HTML tags)
            writer.writerow(file_temprow)
            # Append the results for web display using a dictionary
            results.append(dict(zip(results_headers, temprow)))
    return results

#1st function in toolbox data pipeline when manual data input from peptide_search (views.py, peptide_search.htm)
#major updates rk 8/8/23 from pepfile.txt and returns them to
#major updates rk 8/8/24 incoperated into celery tasks

#creates tsv in uploads/temp folder
@shared_task(bind=True)
def pepdb_multi_search_manual(self, pepfile_path, peptide_option, pid, function, seqsim, matrix, extra, species, no_pep):
    results = []
    messages = []
    formated_header = ''
    results_headers = []
    common_csv_headers_file = []
    #Creates blast_db
    global fasta_db_path
    fasta_db_path = os.path.join(settings.BLAST_DB, "db.fasta")

    q = PeptideInfo.objects.all()

    pep_list = []
    peptide_option_list = []
    matrix_list = []
    q_pid = q_func = q_spec = None

    if pid:
        pid_search_ids = []
        for protein in pid:
            protid_check = ProteinInfo.objects.filter(pid__in=[protein])

            # Fetch primary keys of these ProteinInfo objects
            protein_ids = protid_check.values_list('id', flat=True)

            # Fetch PeptideInfo objects based on these protein IDs
            tempids = PeptideInfo.objects.filter(protein__id__in=protein_ids)
            search_ids = [pepobj.id for pepobj in tempids]

            # Append the search IDs from this iteration to the final list
            pid_search_ids.extend(search_ids)

        # Filter PeptideInfo objects based on the final list of search IDs
        if pid_search_ids:
            q_pid = PeptideInfo.objects.filter(id__in=pid_search_ids)

    if species:
        spec_search_ids = []

        for spec in species:
            for l in settings.SPEC_TRANSLATE_LIST:
                if spec.lower() in l:
                    spec_latin = (l[1])
                    q_obj = Q(species__iexact=spec_latin)

                    proteins = ProteinInfo.objects.filter(q_obj)
                    protein_ids = [proobj.id for proobj in proteins]
                    tempids = PeptideInfo.objects.filter(protein__in=protein_ids)
                    search_ids = [pepobj.id for pepobj in tempids]
                    # Append the search IDs from this iteration to the final list
                    spec_search_ids.extend(search_ids)

        # Filter the query using the final list of search IDs
        if spec_search_ids:
            q_spec = q.filter(id__in=spec_search_ids)

    if function:
        q_func = q.filter(functions__function__in=function)

    with open(fasta_db_path, 'w') as fasta_db_file:
        # Combine and filter q_func, q_pid, q_spec
        if q_pid or q_func or q_spec:
            combined_query = Q()
            filters_applied = False
            if q_pid:
                combined_query &= Q(id__in=q_pid.values_list('id', flat=True))
                filters_applied = True

            if q_func:
                combined_query &= Q(id__in=q_func.values_list('id', flat=True))
                filters_applied = True

            if q_spec:
                combined_query &= Q(id__in=q_spec.values_list('id', flat=True))
                filters_applied = True


            # Apply the combined filter only if it's not empty
            if filters_applied:
                q = q.filter(combined_query)

            # Check if no_pep is 0 and the combined_query is effectively empty
            if no_pep == 0 and not filters_applied:
                q = PeptideInfo.objects.none()
                fasta_db_file.write(f">{10**10}\n{'YPFPG'}\n")
            else:
                for info in q:
                    fasta_db_file.write(f">{info.id}\n{info.peptide}\n")
        else:
            q = PeptideInfo.objects.all()
            for info in q:
                fasta_db_file.write(f">{info.id}\n{info.peptide}\n")
    cache.set(f'q{self.request.id}', q)
    #print(f'q{self.request.id} = {q}')
    fasta_db_file.close()
    if q.exists():
        make_blast_db(fasta_db_path)

    # Check if WORK_DIRECTORY exists and is writable
    global work_path
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_pep_path = pepfile_path
    subprocess.check_output(['dos2unix', '-q', input_pep_path], stderr=subprocess.STDOUT)

    csv.register_dialect('tsv', delimiter='\t', quoting=csv.QUOTE_NONE, escapechar=' ')
    output_path = os.path.join(work_path, "MBPDB_search_%s.tsv" % time.strftime('%Y-%m-%d_%H.%M.%S', time.localtime()))
    out = open(output_path, 'w', encoding='utf-8')
    writer = csv.writer(out, delimiter='\t')

    # Create a variable for common CSV headers
    common_csv_headers = ('Search&nbsppeptide',
                          'Protein&nbspID',
                          'Peptide&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp',
                          'Protein&nbspdescription',
                          'Species&nbsp&nbsp&nbsp&nbsp',
                          'Intervals',
                          'Function&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp',
                          'Additional&nbspdetails',
                          'IC50&nbsp(μM)&nbsp&nbsp&nbsp&nbsp',
                          'Inhibition&nbsptype',
                          'Inhibited&nbspmicroorganisms',
                          'PTM',
                          "Title&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp",#107 whiteshapce characters
                          "Authors&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp", #35 characters
                          "Abstract&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp", #107 whiteshapce characters
                          'DOI&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp',
                          'Search type',
                          'Scoring matrix')

    # Create a variable for extra CSV headers related to BLAST output
    blast_output_headers = ('% Alignment', 'Query start', 'Query end', 'Subject start', 'Subject end', 'e-value',
                            'Alignment length', 'Mismatches', 'Gap opens')
    if no_pep:
        common_csv_headers = tuple(header for header in common_csv_headers if header not in {'Search&nbsppeptide', 'Search type', 'Scoring matrix'})


    with open(input_pep_path, 'r') as pepfile:
        content = pepfile.read().strip()

    # for celery progress
    start_time = time.time()
    cont_size = len(content.splitlines())  # Split the content into lines and store it in a variable
    cache.set(f'size_{self.request.id}', cont_size)
    #(f'size_{self.request.id} = {cont_size}')
    for header in common_csv_headers:
        # Replace &nbsp when it's between two characters (word or non-word) with a space.
        header = re.sub(r'(?<=[\w\W])&nbsp(?=[\w\W])', ' ', header)
        # Replace &nbsp when it's not surrounded by characters with nothing.
        cleaned_header = re.sub(r'&nbsp', '', header)
        # Strip leading and trailing whitespace
        cleaned_header = cleaned_header.strip()
        common_csv_headers_file.append(cleaned_header)

    if extra and seqsim != 100:
        writer.writerow(list(common_csv_headers_file) + list(blast_output_headers))
        #results.append('<tr>{}{}</tr><tr><td>'.format(common_table_headers_str, blast_output_table_headers_str))
        results_headers.extend(list(common_csv_headers) + list(blast_output_headers))
        #results.append(common_csv_headers, blast_output_headers)
    else:
        writer.writerow(common_csv_headers_file)
        #results.append(common_csv_headers)
        results_headers.extend(common_csv_headers)


    #("content",content)
    if cont_size < 1:  # This will be True for both truly empty files and files with just whitespace or ""
        cache.set(f'progress_{self.request.id}', 1)
        elapsed_time = time.time() - start_time
        cache.set(f'elapsed_time_{self.request.id}', elapsed_time)  # Elapsed time in seconds
        cache.set(f'status_{self.request.id}', 'complete')
        #print(f'size_{self.request.id} = {cont_size}, Cache set: progress_{self.request.id} = {1}, elapsed_time_{self.request.id} = {elapsed_time}')
        results.extend(pepdb_search_tsv_line_manual(writer, q, "", peptide_option, seqsim, matrix, extra, pid, function, species, no_pep, results_headers))
    else:
        for i, cont in enumerate(content.splitlines(), start=1):
            elapsed_time = time.time() - start_time
            # Update progress in cache without timeout
            cache.set(f'progress_{self.request.id}', i)
            cache.set(f'elapsed_time_{self.request.id}', elapsed_time)  # Elapsed time in seconds

            #print(f'size_{self.request.id} = {cont_size}, Cache set: progress_{self.request.id} = {i}, elapsed_time_{self.request.id} = {elapsed_time}')


            # Split the cont string into pep and peptide_option
            pep, peptide_option, matrix = cont.split(' ', 2)
            results.extend(pepdb_search_tsv_line_manual(writer, q, pep, peptide_option, seqsim, matrix, extra, pid, function, species,no_pep, results_headers))
        cache.set(f'status_{self.request.id}', 'complete')

    params_list = []
    for cont in content.splitlines():
        # Split the cont string into pep and peptide_option
        pep, peptide_option, matrix = cont.split(' ', 2)
        pep_list.append(pep)
        peptide_option_list.append((peptide_option))
        matrix_list.append(matrix)
        pep_list=list(set(pep_list))
        peptide_option_list=list(set(peptide_option_list))
        matrix_list=list(set(matrix_list))

    if (peptide_option_list != ['sequence'] and peptide_option_list != []) or seqsim != 100 or ( matrix_list != ['IDENTITY'] and matrix_list != []):
        params_list.append(f"<b>Search type:</b> {', '.join(peptide_option_list)},")
        params_list.append(f"<b>Similarity threshold:</b> {seqsim}%,")
        params_list.append(f"<b>Scoring matrix:</b> {', '.join(matrix_list)},")

    if pid:
        params_list.append(f"<b>Protein ID:</b> {', '.join(pid)},")
    if function:
        params_list.append(f"<b>Function:</b> {', '.join(function)},")
    if species:
        params_list.append(f"<b>Species:</b> {', '.join(species)}")
    if params_list:
        last_item = params_list[-1]
        if last_item.endswith(','):
            params_list[-1] = last_item[:-1]
    # Join the list with a tab character between each item
    params_str_tab = "\t".join(params_list)
    # Write to file export using params_str_tab
    # Replace it with the following to remove HTML tags
    cleaned_params_str_tab = re.sub('<.*?>', '', params_str_tab)
    if(len(params_list) >= 1):
        writer.writerow([f'#Advanced search parameters:\t{cleaned_params_str_tab}'])
        params_str_web = "</br>".join(params_list)
        formated_header = ("<h2><u>Advanced search parameters:</u> </br></h2><h4>"+params_str_web+"</h4>")
    #return results,formated_header,output_path,results_headers
    task_result = {
        'results': results,
        'formated_header': formated_header,
        'output_path': output_path,
        'results_headers': results_headers,
    }
    return task_result

#Primary function referenced in blast search when extra information is requested
def run_blastp(peptide, matrix):
    #work_path = create_work_directory(settings.WORK_DIRECTORY)
    query_path = os.path.join(work_path, "query.fasta")
    #fasta_db_path = os.path.join(work_path, "db.fasta")
    query_file = open(query_path, "w")
    query_file.write(">pep_query\n"+peptide+"\n")
    query_file.close()
    output_path = os.path.join(work_path, "blastp_short.out")

    #make_blast_db(fasta_db_path)

    subprocess.check_output(["blastp","-query",query_path,"-db",fasta_db_path,"-outfmt","6 std ppos qcovs qlen slen positive","-evalue","1000","-word_size","2","-matrix",matrix,"-threshold","1","-task","blastp-short","-out",output_path], stderr=subprocess.STDOUT)

    csv.register_dialect('blast_dialect', delimiter='\t')
    output_file = open(output_path, "r")
    data = csv.DictReader(output_file, fieldnames=['query','subject','percid','align_len','mismatches','gaps','qstart','qend','sstart','send','evalue','bitscore','ppos','qcov','qlen','slen','numpos'], dialect='blast_dialect')

    return data

"""
def long_running_task(self):
    start_time = time.time()
    for i in range(360):  # Simulating a task that runs in 60 steps
        time.sleep(1)  # Simulate a delay for each step
        elapsed_time = time.time() - start_time
        # Update progress in cache without timeout
        cache.set(f'progress_{self.request.id}', i)
        cache.set(f'elapsed_time_{self.request.id}', elapsed_time)  # Elapsed time in seconds
        print(f'Cache set: progress_{self.request.id} = {i}, elapsed_time_{self.request.id} = {elapsed_time}')
    # Set task complete status
    cache.set(f'status_{self.request.id}', 'complete')
    print(f'status_{self.request.id}','Cache set: progress_{self.request.id}, elapsed_time_{self.request.id}')

    return 'Task complete'

"""
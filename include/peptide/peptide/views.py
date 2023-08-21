from django.shortcuts import render
import os, re
from .toolbox import run_pepex, add_proteins, pepdb_add_csv, pepdb_multi_search, pepdb_multi_search2, get_latest_peptides #,peptide_db_call, contact_us
from django.http.response import HttpResponse
import subprocess
from subprocess import CalledProcessError
from .models import Counter
from datetime import datetime
from django.http import FileResponse
from django.conf import settings

#Unmodified
def index(request):
    context = {}
    return render(request, 'peptide/index.html', context)

"""  Old code, no need to submit single peptide
#Unmodified
def peptide_db(request):
    errors = []
    messages = ''
    if request.method == 'POST':
        if len(errors) == 0:
            pep = request.POST['pep']
            category = request.POST['category']
            protid = request.POST['protid']
            function = request.POST['function']
            secondary_func = request.POST['secondary_func']
            ptm = request.POST['ptm']
            title = request.POST['title']
            authors = request.POST['authors']
            abstract = request.POST['abstract']
            doi = request.POST['doi']
            
            try:
                messages = peptide_db_call(pep, category, protid, function, secondary_func, ptm, title, authors, abstract, doi)
            except CalledProcessError as e:
                return render(request, 'peptide/peptide_db.html', {'errors':[e.output]})
    return render(request, 'peptide/peptide_db.html', {'errors':errors, 'messages':messages})
"""

#Unmodified, function is used to add csv file of peptides to sqlite db  needs updating as message function is Deprecated
def peptide_db_csv(request):
    print("activat")
    errors = []
    messages = []
    if request.method == 'POST':
        if not request.FILES.get('csv_file',False):
            errors.append('File fields are mandatory.')
        if len(errors) == 0:
            try:
                messages = pepdb_add_csv(request.FILES['csv_file'],messages)
            except CalledProcessError as e:
                return render(request, 'peptide/peptide_db_csv.html', {'errors':[e.output]})
    return render(request, 'peptide/peptide_db_csv.html', {'errors':errors, 'messages':messages})


#Updated rk 8/8/23 handles the search from peptide_search.html, handles both tsv upload and manual peptide search
def peptide_search(request):
    errors = []
    results = []
    output_path = ''
    q = get_latest_peptides(1)
    tsv_submitted = bool(request.FILES.get('tsv_file'))


    if request.method == 'POST':
        counter = Counter(ip=request.META['REMOTE_ADDR'], access_time=datetime.now(), page='peptide search')
        counter.save()

        peptides = request.POST.get('peptides', '').splitlines()
        peptide_option = request.POST['peptide_option']
        pid = request.POST['proteinid']
        function = request.POST['function']
        seqsim = int(request.POST['seqsim'])
        matrix = request.POST['matrix']
        extra = 1 if request.POST.get('extra_output') else 0
        species = request.POST['species']
        category = request.POST['category']
        manual_input_provided = peptides or pid or function or species or category
        if not request.FILES.get('tsv_file',False):

            # Save peptides to a file named pepfile.txt
            pepfile_path = os.path.join(settings.MEDIA_ROOT, "pepfile.txt")
            with open(os.path.join(settings.MEDIA_ROOT, "pepfile.txt"), "w") as pepfile:
                if len(peptides) == 0:
                    pepfile.write("")
                else:
                    for peptide in peptides:
                        pepfile.write(peptide + "\n")

            if not peptides and pid == "" and function == "" and species == "" and category == "" and not request.FILES.get('tsv_file', False):
                errors.append("Error: You must input at least search critera or upload a file under Advanced Search Options.")
            try:
                (results,output_path) = pepdb_multi_search2(pepfile_path,peptide_option,pid,function,seqsim,matrix,extra,species,category)
                FileResponse(open(output_path, 'rb'))
            except CalledProcessError as e:
                return render(request, 'peptide/peptide_search.html', {'errors':[e.output], 'data':request.POST})
        else:
            # If both manual input and tsv file are provided, append an error message
            if manual_input_provided:
                errors.append(
                    f'Error: Please <a href=".">reset search criteria</a>.<br/><br/>Either manually enter peptides, search by Function, Protein ID, Species, Catagory or upload a file under Advanced Search Options.<br/><br/>Both manual inputs and advanced search file uploads can\'t be selected when performing a search.')
            try:
                (results, output_path) = pepdb_multi_search(request.FILES['tsv_file'])
                FileResponse(open(output_path, 'rb'))
            except CalledProcessError as e:
                return render(request, 'peptide/peptide_search.html', {'errors': [e.output]})
    return render(request, 'peptide/peptide_search.html', {'errors':errors, 'results':results, 'output_path':output_path, 'data':request.POST, 'latest_peptides':q, 'file_submitted': tsv_submitted})

#unmodified but needs updating as message function is Deprecated
def add_proteins_tool(request):
    errors = []
    messages = []
    if request.method == 'POST':
        if not request.FILES.get('input_fasta_files',False):
            errors.append('File fields are mandatory.')
        if len(errors) == 0:
            try:
                messages = add_proteins(request.FILES.getlist('input_fasta_files'), messages)
            except CalledProcessError as e:
                return render(request, 'peptide/add_proteins.html', {'errors':[e.output]})
    return render(request, 'peptide/add_proteins.html', {'errors':errors, 'messages':messages})

#Unmodified referenced by pepex tool
def pepex_tool(request):
    errors = []
    if request.method == 'POST':
        if not request.FILES.get('input_tsv',False):
            errors.append('The file field is mandatory.')
        if len(errors) == 0:
            count_pep = "1" if request.POST.get('count_pep') else "0"
            try:
                output_path = run_pepex(request.FILES['input_tsv'], count_pep)
                if not os.path.isfile(output_path):
                    errors.append('run_pepex did not return a valid file path.')
            except CalledProcessError as e:
                return render(request, 'peptide/pepex.html', {'errors': e.output.decode('utf-8').rstrip('\n').split('\n')})
            if len(errors) == 0:
                return FileResponse(open(output_path, 'rb'), as_attachment=True)
    return render(request, 'peptide/pepex.html', {'errors':errors})

#Unmodified returns a list of all proteins in protein fasta file
def protein_headers(request):
    ret = subprocess.check_output("grep -h '>' "+settings.FASTA_FILES_DIR+"/* | sort -u", shell=True, stderr=subprocess.STDOUT)
    ret = ret.decode('utf-8')
    ret = ret.replace('\n', '<br />')
    return HttpResponse(ret)

#Updated rk 8/8/23 returns downloadable file to user
def tsv_search_results(request):
    file_path = request.path.replace("/tsv_search_results/", "")
    if re.match("^" + settings.WORK_DIRECTORY + ".+/MBPDB.+\.tsv$", file_path):
        response = FileResponse(open(file_path, 'rb'))
        return response

#Added RK 8/9/23 returns about us page
def about_us(request):
    return render(request, 'peptide/about_us.html')


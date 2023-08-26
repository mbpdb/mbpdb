from django.shortcuts import render
import os, re
from .toolbox import func_list, spec_list, pro_list, run_pepex, add_proteins, pepdb_add_csv, pepdb_multi_search_fileupload, pepdb_multi_search_manual, get_latest_peptides
from django.http.response import HttpResponse
import subprocess
from subprocess import CalledProcessError
from .models import Counter
from django.utils import timezone
from django.http import FileResponse
from django.conf import settings

#Unmodified
def index(request):
    context = {}
    return render(request, 'peptide/index.html', context)

#Unmodified, function is used to add csv file of peptides to sqlite db  needs updating as message function is Deprecated
def peptide_db_csv(request):
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
    results_header=[]
    results = []
    peptide_option = []
    multi_peptide_option = []
    output_path = ''
    q = get_latest_peptides(1)
    description_to_pid = pro_list(request)
    unique_func = func_list(request)
    common_to_sci = spec_list(request)
    tsv_submitted = bool(request.FILES.get('tsv_file'))

    if request.method == 'POST':
        counter = Counter(ip=request.META['REMOTE_ADDR'], access_time=timezone.now(), page='peptide search')
        counter.save()

        peptides = [line.strip() for line in request.POST.get('peptides', '').splitlines()]
        peptide_option = request.POST.getlist('peptide_option')
        pid = [x.strip() for x in request.POST.get('proteinid', '').split(',')] if request.POST.get('proteinid','').strip() else []
        function = [x.strip() for x in request.POST.get('function', '').split(',')] if request.POST.get('function','').strip() else []
        species = [x.strip() for x in request.POST.get('species', '').split(',')] if request.POST.get('species','').strip() else []
        seqsim = int(request.POST['seqsim'])
        matrix = request.POST['matrix']
        multi_peptide_option = len(peptide_option) > 1
        for peptide in peptides:
            if not peptide.isalpha():
                errors.append("Error: Invalid input. Only text characters are allowed. Ensure there are no emtpy lines.")
            if len(peptide) >= 4:
                extra = 1
            else:
                extra = 0
        if not peptides:
               extra = 0
        if not request.FILES.get('tsv_file',False):
            # Save peptides to a file named pepfile.txt
            pepfile_path = os.path.join(settings.MEDIA_ROOT, "pepfile.txt")
            with open(os.path.join(settings.MEDIA_ROOT, "pepfile.txt"), "w") as pepfile:
                if len(peptides) == 0:
                    pepfile.write("")
                    no_pep = 1
                else:
                    for peptide in peptides:
                        for po in peptide_option:
                            # Check if both peptide and po are not empty
                            if peptide.strip() and po.strip():
                                pepfile.write(peptide + ' ' + po + "\n")
                            else:
                                # Handle the error case here if needed, for example:
                                errors.append("Error: Both peptide and peptide option must be non-empty.")
                    no_pep = 0

            if not peptide_option and peptides:
                errors.append("Error: You select a search type (Sequence, Truncated, or precursor) and input at least one peptide.")
            if not (peptides or pid or function or species or tsv_submitted or peptide_option):
                errors.append("Error: You must input at least search critera or upload a file under Advanced Search Options.")
            if not (peptides or pid or function or species or tsv_submitted):
                errors.append("Error: You must input at least search critera or upload a file under Advanced Search Options.")
            if no_pep:
                peptide_option =[]
                matrix == ""
                seqsim == ""
            errors = set(errors)
            try:
                (results, results_header,output_path) = pepdb_multi_search_manual(pepfile_path,peptide_option,pid,function,seqsim,matrix,extra,species,no_pep)
                FileResponse(open(output_path, 'rb'))
            except CalledProcessError as e:
                return render(request, 'peptide/peptide_search.html', {'errors': [e.output], 'data':request.POST})
        else:
            # If both manual input and tsv file are provided, append an error message
            if peptides or pid or function or species:
                errors.append(
                    f'Error: Please <a href=".">reset search criteria</a>.<br/><br/>Either manually enter peptides, search by Function, Protein ID, Species, Catagory or upload a file under Advanced Search Options.<br/><br/>Both manual inputs and advanced search file uploads can\'t be selected when performing a search.')
            try:
                (results, output_path) = pepdb_multi_search_fileupload(request.FILES['tsv_file'])
                FileResponse(open(output_path, 'rb'))
            except CalledProcessError as e:
                 return render(request, 'peptide/peptide_search.html', {'errors': [e.output], 'data':request.POST})
    return render(request, 'peptide/peptide_search.html', {'errors':errors, 'results':results, 'output_path':output_path, 'data':request.POST, 'peptide_option': peptide_option, 'latest_peptides':q, 'description_to_pid': description_to_pid, 'functions': unique_func, 'common_to_sci_list': common_to_sci, 'file_submitted': tsv_submitted, 'multi_peptide_option': multi_peptide_option, 'results_header':results_header})

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
    q = get_latest_peptides(1)
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
    return render(request, 'peptide/pepex.html', {'errors':errors,'latest_peptides': q})

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
    q = get_latest_peptides(1)
    return render(request, 'peptide/about_us.html', {'latest_peptides': q})
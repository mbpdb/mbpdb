from django.shortcuts import render
import os, re
from .toolbox import blast_pipeline, run_pepex, add_proteins, peptide_db_call, pepdb_add_csv, pepdb_multi_search, pepdb_multi_search2, contact_us, get_latest_peptides
from django.http.response import HttpResponse
import subprocess
from subprocess import CalledProcessError
from .models import Counter
from datetime import datetime
from django.http import FileResponse
from django.conf import settings

def index(request):
    context = {}
    return render(request, 'peptide/index.html', context)

def homology_search(request):
    errors = []
    if request.method == 'POST':
        if not request.FILES.get('peptide_library',False) or not request.FILES.get('peptide_input',False):
            errors.append('Both file fields are mandatory.')
        if len(errors) == 0:
            try:
                output_path = blast_pipeline(request.FILES['peptide_library'],request.FILES['peptide_input'])
            except CalledProcessError as e:
                return render(request, 'peptide/homology_search.html', {'errors':[e.output]})
            return FileResponse(open(output_path, 'rb'), as_attachment=True)
    return render(request, 'peptide/homology_search.html', {'errors':errors})

def contact(request):
    errors = []
    messages = ''
    if request.method == 'POST':
        if len(errors) == 0:
            name = request.POST['name']
            email = request.POST['email']
            message = request.POST['message']

            try:
                messages = contact_us(name, email, message)
            except CalledProcessError as e:
                return render(request, 'peptide/contact.html', {'errors':[e.output]})
    return render(request, 'peptide/contact.html', {'errors':errors, 'messages':messages})

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

def peptide_multi_search(request):
    errors = []
    results = ''
    output_path = ''
    if request.method == 'POST':
        counter = Counter(ip=request.META['REMOTE_ADDR'], access_time=datetime.now(), page='peptide multi search')
        counter.save()

        if not request.FILES.get('tsv_file',False):
            errors.append('File fields are mandatory.')
        if len(errors) == 0:
            rt = 1 if request.POST.get('return_tsv') else 0
            try:
                (results,output_path) = pepdb_multi_search(request.FILES['tsv_file'])
            except CalledProcessError as e:
                return render(request, 'peptide/peptide_multi_search.html', {'errors':[e.output]})

            if rt == 1:
                return FileResponse(open(output_path, 'rb'), as_attachment=True)

    return render(request, 'peptide/peptide_multi_search.html', {'errors':errors, 'results':results, 'output_path':output_path})

#Updated rk 8/8/23
def peptide_search(request):
    errors = []
    results = []
    output_path = ''
    q = get_latest_peptides(1) #changed to 1 RK 8/4/23

    if request.method == 'POST':
        counter = Counter(ip=request.META['REMOTE_ADDR'], access_time=datetime.now(), page='peptide search')
        counter.save()

        peptides = request.POST.get('peptides', '').splitlines()
        # Save peptides to a file named pepfile.txt
        pepfile_path = os.path.join(settings.MEDIA_ROOT, "pepfile.txt")
        with open(os.path.join(settings.MEDIA_ROOT, "pepfile.txt"), "w") as pepfile:
            if len(peptides) == 0:
                pepfile.write("")
            else:
                for peptide in peptides:
                    pepfile.write(peptide + "\n")

        peptide_option = request.POST['peptide_option']
        pid = request.POST['proteinid']
        function = request.POST['function']
        seqsim = int(request.POST['seqsim'])
        matrix = request.POST['matrix']
        extra = 1 if request.POST.get('extra_output') else 0
        species = request.POST['species']
        category = request.POST['category']

        if not peptides and pid == "" and function == "" and species == "" and category == "":
            errors.append("Error: You must input at least one value.")
        try:
            (results,output_path) = pepdb_multi_search2(pepfile_path,peptide_option,pid,function,seqsim,matrix,extra,species,category)
            FileResponse(open(output_path, 'rb'))
        except CalledProcessError as e:
            return render(request, 'peptide/peptide_search.html', {'errors':[e.output], 'data':request.POST})
    return render(request, 'peptide/peptide_search.html', {'errors':errors, 'results':results, 'output_path':output_path, 'data':request.POST, 'latest_peptides':q})

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

def protein_headers(request):
    ret = subprocess.check_output("grep -h '>' "+settings.FASTA_FILES_DIR+"/* | sort -u", shell=True, stderr=subprocess.STDOUT)
    ret = ret.decode('utf-8')
    ret = ret.replace('\n', '<br />')
    return HttpResponse(ret)

#Updated rk 8/8/23
def tsv_search_results(request):
    file_path = request.path.replace("/tsv_search_results/", "")
    if re.match("^" + settings.WORK_DIRECTORY + ".+/MBPDB.+\.tsv$", file_path):
        response = FileResponse(open(file_path, 'rb'))
        return response

def about_us(request):
    return render(request, 'peptide/about_us.html')
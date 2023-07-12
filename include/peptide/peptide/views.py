from django.shortcuts import render

import os, re
from django.conf import settings
from .toolbox import blast_pipeline, skyline_pipeline, skyline_pipeline_auto, remove_domains, run_pepex, add_proteins, peptide_db_call, pepdb_add_csv,pepdb_search, pepdb_multi_search, pepdb_multi_search2, contact_us, get_latest_peptides
from sendfile import sendfile
from django.http.response import HttpResponse, HttpResponseRedirect
import subprocess
from subprocess import CalledProcessError
from django.contrib.auth.decorators import login_required
from .models import Counter
from datetime import datetime


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
            return sendfile(request,output_path,attachment=True)
    return render(request, 'peptide/homology_search.html', {'errors':errors})

def skyline(request):
    errors = []
    if request.method == 'POST':
        if not request.FILES.get('input_tsv',False) or not request.FILES.get('input_xmls',False):
            errors.append('Both file fields are mandatory.')
        if len(errors) == 0:
            output_path = '/tmp/skyline.tsv'
            try:
                skyline_pipeline(request.FILES['input_tsv'],request.FILES.getlist('input_xmls'),output_path)
            except CalledProcessError as e:
                return render(request, 'peptide/skyline.html', {'errors':[e.output]})
            return sendfile(request,output_path,attachment=True)
    return render(request, 'peptide/skyline.html', {'errors':errors})

def skyline_auto(request):
    errors = []
    if request.method == 'POST':
        if not request.FILES.get('input_tsv',False) or not request.FILES.get('input_xmls',False):
            errors.append('Both file fields are mandatory.')
        if len(errors) == 0:
            idotp = request.POST['idotp']
            reduce_columns = "1" if request.POST.get('reduce_columns') else "0"
            only_keep_true = "1" if request.POST.get('only_keep_true') else "0"
            # making absolutely sure that idotp is the correct format
            try:
                float(idotp)
            except ValueError as e:
                return render(request, 'peptide/skyline_auto.html', {'errors':[e.output]})

            try:
                output_path = skyline_pipeline_auto(idotp, reduce_columns, only_keep_true, request.FILES['input_tsv'],request.FILES.getlist('input_xmls'))
            except CalledProcessError as e:
                return render(request, 'peptide/skyline_auto.html', {'errors':[e.output]})
            return sendfile(request,output_path,attachment=True)
    return render(request, 'peptide/skyline_auto.html', {'errors':errors})

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
                return sendfile(request,output_path,attachment=True)

    return render(request, 'peptide/peptide_multi_search.html', {'errors':errors, 'results':results, 'output_path':output_path})

def peptide_search(request):
    errors = []
    results = []
    output_path = ''

    q = get_latest_peptides(3)

    if request.method == 'POST':
        counter = Counter(ip=request.META['REMOTE_ADDR'], access_time=datetime.now(), page='peptide search')
        counter.save()

        peptide = request.POST['peptide']
        if request.FILES.get('pepfile',False) and peptide!='':
            errors.append("Error: Please input EITHER a single peptide sequence OR a file with multiple peptides, but not both.")

        pid = request.POST['proteinid']
        function = request.POST['function']
        species = request.POST['species']
        category = request.POST['category']
        if peptide == '' and not request.FILES.get('pepfile',False) and pid == '' and function == '' and species == '' and category == '':
            errors.append("Error: You must input at least one of the following: Single Peptide Sequence, file with multiple peptides, Protein ID, Function, Species, or Category.")

        if len(errors) == 0:
            peptide_option = request.POST['peptide_option']
            pid = request.POST['proteinid']
            function = request.POST['function']
            seqsim = int(request.POST['seqsim'])
            matrix = request.POST['matrix']
            rt = 1 if request.POST.get('return_tsv') else 0
            extra = 1 if request.POST.get('extra_output') else 0
            species = request.POST['species']
            category = request.POST['category']

            try:
                if request.FILES.get('pepfile',False):
                    (results,output_path) = pepdb_multi_search2(request.FILES['pepfile'],peptide_option,pid,function,seqsim,matrix,extra,species,category)
                else:
                    (results,output_path) = pepdb_search(peptide,peptide_option,pid,function,seqsim,matrix,extra,species,category)
            except CalledProcessError as e:
                return render(request, 'peptide/peptide_search.html', {'errors':[e.output], 'data':request.POST})

            if rt == 1:
                return sendfile(request,output_path,attachment=True)

    return render(request, 'peptide/peptide_search.html', {'errors':errors, 'results':results, 'output_path':output_path, 'data':request.POST, 'latest_peptides':q})


def remove_domains_tool(request):
    errors = []
    if request.method == 'POST':
        if not request.FILES.get('input_xmls',False):
            errors.append('File fields are mandatory.')
        if len(errors) == 0:
            remove_all_mods = "1" if request.POST.get('remove_all_mods') else "0"
            try:
                output_path = remove_domains(request.FILES.getlist('input_xmls'), remove_all_mods)
            except CalledProcessError as e:
                return render(request, 'peptide/remove_domains_tool.html', {'errors':[e.output]})
            return sendfile(request,output_path,attachment=True)
    return render(request, 'peptide/remove_domains_tool.html', {'errors':errors})


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
                output_path = run_pepex (request.FILES['input_tsv'],count_pep)
            except CalledProcessError as e:
                return render(request, 'peptide/pepex.html', {'errors':e.output.rstrip('\n').split('\n')})
                #return render(request, 'peptide/pepex.html', {'errors':[e.output]})
            return sendfile(request,output_path,attachment=True)
    return render(request, 'peptide/pepex.html', {'errors':errors})


def protein_headers(request):
    ret = subprocess.check_output("grep -h '>' "+settings.FASTA_FILES_DIR+"/* | sort -u", shell=True, stderr=subprocess.STDOUT)
    ret = ret.replace('\n', '<br />')
    return HttpResponse(ret)


def tsv_search_results(request):
    file_path = request.path.replace("/tsv_search_results","")
    if re.match("^"+settings.WORK_DIRECTORY+".+/MBPDB.+\.tsv$", file_path):
        return sendfile(request,file_path,attachment=True)

"""
from django.core.files.temp import NamedTemporaryFile
def send_file(request):
    newfile = NamedTemporaryFile(suffix='.txt')
    # save your data to newfile.name
    wrapper = FileWrapper(newfile)
    response = HttpResponse(wrapper, content_type=mime_type)
    response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(modelfile.name)
    response['Content-Length'] = os.path.getsize(modelfile.name)
    return response
"""

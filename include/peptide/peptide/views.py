from django.shortcuts import render
import os, re
from .toolbox import func_list, clear_temp_directory, spec_list, pro_list, run_pepex, add_proteins, pepdb_add_csv, pepdb_multi_search_manual, get_latest_peptides
import subprocess
from subprocess import CalledProcessError
from .models import Counter
from django.utils import timezone
from django.http import FileResponse, HttpResponse, JsonResponse
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


#Updated handles the search from peptide_search.html, handles both tsv upload and manual peptide search
def peptide_search(request):
    # Clear the temp directory first
    WORK_DIRECTORY = os.path.join(settings.BASE_DIR, 'uploads/temp')
    clear_temp_directory(WORK_DIRECTORY)

    errors = []
    results_headers = []
    formated_header = []
    results = []
    peptide_option = []
    matrix = []
    output_path = ''
    combined_results = []
    q = get_latest_peptides(1)
    description_to_pid = pro_list(request)
    unique_func = func_list(request)
    common_to_sci = spec_list(request)
    if request.method == 'POST':
        counter = Counter(ip=request.META['REMOTE_ADDR'], access_time=timezone.now(), page='peptide search')
        counter.save()
        # Split the input based on comma, tab, space, or new line.
        peptides = re.split(r'[\s,\'\[\]\(\)\.\}\{"]+', request.POST.get('peptides', '').strip())
        peptide_option = request.POST.getlist('peptide_option')
        pid = request.POST.getlist('proteinid[]')
        function = request.POST.getlist('function[]')
        species = request.POST.getlist('species[]')
        seqsim = int(request.POST['seqsim'])
        matrix = request.POST.getlist('matrix')
        peptides = [peptide for peptide in peptides if peptide]
        if (len(peptides) > 10000):
            errors.append(
                f"Error: A maximium of 10,000 peptides can be search in one Querry. Please reduce the list from the {len(peptides)} peptides inputed in the last search.")
        for peptide in peptides:
            if not peptide.isalpha():
                errors.append(
                    f"Error: Invalid input '{peptide}'. Only text characters are allowed.")
            if len(peptide) >= 4:
                extra = 1
            else:
                extra = 0
        if not peptides:
               extra = 0


        # Save peptides to a file named pepfile.txt
        pepfile_path = os.path.join(settings.MEDIA_ROOT, "pepfile.txt")
        with open(os.path.join(settings.MEDIA_ROOT, "pepfile.txt"), "w") as pepfile:
            if len(peptides) == 0:
                no_pep = 1
                pepfile.write("")
            else:
                for peptide in peptides:
                    for po in peptide_option:
                        for m in matrix:
                            # Check if both peptide and po are not empty
                            if peptide.strip() and po.strip() and m.strip():
                                pepfile.write(peptide + ' ' + po + ' ' + m + "\n")
                            else:
                                # Handle the error case here if needed, for example:
                                errors.append("Error: Peptide, search type and scoring matrix must be non-empty.")
                no_pep = 0

        if not (peptides or pid or function or species):
            errors.append(
                f'Error: Please enter peptides into the Peptide Search box, or select a Function, Protein ID, or Species from the Advanced Search Option.')
        if not (seqsim and matrix and peptide_option):
            errors.append(
                f'Error: Please select the Search Type, Similarity Threshold and Scoring Matrix form the Homology Search Options')
        try:
            (results, formated_header,output_path,results_headers) = pepdb_multi_search_manual(pepfile_path,peptide_option,pid,function,seqsim,matrix,extra,species,no_pep)
            FileResponse(open(output_path, 'rb'))
        except CalledProcessError as e:
            return render(request, 'peptide/peptide_search.html', {'errors': [e.output], 'data':request.POST})

    # Given columns to check
    columns_to_check = [
        'Additional&nbspdetails',
        'IC50&nbsp(μM)&nbsp&nbsp&nbsp&nbsp',
        'Inhibition&nbsptype',
        'Inhibited&nbspmicroorganisms',
        'PTM'
    ]

    # Check for each column
    for column in columns_to_check:
        if all([(result.get(column, '').strip() == '' if isinstance(result, dict) else True) for result in results]):

            # Remove column from each dictionary in results
            for result in results:
                if column in result:
                    del result[column]

            # Remove column from headers
            if column in results_headers:
                results_headers.remove(column)

    for item in results:
        if isinstance(item, dict):  # Check if the item is a dictionary (a regular result)
            combined_results.append({"type": "result", "data": item})
        else:  # Assume it's a warning
            combined_results.append({"type": "warning", "data": item})

    # Initialize dictionaries for counting
    species_counts = {}
    function_counts = {}
    protein_id_counts = {}
    peptide_counts = {}

    for item in combined_results:
        if item['type'] == 'result':
            # Extracting and adding unique values
            peptide = item['data'].get('Peptide&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp', None)
            species = item['data'].get('Species&nbsp&nbsp&nbsp&nbsp', None)
            function = item['data'].get(
                'Function&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp', None)
            protein_id = item['data'].get('Protein&nbspID', None)

            # Update counts in dictionaries
            if peptide:
                peptide_counts[peptide] = peptide_counts.get(peptide, 0) + 1
            if species:
                species_counts[species] = species_counts.get(species, 0) + 1
            if function:
                function_counts[function] = function_counts.get(function, 0) + 1
            if protein_id:
                protein_id_counts[protein_id] = protein_id_counts.get(protein_id, 0) + 1

    return render(request, 'peptide/peptide_search.html', {
        'errors': errors,
        'combined_results': combined_results,
        'output_path': output_path,
        'data': request.POST,
        'peptide_option': peptide_option,
        'matrix': matrix,
        'latest_peptides': q,
        'description_to_pid': description_to_pid,
        'functions': unique_func,
        'common_to_sci_list': common_to_sci,
        'formated_header': formated_header,
        'table_headers': results_headers,
        'function_counts': function_counts,
        'species_counts': species_counts,
        'function_counts': function_counts,
        'protein_id_counts': protein_id_counts,
        'peptide_counts': peptide_counts,
    })


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
def download_fasta_file(request):
    # Assuming you have a single FASTA file in FASTA_FILES_DIR
    # If you have multiple files, you might need a way to specify which file to download
    fasta_file_path = os.path.join(settings.FASTA_FILES_DIR, "protein_database.fasta")
    response = FileResponse(open(fasta_file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(fasta_file_path)}"'
    return response

#Updated returns downloadable file to user
def tsv_search_results(request):
    debug_info = []  # List to collect debug information
    try:
        file_path = request.path.replace("/tsv_search_results/", "").lstrip('/')
        debug_info.append(f"File path from request: {file_path}")

        escaped_work_directory = re.escape(settings.WORK_DIRECTORY).lstrip('/')
        debug_info.append(f"Escaped work directory from settings: {escaped_work_directory}")

        regex_pattern = "^" + escaped_work_directory + "/work_.+/MBPDB.+\.tsv$"  # Updated regex
        debug_info.append(f"Regex pattern: {regex_pattern}")

        if re.match(regex_pattern, file_path):
            if file_path.startswith('/'):
                absolute_file_path = file_path  # It's already an absolute path
            else:
                # It's already an absolute path relative to the application directory, no need to append again.
                absolute_file_path = '/' + file_path

            debug_info.append(f"Absolute file path: {absolute_file_path}")

            if os.path.exists(absolute_file_path):
                response = FileResponse(open(absolute_file_path, 'rb'))
                return response
            else:
                debug_info.append("File not found")
                return HttpResponse("\n".join(debug_info), status=404)
    except Exception as e:
        debug_info.append(f"An error occurred: {str(e)}")
        return HttpResponse("\n".join(debug_info), status=500)

#Added  returns about us page
def about_us(request):
    q = get_latest_peptides(1)
    return render(request, 'peptide/about_us.html', {'latest_peptides': q})

#Added  returns protein list for the add peptide/protein page
def get_protein_list_view(request):
    data = pro_list(request)
    return JsonResponse(data)
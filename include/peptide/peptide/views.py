from django.shortcuts import render
import os, re, subprocess
from .toolbox import func_list, clear_temp_directory, spec_list, pro_list, run_pepex, add_proteins, pepdb_add_csv, get_latest_peptides, append_with_titnum

from subprocess import CalledProcessError
from .models import Counter, ProteinInfo, PeptideInfo, Function
from django.utils import timezone
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.urls import reverse

from celery.result import AsyncResult
from celery.app.control import Inspect
from peptide.celery import app

from .tasks import pepdb_multi_search_manual
from django.core.cache import cache


from django.shortcuts import render

def supplementals_tables_and_figures(request):
    return render(request, 'peptide/supplementals_tables_and_figures.html')

def zukaitis_2026(request):
    return render(request, 'peptide/zukaitis_2026.html')

def test(request):
    return render(request, 'peptide/test.html')

# Fetch active Task ID function
def get_active_tasks(request):
    i = Inspect(app=app)
    active_tasks = i.active()
    task_ids = []

    if active_tasks:
        for worker, tasks in active_tasks.items():
            for task in tasks:
                task_ids.append(task['id'])
    #print("active_taskID:",active_tasks)
    #print("i",i)
    return JsonResponse({'active_task_ids': task_ids,
                         'errors': []})

#Polls progress of celery task and returns to website
def check_progress(request, task_id):
    #print("check_progress_tsk_id", task_id)
    progress = cache.get(f'progress_{task_id}', 0)  # Default value if not set yet
    size = cache.get(f'size_{task_id}')
    elapsed_time = cache.get(f'elapsed_time_{task_id}', 0.0)  # Default value if not set yet
    status = cache.get(f'status_{task_id}', 'in_progress')  # Default status is 'in_progress'
    #print("status_check_progress_in_progress", status)
    #print("elapsed_time_check_progress_in_progress",elapsed_time)

    if status == 'in_progress':
        # Calculate percent progress and estimated time remaining
        if progress > 0 and size is not None and size > 0:
            percent_progress = progress / size * 100
            # Calculate estimated time remaining: (elapsed_time / percent_progress * 100) - elapsed_time
            total_estimated_time = elapsed_time * 100 / percent_progress
            estimated_time_remaining = total_estimated_time - elapsed_time
        else:
            percent_progress = 0.0
            estimated_time_remaining = None

        return JsonResponse({
            'task_id': task_id,
            'percent_progress': percent_progress,
            'progress': progress,
            'size': size,
            'elapsed_time': elapsed_time,
            'estimated_time_remaining': estimated_time_remaining,
            'status': status
        })

    if status == 'complete':
        elapsed_time = cache.get(f'elapsed_time_{task_id}', 0.0)  # Default value if not set yet
        percent_progress = 100
        #post_data, peptide_option, matrix, q, description_to_pid, unique_func, common_to_sci, errors, combined_results, output_path, formated_header, results_headers, species_counts, function_counts, protein_id_counts, peptide_counts = return_results(request, task_id)

        return JsonResponse({
            'task_id': task_id,
            'percent_progress': percent_progress,
            'progress': progress,
            'size': size,
            'elapsed_time': elapsed_time,
            'status': status
        })
        """
            'data': post_data,
            'peptide_option': peptide_option,
            'matrix': matrix,
            'latest_peptides': q,
            'description_to_pid': description_to_pid,
            'functions': unique_func,
            'common_to_sci_list': common_to_sci,
            'errors': errors,
            'combined_results': combined_results,
            'output_path': output_path,
            'formated_header': formated_header,
            'table_headers': results_headers,
            'species_counts': species_counts,
            'function_counts': function_counts,
            'protein_id_counts': protein_id_counts,
            'peptide_counts': peptide_counts,
        })
        """
    else:
        # Handle any other status (e.g., 'failed', 'pending', etc.)
        response_data = {
            'task_id': task_id,
            'status': status,
            'percent_progress': 0.0,
            'progress': progress,
            'size': size,
            'elapsed_time': elapsed_time,
        }
        return JsonResponse(response_data)

#Returns results of search to results_section html page
def return_render_results(request, task_id):
    if request.method == 'GET':
        q = get_latest_peptides(1)
        combined_results = []
        task_id_str = str(task_id)
        task_result = AsyncResult(task_id_str)
        
        # Initialize default values for template variables
        peptide_option = []
        matrix = []
        description_to_pid = {}
        unique_func = []
        common_to_sci = {}
        formated_header = ''
        
        if task_result.ready():
            # Check if task failed
            if task_result.failed():
                return render(request, 'peptide/results_section.html', {
                    'errors': ['Task failed to complete. Please try again.'],
                    'combined_results': [],
                    'output_path': '',
                    'data': request.POST,
                    'peptide_option': peptide_option,
                    'matrix': matrix,
                    'latest_peptides': q,
                    'description_to_pid': description_to_pid,
                    'functions': unique_func,
                    'common_to_sci_list': common_to_sci,
                    'formated_header': formated_header,
                    'table_headers': [],
                    'function_counts': {},
                    'species_counts': {},
                    'protein_id_counts': {},
                    'peptide_counts': {},
                })
            
            result_data = task_result.result
            
            # Handle case where result_data might be None
            if result_data is None:
                return render(request, 'peptide/results_section.html', {
                    'errors': ['Results are not yet available. Please wait a moment and refresh.'],
                    'combined_results': [],
                    'output_path': '',
                    'data': request.POST,
                    'peptide_option': peptide_option,
                    'matrix': matrix,
                    'latest_peptides': q,
                    'description_to_pid': description_to_pid,
                    'functions': unique_func,
                    'common_to_sci_list': common_to_sci,
                    'formated_header': formated_header,
                    'table_headers': [],
                    'function_counts': {},
                    'species_counts': {},
                    'protein_id_counts': {},
                    'peptide_counts': {},
                })

            results = result_data.get('results', [])
            formated_header = result_data.get('formated_header', '')
            output_path = result_data.get('output_path', '')
            results_headers = result_data.get('results_headers', [])

            # Given columns to check
            columns_to_check = [
                'Additional details',
                'IC50 (μM)',
                'Inhibition type',
                'Inhibited microorganisms',
                'PTM'
            ]

            # Check for each column
            for column in columns_to_check:
                if all([(result.get(column, '').strip() == '' if isinstance(result, dict) else True) for result in
                        results]):

                    # Remove column from each dictionary in results
                    for result in results:
                        if isinstance(result, dict) and column in result:
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
                    peptide = item['data'].get('Peptide', None)
                    species = item['data'].get('Species', None)
                    function = item['data'].get('Function', None)
                    protein_id = item['data'].get('Protein ID', None)

                    # Update counts in dictionaries
                    if peptide:
                        peptide_counts[peptide] = peptide_counts.get(peptide, 0) + 1
                    if species:
                        species_counts[species] = species_counts.get(species, 0) + 1
                    if function:
                        function_counts[function] = function_counts.get(function, 0) + 1
                    if protein_id:
                        protein_id_counts[protein_id] = protein_id_counts.get(protein_id, 0) + 1

            if len(results) >= 1000:
                # Remove all warnings from combined_results
                combined_results = [item for item in combined_results if item['type'] != 'warning']

                # Insert a new warning at the start
                download_url = reverse('tsv_search_results') + output_path

                combined_results.insert(0, {
                    "type": "warning",
                    "data": (
                        f'<div style="font-size: 18px; color: red; padding: 10px;">'
                        f'Search results exceed 1,000 entries. Non-matching results have been hidden from this display but can be reviewed in the '
                        f'<a href="{download_url}" download style="color: blue; text-decoration: underline;">downloadable file</a>.'
                        f'</div>'
                    )
                })

            return render(request, 'peptide/results_section.html', {
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
                'protein_id_counts': protein_id_counts,
                'peptide_counts': peptide_counts,
            })
        else:
            # Task not ready yet
            return render(request, 'peptide/results_section.html', {
                'errors': ['Results are still being processed. Please wait...'],
                'combined_results': [],
                'output_path': '',
                'data': request.POST,
                'peptide_option': peptide_option,
                'matrix': matrix,
                'latest_peptides': q,
                'description_to_pid': description_to_pid,
                'functions': unique_func,
                'common_to_sci_list': common_to_sci,
                'formated_header': formated_header,
                'table_headers': [],
                'function_counts': {},
                'species_counts': {},
                'protein_id_counts': {},
                'peptide_counts': {},
            })

def start_work(request):
    # Get the task_id from cache (set by peptide_search)
    # Use a session-based key to track the most recent task for this user
    session_key = request.session.session_key or 'anonymous'
    task_id = cache.get(f'latest_task_{session_key}')
    
    if not task_id:
        return JsonResponse({'error': 'No task found. Please submit a search first.'}, status=400)
    
    return JsonResponse({'task_id': task_id})

def get_request_parameter(request, param_name):
    param_value = request.POST.get(param_name)
    if param_value is not None:
        if param_value == '':
            return []
        return [param_value]

    param_list = request.POST.getlist(param_name + '[]')
    return [item for item in param_list if item]  # Filter out empty strings

#Updated handles the search from peptide_search.html, handles both tsv upload and manual peptide search
def peptide_search(request):
    # Clear the temp directory first
    global WORK_DIRECTORY, errors, peptide_option, matrix, pid, seqsim, species, function, description_to_pid, unique_func, common_to_sci, post_data

    WORK_DIRECTORY = os.path.join(settings.BASE_DIR, 'uploads/temp')
    clear_temp_directory(WORK_DIRECTORY)
    errors = []
    peptide_option = []
    matrix = []
    description_to_pid = pro_list(request)
    unique_func = func_list(request)
    common_to_sci = spec_list(request)
    q = get_latest_peptides(1)
    if request.method == 'POST':
        post_data = request.POST
        #print(post_data)
        counter = Counter(ip=request.META['REMOTE_ADDR'], access_time=timezone.now(), page='peptide search')
        counter.save()
        # Split the input based on comma, tab, space, or new line.
        peptides_raw = request.POST.get('peptides', '').strip()
        peptides_cleaned = peptides_raw.replace('\r\n', ' ')  # Replace '\r\n' with a space
        peptides = re.split(r'[\s,\'\[\]\(\)\.\}\{"]+', peptides_cleaned)

        peptide_option = get_request_parameter(request, 'peptide_option')
        pid = get_request_parameter(request, 'proteinid')
        function = get_request_parameter(request, 'function')
        species = get_request_parameter(request, 'species')
        seqsim = int(request.POST['seqsim'])
        matrix = get_request_parameter(request, 'matrix')
        peptides = [peptide for peptide in peptides if peptide]

        #("len(peptides) ",len(peptides) )
        #if (len(peptides) > 10000):
        #    errors.append(
        #        f"Error: A maximium of 10,000 peptides can be search in one Querry. Please reduce the list from the {len(peptides)} peptides inputed in the last search.")
        for peptide in peptides:
            if not peptide.isalpha():
                errors.append(
                    f"Error: Invalid input '{peptide}'. Only text characters are allowed.")
            if len(peptide) >= 4:
                extra = 1
                break  # Exits the loop after the condition is met
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
        #print("peptides",peptides,"pid",pid,"function",function,"species",species,"no_pep",no_pep)

        if not (peptides or pid or function or species):
            errors.append(
                f'Error: Please enter peptides into the Peptide Search box, or select a Function, Protein ID, or Species from the Advanced Search Option.')
        if not (seqsim and matrix and peptide_option):
            errors.append(
                f'Error: Please select the Search Type, Similarity Threshold and Scoring Matrix form the Homology Search Options')

        if errors:
            return JsonResponse({'errors': errors})
        try:
            #(results, formated_header,output_path,results_headers) = pepdb_multi_search_manual.delay(pepfile_path,peptide_option,pid,function,seqsim,matrix,extra,species,no_pep)
            global task, task_id
            task = pepdb_multi_search_manual.delay(pepfile_path,peptide_option,pid,function,seqsim,matrix,extra,species,no_pep)
            task_id = task.id
            # Store task_id in cache for start_work to retrieve
            session_key = request.session.session_key or 'anonymous'
            cache.set(f'latest_task_{session_key}', task_id, timeout=3600)  # Store for 1 hour
            # Return JSON for AJAX requests, HTML for regular requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'task_id': task_id, 'errors': []})
            return render(request, 'peptide/peptide_search.html', {
                'errors': errors,
                'data': request.POST,
                'peptide_option': peptide_option,
                'matrix': matrix,
                'latest_peptides': q,
                'description_to_pid': description_to_pid,
                'functions': unique_func,
                'common_to_sci_list': common_to_sci,
                'task_id': task_id
            })
        except CalledProcessError as e:
            #return render(request, 'peptide/peptide_search.html', {'errors': [e.output], 'data': request.POST})
            return JsonResponse({'errors': [e.output]})

    #return JsonResponse({'task_id': task_id})

    return render(request, 'peptide/peptide_search.html', {
        'errors': errors,
        'data': request.POST,
        'peptide_option': peptide_option,
        'matrix': matrix,
        'latest_peptides': q,
        'description_to_pid': description_to_pid,
        'functions': unique_func,
        'common_to_sci_list': common_to_sci,
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
        #file_path = re.escape(settings.WORK_DIRECTORY)
        debug_info.append(f"BASE_DIR: {settings.BASE_DIR}\n")

        file_path = request.path.replace("/tsv_search_results/", "/")  # No lstrip
        if file_path.startswith('//'):
            file_path = request.path.replace("/tsv_search_results/", "")  # No lstrip
        debug_info.append(f"File path from request: {file_path}\n")

        escaped_work_directory = re.escape(settings.WORK_DIRECTORY)  # No lstrip
        debug_info.append(f"Escaped work directory from settings: {escaped_work_directory}\n")

        if file_path.startswith('/'):
            regex_pattern = f"^{escaped_work_directory}/work_.+/MBPDB.+\\.tsv$"  # Updated regex
        else:
            regex_pattern = f"^/{escaped_work_directory}/work_.+/MBPDB.+\\.tsv$"  # Updated regex

        debug_info.append(f"Regex pattern: {regex_pattern}\n")

        if re.match(regex_pattern, file_path):
            if file_path.startswith('/'):
                absolute_file_path = file_path  # It's already an absolute path
                debug_info.append(f"File path starts with /: {absolute_file_path}\n")
            else:
                # Assume it's a relative path and make it absolute
                absolute_file_path = '/' + file_path
                debug_info.append(f"File path does not start with /: {absolute_file_path}\n")

            if os.path.exists(absolute_file_path):
                response = FileResponse(open(absolute_file_path, 'rb'))
                debug_info.append("File found, returning FileResponse\n")
                return response
            else:
                debug_info.append("File not found\n")
                return HttpResponse("\n".join(debug_info), status=404, content_type='text/plain')

    except Exception as e:
        debug_info.append(f"An error occurred: {str(e)}\n")
        return HttpResponse("\n".join(debug_info), status=500, content_type='text/plain')

    # If none of the above returns execute, return a general error (this shouldn't normally be reached)
    debug_info.append("An unexpected error occurred\n")
    return HttpResponse("\n".join(debug_info), status=500, content_type='text/plain')

#Added  returns about us page
def about_us(request):
    q = get_latest_peptides(1)
    return render(request, 'peptide/about_us.html', {'latest_peptides': q})

#Renders results section which is seperate html with results of query
def results_section(request, task_id):
    # Assuming task_id is being passed in the URL or through some other means
    context = {
        'task_id': task_id
    }
    return render(request, 'peptide/results_section.html', context)

def test(request):
    return render(request, 'peptide/test.html')

#Added  returns protein list for the add peptide/protein page
def get_protein_list_view(request):
    data = pro_list(request)
    return JsonResponse(data)

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

def peptiline_landing(request):
    return render(request, 'peptide/peptiline_landing.html')

def download_supplemental_table(request):
    """Serve the supplemental table file for download."""
    file_path = os.path.join(settings.STATIC_ROOT, 'peptide', 'publications', 'zukaitis_2026', 'supplementals', 'correlation_analysis_pearson_log10_20250917_194233.xlsx')
    
    try:
        response = FileResponse(open(file_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="supplemental_table_1.xlsx"'
        return response
    except FileNotFoundError:
        return HttpResponse("Supplemental table file not found", status=404)

def serve_supplemental_figure_1(request):
    """Serve scatter_plot_1.html as supplemental figure 1."""
    file_path = os.path.join(settings.STATIC_ROOT, 'peptide', 'publications', 'zukaitis_2026', 'supplementals', 'scatter_plot_1.html')
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse("Supplemental figure 1 not found", status=404)

def serve_supplemental_figure_2(request):
    """Serve scatter_plot_2.html as supplemental figure 2."""
    file_path = os.path.join(settings.STATIC_ROOT, 'peptide', 'publications', 'zukaitis_2026', 'supplementals', 'scatter_plot_2.html')
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse("Supplemental figure 2 not found", status=404)
"""
def serve_plot(request, plot_name):
    #Serve Plotly HTML files.
    template_dir = os.path.join(os.path.dirname(__file__), 'templates', 'peptide')
    plot_path = os.path.join(template_dir, f'{plot_name}.html')

    try:
        with open(plot_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse(f"Plot {plot_name} not found", status=404)

import logging

logger = logging.getLogger(__name__)

def log_message(request):
    if request.method == 'POST':
        message = request.POST.get('message')
        logger.info(message)
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)
"""


# ---------------------------------------------------------------------------
# Default all-peptides view (loaded on page open)
# ---------------------------------------------------------------------------

@require_GET
def all_peptides_view(request):
    """Return all peptides in the database rendered as results_section.html."""
    results_headers = [
        'Protein ID', 'Peptide', 'Protein description', 'Species',
        'Intervals', 'Function', 'Additional details', 'IC50 (μM)',
        'Inhibition type', 'Inhibited microorganisms', 'PTM',
        'Title', 'Authors', 'Abstract', 'DOI'
    ]

    peptides = (
        PeptideInfo.objects.all()
        .select_related('protein')
        .prefetch_related('functions__references')
    )

    results = []
    for info in peptides:
        for func in info.functions.all():
            pp = info.protein.pid
            pd = info.protein.desc
            if info.protein_variants:
                pp = pp + " Genetic Variant " + info.protein_variants
                pd = pd + " Genetic Variant " + info.protein_variants

            refs = list(func.references.all())
            titles, authors, abstracts, dois = [], [], [], []
            ad, ic, it, im, ptms = [], [], [], [], []
            titnum = 1
            for ref in refs:
                if ref.title:
                    append_with_titnum(titles, ref.title, titnum)
                if ref.additional_details:
                    append_with_titnum(ad, ref.additional_details, titnum)
                if ref.ic50 is not None and str(ref.ic50) != '':
                    append_with_titnum(ic, str(ref.ic50), titnum)
                if ref.inhibition_type:
                    append_with_titnum(it, ref.inhibition_type, titnum)
                if ref.inhibited_microorganisms:
                    append_with_titnum(im, ref.inhibited_microorganisms, titnum)
                if ref.ptm:
                    append_with_titnum(ptms, ref.ptm, titnum)
                if ref.authors:
                    append_with_titnum(authors, ref.authors, titnum)
                if ref.abstract:
                    append_with_titnum(abstracts, ref.abstract, titnum)
                if ref.doi:
                    append_with_titnum(dois, ref.doi, titnum)
                titnum += 1

            row = {
                'Protein ID': pp,
                'Peptide': info.peptide,
                'Protein description': pd,
                'Species': info.protein.species,
                'Intervals': info.intervals,
                'Function': func.function,
                'Additional details': ',<br>'.join(ad),
                'IC50 (μM)': ',<br>'.join(ic),
                'Inhibition type': ',<br>'.join(it),
                'Inhibited microorganisms': ',<br>'.join(im),
                'PTM': ',<br>'.join(ptms),
                'Title': ',<br>'.join(titles),
                'Authors': ',<br>'.join(authors),
                'Abstract': ',<br>'.join(abstracts),
                'DOI': ',<br>'.join(dois),
            }
            # Remove 'None' strings
            row = {k: ('' if v == 'None' else v) for k, v in row.items()}
            results.append(row)

    # Remove empty columns
    columns_to_check = [
        'Additional details', 'IC50 (μM)', 'Inhibition type',
        'Inhibited microorganisms', 'PTM'
    ]
    for column in columns_to_check:
        if all(r.get(column, '').strip() == '' for r in results):
            for r in results:
                r.pop(column, None)
            if column in results_headers:
                results_headers.remove(column)

    combined_results = [{"type": "result", "data": r} for r in results]

    # Build counts
    species_counts, function_counts, protein_id_counts, peptide_counts = {}, {}, {}, {}
    for item in combined_results:
        d = item['data']
        pep = d.get('Peptide')
        sp = d.get('Species')
        fn = d.get('Function')
        pid = d.get('Protein ID')
        if pep:
            peptide_counts[pep] = peptide_counts.get(pep, 0) + 1
        if sp:
            species_counts[sp] = species_counts.get(sp, 0) + 1
        if fn:
            function_counts[fn] = function_counts.get(fn, 0) + 1
        if pid:
            protein_id_counts[pid] = protein_id_counts.get(pid, 0) + 1

    return render(request, 'peptide/results_section.html', {
        'combined_results': combined_results,
        'output_path': '',
        'data': {},
        'peptide_option': [],
        'matrix': [],
        'latest_peptides': [],
        'description_to_pid': {},
        'functions': [],
        'common_to_sci_list': {},
        'formated_header': '',
        'table_headers': results_headers,
        'function_counts': function_counts,
        'species_counts': species_counts,
        'protein_id_counts': protein_id_counts,
        'peptide_counts': peptide_counts,
        'is_default_view': True,
    })


# ---------------------------------------------------------------------------
# Bioactivity Visualization
# ---------------------------------------------------------------------------

@require_GET
def bioactivity_viz_proteins(request):
    """Return list of proteins that have peptides with bioactive functions."""
    protein_ids_with_functions = (
        Function.objects
        .values_list('pep__protein__id', flat=True)
        .distinct()
    )
    proteins = (
        ProteinInfo.objects
        .filter(id__in=protein_ids_with_functions)
        .values('pid', 'desc', 'species')
        .order_by('desc')
    )
    protein_list = [
        {'pid': p['pid'], 'label': f"{p['desc']} ({p['pid']}) - {p['species']}"}
        for p in proteins
    ]
    return JsonResponse({'proteins': protein_list})


@require_POST
def bioactivity_viz_plot(request):
    """
    Generate an interactive Plotly bioactivity map for a given protein.

    The figure is similar to example_figure.jpg: the protein amino acid sequence
    is displayed along the x-axis, and colored horizontal bars show where each
    bioactive peptide maps onto the protein, color-coded by bioactive function.
    Hover text shows peptide sequence, amino acid, and bioactive functions.

    POST body (JSON): {"protein_id": "P02666"}
    Returns: Plotly figure JSON.
    """
    import json as _json
    try:
        body = _json.loads(request.body)
        protein_id = body.get('protein_id', '').strip()
        selected_functions = body.get('functions', [])  # optional function filter
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    if not protein_id:
        return JsonResponse({'error': 'protein_id is required.'}, status=400)

    # Look up protein
    try:
        protein = ProteinInfo.objects.get(pid=protein_id)
    except ProteinInfo.DoesNotExist:
        return JsonResponse({'error': f'Protein {protein_id} not found.'}, status=404)

    sequence = protein.seq
    if not sequence:
        return JsonResponse({'error': f'No sequence available for {protein_id}.'}, status=400)

    # Get all peptides for this protein that have at least one function
    peptides = PeptideInfo.objects.filter(protein=protein).prefetch_related('functions')

    # Build list of peptide entries with their functions and intervals
    peptide_entries = []
    for pep in peptides:
        funcs = list(pep.functions.values_list('function', flat=True))
        if not funcs:
            continue
        # Apply function filter if provided
        if selected_functions:
            funcs = [f for f in funcs if f in selected_functions]
            if not funcs:
                continue
        # Parse intervals like "96-97, 114-115, 168-169"
        intervals_str = pep.intervals.strip()
        if not intervals_str:
            continue
        for interval in intervals_str.split(','):
            interval = interval.strip()
            if '-' not in interval:
                continue
            parts = interval.split('-')
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
            except (ValueError, IndexError):
                continue
            peptide_entries.append({
                'peptide': pep.peptide,
                'start': start,
                'end': end,
                'functions': funcs,
            })

    if not peptide_entries:
        return JsonResponse({
            'error': f'No bioactive peptides found for protein {protein_id}.'
        }, status=404)

    # Generate Plotly figure
    fig_json = _build_bioactivity_figure(protein, sequence, peptide_entries)

    return JsonResponse({'success': True, 'figure': fig_json})


def _build_bioactivity_figure(protein, sequence, peptide_entries):
    """
    Build a Plotly figure JSON dict showing a heatmap-style bioactivity map.

    Styling matches the heatmap visualization app:
    - RdYlGn_r colormap with discrete binning (6 groups max)
    - Seamless AA cells (no borders)
    - Discrete color-range legend for peptide counts
    - Hover text with each function and peptide on its own line
    - Position numbers spaced above the sequence with no overlap
    - Vertical function legend on the right
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    from matplotlib import colormaps as mpl_colormaps
    from matplotlib.colors import Normalize

    CHUNK_SIZE = 70  # amino acids per row
    seq_len = len(sequence)
    num_chunks = (seq_len + CHUNK_SIZE - 1) // CHUNK_SIZE

    # Assign colors to functions
    FUNCTION_COLORS = {
        'ACE-inhibitory': '#E27D8A',
        'Antimicrobial': '#D4A843',
        'Antioxidant': '#2D8A4E',
        'DPP-IV Inhibitory': '#A8D8EA',
        'Opioid': '#5B8C5A',
        'Immunomodulatory': '#4A7C8C',
        'Anticancer': '#8B5E83',
        'Antihypertensive': '#C97B4B',
        'Antithrombotic': '#6B8E9B',
        'Osteoanabolic': '#B8860B',
        'Increase cellular growth': '#9370DB',
        'Increase mucin secretion': '#FF8C69',
        'Increase calcium uptake': '#20B2AA',
        'Cholesterol regulation': '#CD853F',
        'Wound healing': '#DC143C',
        'Antianxiety': '#4169E1',
        'Prolyl endopeptidase-inhibitory': '#708090',
        'Satiety': '#FFD700',
        'Cytomodulatory': '#8FBC8F',
        'Bradykinin-Potentiating': '#FF69B4',
        'Cathepsin B Inhibitory': '#A0522D',
        'Nitric oxide liberation': '#7FFFD4',
        'Anti-obesity': '#FF4500',
        'DNA repair': '#9932CC',
        'Bacterial growth promoting': '#BDB76B',
        'Cytotoxic': '#FF1493',
        'Enhance insulin signaling': '#00CED1',
        'Ameliorates insulin resistance': '#BA55D3',
        'Increase exocrine pancreatic secretion': '#DAA520',
        'Increase intestinal motility': '#48D1CC',
        'Cell Penetrating': '#C71585',
        'Improves cognition': '#3CB371',
    }
    DEFAULT_COLORS = [
        '#E27D8A', '#D4A843', '#2D8A4E', '#A8D8EA', '#5B8C5A',
        '#4A7C8C', '#8B5E83', '#C97B4B', '#6B8E9B', '#B8860B',
    ]

    # Collect all unique functions
    all_functions = set()
    for entry in peptide_entries:
        all_functions.update(entry['functions'])
    all_functions = sorted(all_functions)

    # Assign colors
    func_color = {}
    color_idx = 0
    for func in all_functions:
        if func in FUNCTION_COLORS:
            func_color[func] = FUNCTION_COLORS[func]
        else:
            func_color[func] = DEFAULT_COLORS[color_idx % len(DEFAULT_COLORS)]
            color_idx += 1

    # ---- Pre-compute per-position data ----
    pos_count = [0] * (seq_len + 1)       # 1-indexed
    pos_functions = [set() for _ in range(seq_len + 1)]
    # Store full entry dicts per position for rich hover text
    pos_peptide_entries = [[] for _ in range(seq_len + 1)]

    for entry in peptide_entries:
        for p in range(entry['start'], entry['end'] + 1):
            if 1 <= p <= seq_len:
                pos_count[p] += 1
                pos_functions[p].update(entry['functions'])
                pos_peptide_entries[p].append(entry)

    max_count = max(pos_count[1:]) if seq_len > 0 else 1
    if max_count == 0:
        max_count = 1

    # ---- RdYlGn_r colormap with binning (matching heatmap_renderer) ----
    cmap = mpl_colormaps.get_cmap('RdYlGn_r')
    plot_zero = 'no'  # white for zero counts
    num_unique = len(set(pos_count[1:]))
    num_colors = 6 if num_unique >= 6 else max(num_unique, 1)
    start_point = 1  # plot_zero='no'

    group_bounds = np.linspace(start_point, max_count, num_colors + 1)

    def _get_cell_color(count):
        """Return rgba string for a peptide count, matching heatmap binning."""
        if count == 0:
            return 'rgba(255,255,255,1.0)'
        if max_count > 20:
            rgba = cmap(count / max_count)
        else:
            label = int(np.digitize(count, bins=group_bounds, right=True))
            norm = Normalize(vmin=start_point, vmax=num_colors)
            rgba = cmap(norm(label))
        r, g, b, a = [int(c * 255) for c in rgba[:3]] + [rgba[3]]
        return f'rgba({r},{g},{b},{a:.2f})'

    def _get_text_color(count):
        """Return white or black text depending on background luminance."""
        if count == 0:
            return '#333333'
        if max_count > 20:
            rgba = cmap(count / max_count)
        else:
            label = int(np.digitize(count, bins=group_bounds, right=True))
            norm = Normalize(vmin=start_point, vmax=num_colors)
            rgba = cmap(norm(label))
        # Perceived luminance
        lum = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
        return 'white' if lum < 0.5 else '#333333'

    # ---- Build discrete legend labels & colors (matching create_heatmap_legend_handles) ----
    count_ranges = np.linspace(start_point, max_count, num_colors + 1)
    legend_colors = []
    legend_labels = []
    if max_count == 0:
        legend_colors.append('rgba(255,255,255,1.0)')
        legend_labels.append('0')
    else:
        plt_interval = max_count if max_count > num_colors else num_colors
        start_idx = 1 if plt_interval <= 6 else 0
        norm_leg = Normalize(vmin=start_point, vmax=max_count)
        for i in range(start_idx, len(count_ranges)):
            rgba = cmap(norm_leg(count_ranges[i]))
            r, g, b = [int(c * 255) for c in rgba[:3]]
            legend_colors.append(f'rgb({r},{g},{b})')
            if plt_interval <= 6:
                legend_labels.append(f'{int(count_ranges[i])}')
            elif i + 1 >= len(count_ranges):
                legend_labels.append(f'{int(count_ranges[i])} - {int(max(count_ranges))}')
                break
            else:
                legend_labels.append(f'{int(count_ranges[i])} - {int(count_ranges[i + 1])}')

    # ---- Compute peptide bar rows per chunk ----
    chunk_bar_rows = []
    for chunk_idx in range(num_chunks):
        chunk_start = chunk_idx * CHUNK_SIZE + 1
        chunk_end = min((chunk_idx + 1) * CHUNK_SIZE, seq_len)
        chunk_peptides = [e for e in peptide_entries
                          if e['end'] >= chunk_start and e['start'] <= chunk_end]
        y_offset = 0
        for func in all_functions:
            entries_for_func = [e for e in chunk_peptides if func in e['functions']]
            if not entries_for_func:
                continue
            entries_for_func.sort(key=lambda e: (e['start'], e['end']))
            sub_rows = []
            for entry in entries_for_func:
                placed = False
                for sr in sub_rows:
                    if entry['start'] > sr[-1]['end']:
                        sr.append(entry)
                        placed = True
                        break
                if not placed:
                    sub_rows.append([entry])
            y_offset += len(sub_rows)
        chunk_bar_rows.append(max(y_offset, 1))

    # Row heights proportional to content: 1 (AA row) + bar_rows
    row_heights = [1 + br for br in chunk_bar_rows]
    total_h = sum(row_heights)
    row_height_fracs = [h / total_h for h in row_heights]

    fig = make_subplots(
        rows=num_chunks, cols=1,
        shared_xaxes=False,
        vertical_spacing=0.03,
        subplot_titles=['' for _ in range(num_chunks)],
        row_heights=row_height_fracs,
    )

    # Track which functions we've already added to legend
    legend_added = set()
    _MAX_PEP = 25   # cap peptides in hover to keep text manageable

    for chunk_idx in range(num_chunks):
        chunk_start = chunk_idx * CHUNK_SIZE + 1  # 1-based
        chunk_end = min((chunk_idx + 1) * CHUNK_SIZE, seq_len)
        row = chunk_idx + 1

        xref = f'x{row}' if row > 1 else 'x'
        yref = f'y{row}' if row > 1 else 'y'

        # ---- Amino acid heatmap row (y = 0) ----
        # Seamless colored rectangles — NO borders (matching heatmap_renderer marker_line_width=0)
        for pos in range(chunk_start, chunk_end + 1):
            count = pos_count[pos]
            fill_color = _get_cell_color(count)

            fig.add_shape(
                type='rect',
                x0=pos - 0.5, x1=pos + 0.5,
                y0=-0.5, y1=0.5,
                fillcolor=fill_color,
                line=dict(width=0),
                xref=xref, yref=yref,
            )

            # AA letter annotation (matching heatmap: 13px, #333333 or white)
            aa = sequence[pos - 1]
            text_color = _get_text_color(count)
            fig.add_annotation(
                x=pos, y=0,
                text=f'<b>{aa}</b>',
                showarrow=False,
                font=dict(size=10, family='Courier New, monospace', color=text_color),
                xref=xref, yref=yref,
            )

        # ---- Hover text for AA cells (each function and peptide on its own line) ----
        hover_x = list(range(chunk_start, chunk_end + 1))
        hover_y = [0] * len(hover_x)
        hover_texts = []
        for pos in hover_x:
            aa = sequence[pos - 1]
            count = pos_count[pos]
            funcs_at = sorted(pos_functions[pos])
            entries_at = pos_peptide_entries[pos]

            # Build function list — each on its own line
            if funcs_at:
                func_lines = '<br>'.join(f'&nbsp;&nbsp;{f}' for f in funcs_at)
                func_block = f'<b>Functions:</b><br>{func_lines}'
            else:
                func_block = '<b>Functions:</b> None'

            # Build overlapping peptides block — vertically aligned
            # monospace display matching the heatmap application hover format.
            # Each peptide is padded so the bolded amino acid at the hovered
            # position falls in the same vertical column across all entries.
            unique_peps = []
            seen = set()
            for e in entries_at:
                key = (e['peptide'], e['start'], e['end'])
                if key not in seen:
                    seen.add(key)
                    unique_peps.append(e)

            if unique_peps:
                orig_len = len(unique_peps)
                truncated = orig_len > _MAX_PEP
                shown = unique_peps[:_MAX_PEP]
                offsets = [pos - e['start'] for e in shown]
                max_off = max(offsets)
                n_dig = len(str(orig_len))  # consistent ID width
                pep_lines = []
                for uid, (e, off) in enumerate(zip(shown, offsets), start=1):
                    pep_seq = e['peptide']
                    pad = '&nbsp;' * (max_off - off)
                    if 0 <= off < len(pep_seq):
                        seq_html = (pad + pep_seq[:off]
                                    + f'[<b>{pep_seq[off]}</b>]'
                                    + pep_seq[off + 1:])
                    else:
                        seq_html = pad + pep_seq
                    id_str = str(uid).rjust(n_dig)
                    pep_lines.append(f'{id_str}.&nbsp;{seq_html}')
                if truncated:
                    pep_lines.append(f'&nbsp;&nbsp;&nbsp;… and {orig_len - _MAX_PEP} more')
                pep_block = (
                    '<br><b>Overlapping Peptides:</b><br>'
                    '<span style="font-family:monospace">'
                    + '<br>'.join(pep_lines)
                    + '</span>'
                )
            else:
                pep_block = ''

            ht = (
                f"<b>Position: {pos} | {aa}</b><br>"
                f"Peptide Count: {count}<br>"
                f"{func_block}"
                f"{pep_block}"
            )
            hover_texts.append(ht)

        fig.add_trace(
            go.Scatter(
                x=hover_x, y=hover_y,
                mode='markers',
                marker=dict(size=12, opacity=0),
                hovertemplate='%{customdata}<extra></extra>',
                customdata=hover_texts,
                showlegend=False,
            ),
            row=row, col=1,
        )

        # ---- Position number annotations — spaced above the AA strip ----
        for pos in range(chunk_start, chunk_end + 1):
            if pos % 10 == 0 or pos == 1:
                fig.add_annotation(
                    x=pos, y=1.0,
                    text=str(pos),
                    showarrow=False,
                    font=dict(size=12, color='black'),
                    xref=xref, yref=yref,
                    yanchor='bottom',
                )

        # ---- Peptide bars below AA row ----
        chunk_peptides = [e for e in peptide_entries
                          if e['end'] >= chunk_start and e['start'] <= chunk_end]

        y_offset = 0
        for func in all_functions:
            entries_for_func = [e for e in chunk_peptides if func in e['functions']]
            if not entries_for_func:
                continue

            entries_for_func.sort(key=lambda e: (e['start'], e['end']))

            sub_rows = []
            for entry in entries_for_func:
                placed = False
                for sr in sub_rows:
                    if entry['start'] > sr[-1]['end']:
                        sr.append(entry)
                        placed = True
                        break
                if not placed:
                    sub_rows.append([entry])

            for sr_idx, sr in enumerate(sub_rows):
                for entry in sr:
                    bar_start = max(entry['start'], chunk_start)
                    bar_end = min(entry['end'], chunk_end)

                    pep_seq = entry['peptide']
                    aa_range = sequence[bar_start - 1:bar_end]
                    # Each function on its own line in bar hover too
                    func_lines = '<br>'.join(
                        f'&nbsp;&nbsp;{f}' for f in entry['functions']
                    )
                    hover = (
                        f"<b>Peptide:</b> {pep_seq}<br>"
                        f"<b>Position:</b> {entry['start']}-{entry['end']}<br>"
                        f"<b>Amino Acids:</b> {aa_range}<br>"
                        f"<b>Functions:</b><br>{func_lines}"
                    )

                    y_val = -(y_offset + sr_idx + 1.5)
                    show_legend = func not in legend_added

                    fig.add_trace(
                        go.Bar(
                            x=[bar_end - bar_start + 1],
                            y=[y_val],
                            base=[bar_start - 0.5],
                            orientation='h',
                            marker_color=func_color[func],
                            name=func,
                            legendgroup=func,
                            showlegend=show_legend,
                            hovertemplate=hover + '<extra></extra>',
                            width=0.8,
                        ),
                        row=row, col=1,
                    )
                    if show_legend:
                        legend_added.add(func)

            y_offset += len(sub_rows)

        # ---- Axis configuration ----
        xaxis_key = f'xaxis{row}' if row > 1 else 'xaxis'
        yaxis_key = f'yaxis{row}' if row > 1 else 'yaxis'

        # Fixed x-range per chunk: start at chunk_start, span CHUNK_SIZE positions
        fig.update_layout(**{
            xaxis_key: dict(
                range=[chunk_start - 0.5, chunk_start + CHUNK_SIZE - 0.5],
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                fixedrange=True,
            ),
            yaxis_key: dict(
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                range=[-(y_offset + 1.5) if y_offset > 0 else -2.5, 1.5],
                fixedrange=True,
            ),
        })

    # ---- Peptide count discrete legend (matching heatmap_renderer style) ----
    # Add invisible bar traces for each count range to create the legend
    for lbl, col in zip(legend_labels, legend_colors):
        fig.add_trace(
            go.Bar(
                x=[None], y=[None],
                marker_color=col,
                name=lbl,
                legendgroup='peptide_counts',
                legendgrouptitle_text='<b>Peptide Counts:</b>',
                showlegend=True,
                hoverinfo='skip',
            ),
            row=1, col=1,
        )

    # Overall layout
    total_height = max(450, num_chunks * 220)
    fig.update_layout(
        title=dict(
            text=f"Bioactive Peptide Map: {protein.desc} ({protein.pid})",
            font=dict(size=16),
        ),
        height=total_height,
        barmode='overlay',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            title=dict(text=''),
            orientation='v',
            yanchor='top',
            y=0.98,
            xanchor='left',
            x=1.03,
            font=dict(size=11),
            tracegroupgap=10,
            groupclick='toggleitem',
        ),
        margin=dict(t=80, b=30, l=30, r=220),
    )

    return fig.to_dict()
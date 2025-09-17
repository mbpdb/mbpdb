from django.shortcuts import render
import os, re, subprocess
from .toolbox import func_list, clear_temp_directory, spec_list, pro_list, run_pepex, add_proteins, pepdb_add_csv, get_latest_peptides

from subprocess import CalledProcessError
from .models import Counter
from django.utils import timezone
from django.http import FileResponse, HttpResponse, JsonResponse
from django.conf import settings
from django.urls import reverse

from celery.result import AsyncResult
from celery.app.control import Inspect
from peptide.celery import app

from .tasks import pepdb_multi_search_manual
from django.core.cache import cache


from django.shortcuts import render

def voila_heatmap_view(request):
    return render(request, 'peptide/heatmap.html')

def voila_data_view(request):
    return render(request, 'peptide/data_transform.html')

def voila_data_analysis_view(request):
    return render(request, 'peptide/data_analysis_plot.html')

#def voila_protein_bar_view(request):
#    return render(request, 'peptide/protein_bar_plot.html')

#def voila_bioactive_bar_view(request):
#    return render(request, 'peptide/bioactive_bar_plot.html')
#def voila_summed_bar_view(request):
#    return render(request, 'peptide/summed_bar_plot.html')

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
                         'errors': errors})

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
        # Calculate estimated time remaining in seconds
        if progress > 0:
            percent_progress = progress / size * 100

            total_estimated_time = elapsed_time / percent_progress
        else:
            percent_progress = 0.0

        return JsonResponse({
            'task_id': task_id,
            'percent_progress': percent_progress,
            'progress': progress,
            'size': size,
            'elapsed_time': elapsed_time,
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
        # Ensure task_result.info is a dictionary
        response_data = {
            'status': task_result.status,
            'progress': task_result.info.get('progress', 0),
            'elapsed_time': task_result.info.get('elapsed_time', 0),
        }
        return JsonResponse(response_data)

#Returns results of search to results_section html page
def return_render_results(request, task_id):
    if request.method == 'GET':
        q = get_latest_peptides(1)
        combined_results = []
        task_id_str = str(task_id)
        task_result = AsyncResult(task_id_str)
        if task_result.ready():
            result_data = task_result.result

            results = result_data.get('results', [])
            formated_header = result_data.get('formated_header', [])
            output_path = result_data.get('output_path', '')
            results_headers = result_data.get('results_headers', [])

            FileResponse(open(output_path, 'rb'))

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
                    peptide = item['data'].get('Peptide&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp', None)
                    species = item['data'].get('Species&nbsp&nbsp&nbsp&nbsp', None)
                    function = item['data'].get(
                        'Function&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp',
                        None)
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
            return render(request, 'peptide/results_section.html', {
                'data': request.POST,
                'peptide_option': peptide_option,
                'matrix': matrix,
                'latest_peptides': q,
                'description_to_pid': description_to_pid,
                'functions': unique_func,
                'common_to_sci_list': common_to_sci,
            })

def start_work(request):
    #peptide_search(request)
    #task = pepdb_multi_search_manual.delay('', '', '', '', '', '', '', '', '')
    #task_id = task.id  # Extiract the task ID from the AsyncResult
    print("task_result", task)  # This will print the AsyncResult object
    print(f"Task ID: {task_id}")  # This will print the task ID

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
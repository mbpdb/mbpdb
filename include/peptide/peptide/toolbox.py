import subprocess, os, shutil, time, csv, re, sys
import pandas as pd
from django.conf import settings
from .models import PeptideInfo, Reference, Function, ProteinInfo, Submission, ProteinVariant
from datetime import datetime
from django.contrib.auth.models import User
from chardet.universaldetector import UniversalDetector
from django.db.models import Count
from django.http import HttpResponse
from Bio import SeqIO
from pathlib import Path
from collections import defaultdict
from django.db.models import Q



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
    work_path = create_work_directory(settings.WORK_DIRECTORY)
    input_file_path = os.path.join(work_path, csv_file.name).replace(' ','_')
    handle_uploaded_file(csv_file, input_file_path)
    records = 0

    # Handle file based on extension
    file_extension = os.path.splitext(csv_file.name)[1].lower()
    
    if file_extension == '.xlsx':
        try:
            df = pd.read_excel(input_file_path)
            # Convert DataFrame to list of dictionaries
            data = df.to_dict('records')
            # Convert all values to strings and strip whitespace, handle NaN values
            data = [{k: str(v).strip() if pd.notna(v) else '' for k, v in row.items()} for row in data]
        except Exception as e:
            raise subprocess.CalledProcessError(1, cmd="", output=f"Error reading Excel file: {str(e)}")
    else:  # .tsv file
        csv.register_dialect('pep_dialect', delimiter='\t')
        
        # remove weird characters from end of fields
        temp_file = os.path.join(work_path, "temp.csv")
        subprocess.check_output(['dos2unix','-q',input_file_path], stderr=subprocess.STDOUT)
        subprocess.check_output([settings.FIX_WEIRD_CHARS,input_file_path,temp_file], stderr=subprocess.STDOUT)
        subprocess.check_output(['mv',temp_file,input_file_path], stderr=subprocess.STDOUT)

        # detecting file encoding
        detector = UniversalDetector()
        for line in open(input_file_path, 'rb'):
            detector.feed(line)
            if detector.done: break
        detector.close()

        # if file is not UTF-8, attempt to recode to UTF-8
        if detector.result['encoding'].lower() != "utf-8":
            subprocess.check_output(['recode',detector.result['encoding']+'..UTF-8',input_file_path], stderr=subprocess.STDOUT)

        try:
            with open(input_file_path, 'r', encoding='utf-8') as pepfile:
                reader = csv.DictReader(pepfile, dialect='pep_dialect')
                data = list(reader)
        except UnicodeDecodeError:
            raise subprocess.CalledProcessError(1, cmd="", output="Error: File needs to use Unicode (UTF-8) encoding. Conversion failed.")

    # Validate headers
    headers = list(data[0].keys())
    headers = list(filter(None, headers))  # remove empty column headers
    headers.sort()

    required_headers = ['abstract', 'additional_details', 'authors', 'doi', 'function', 'ic50', 
                       'inhibited_microorganisms', 'inhibition_type', 'peptide', 'proteinID', 'ptm', 'title']
    required_headers.sort()

    if headers != required_headers:
        raise subprocess.CalledProcessError(1, cmd="", 
            output="Error: Input file does not have the correct headers (proteinID, peptide, function, 'additional_details', 'ic50' , 'inhibition_type','inhibited_microorganisms', ptm, title, authors, abstract, and doi).")

    err = 0
    count = 0
    tn = datetime.now()
    
    for row in data:
        rownum = count + 2  # +2 because Excel/CSV files typically start at row 2 (after header)

        # Validate required fields
        if (row['peptide']=='' or row['proteinID']=='' or row['function']=='' or row['title']=='' or row['authors']=='' or row['doi']==''):
            messages.append("Error: Line "+str(rownum)+" in file has values that cannot be empty (only abstract, additional_details, ic50 , inhibition_type, inhibited_microorganisms, and ptm can be empty).")
            err+=1
            continue

        # Check if protein exists
        idcheck = ProteinInfo.objects.filter(pid=row['proteinID']).first()
        if idcheck is None:
            messages.append("Error: Protein ID " + row['proteinID'] + " not found in database (Line " + str(rownum) + "). Skipping. You can use the Add Fasta Files tool to add the protein to the database.")
            err += 1
            continue

        # Check if peptide exists in protein or variants
        prot = idcheck.seq
        intervals = ', '.join([str(m.start()+1) + "-" + str(m.start()+len(row['peptide'])) for m in re.finditer(row['peptide'], prot)])
        pvid_list = []

        if not intervals:
            gv_check = ProteinVariant.objects.filter(protein=idcheck)
            for pv in gv_check:
                intervals = ', '.join(
                    [str(m.start() + 1) + "-" + str(m.start() + len(row['peptide'])) for m in
                     re.finditer(row['peptide'], pv.seq)])
                if intervals:
                    pvid_list.append(pv.pvid)
            if not pvid_list:
                messages.append(f"Error: Peptide sequence '{row['peptide']}' was not found in protein ID {row['proteinID']} or any of its variants. This occurred in line {rownum} of your input file.")
                err += 1
                continue

        # Check and handle the ic50 value
        ic50_value = None
        if row['ic50'] and row['ic50'].strip():
            try:
                ic50_value = float(row['ic50'])
            except ValueError:
                messages.append(f"Warning: Invalid IC50 value '{row['ic50']}' in line {rownum}. Setting to null.")
                ic50_value = None

        # If we get here, the entry is valid - create the submission
        sub = Submission(protein_id=row['proteinID'], 
                        peptide=row['peptide'], 
                        function=row['function'], 
                        additional_details=row['additional_details'], 
                        ic50=ic50_value, 
                        inhibition_type=row['inhibition_type'],
                        inhibited_microorganisms=row['inhibited_microorganisms'], 
                        ptm=row['ptm'], 
                        title=row['title'], 
                        authors=row['authors'], 
                        abstract=row['abstract'], 
                        doi=row['doi'], 
                        intervals=intervals, 
                        protein_variants=','.join(pvid_list), 
                        length=len(row['peptide']), 
                        time_submitted=tn)
        sub.save()
        count += 1

    if file_extension == '.tsv' and detector.result['encoding'].lower() != "utf-8":
        messages.append("Warning: Detected encoding for input file was not UTF-8 (It was detected as "+detector.result['encoding']+"). Recoding was attempted but if this is not the correct original encoding, then non-standard characters may not have been recoded correctly.")
    
    if count > 0:
        messages.append(f"Successfully added {count} entries to the database.")
    if err > 0:
        errbit = "errors" if err > 1 else "error"
        messages.append(f"{err} {errbit} were found and those entries were skipped.")

    return messages

def pepdb_approve(queryset):
    messages = []
    records = 0

    for e in queryset:
        try:
            idcheck = ProteinInfo.objects.get(pid=e.protein_id)
        except ProteinInfo.DoesNotExist:
            messages.append(
                f"Error: Protein ID {e.protein_id} not found in database for peptide {e.peptide}. Skipping. You can use the Add Fasta Files tool to add the protein to the database.")
            continue
        try:
            pepcheck = PeptideInfo.objects.get(peptide=e.peptide)
        except PeptideInfo.DoesNotExist:
            tn = datetime.now()
            pepinfo = PeptideInfo(peptide=e.peptide, protein_variants=e.protein_variants, protein=idcheck, length=e.length, intervals=e.intervals, time_approved=tn)
            pepinfo.save()
            f = Function(pep=pepinfo, function=e.function)
            f.save()
            r = Reference(func=f, title=e.title, authors=e.authors, abstract=e.abstract, doi=e.doi,additional_details=e.additional_details, ic50=e.ic50, inhibition_type=e.inhibition_type, inhibited_microorganisms=e.inhibited_microorganisms, ptm=e.ptm)
            r.save()
            records = records + 1
            e.delete()
            continue

        try:
            fcheck = Function.objects.get(pep=pepcheck, function=e.function)
        except Function.DoesNotExist:
            f = Function(pep=pepcheck, function=e.function)
            f.save()
            r = Reference(func=f, title=e.title, authors=e.authors, abstract=e.abstract, doi=e.doi,
                          additional_details=e.additional_details, ic50=e.ic50, inhibition_type=e.inhibition_type,
                          inhibited_microorganisms=e.inhibited_microorganisms, ptm=e.ptm)
            r.save()
            records = records + 1
            e.delete()
            continue

        try:
            doi_check = Reference.objects.get(func=fcheck, doi=e.doi)
            if (doi_check.additional_details != '' and e.additional_details != '') or (doi_check.ptm != '' and e.ptm != ''):
                if doi_check.additional_details != '' and e.additional_details != '':
                    doi_check.additional_details = e.additional_details
                    doi_check.save()
                    messages.append("Peptide "+e.peptide+" with Function '"+e.function+"' and DOI '"+e.doi+"' found. Updated additional details to '"+e.additional_details+"'.")

                if doi_check.ptm != '' and e.ptm != '':
                    doi_check.ptm = e.ptm
                    doi_check.save()
                    messages.append("Peptide "+e.peptide+" with Function '"+e.function+"' and DOI '"+e.doi+"' found. Updated PTM to '"+e.ptm+"'.")

                e.delete()
                records = records + 1
                continue
        except Reference.DoesNotExist:
            r = Reference(func=fcheck, title=e.title, authors=e.authors, abstract=e.abstract, doi=e.doi, additional_details=e.additional_details, ic50=e.ic50, inhibition_type=e.inhibition_type,
                          inhibited_microorganisms=e.inhibited_microorganisms, ptm=e.ptm)
            r.save()
            records = records + 1
            e.delete()
            continue

        messages.append("Warning: Peptide "+e.peptide+" with Function '"+e.function+"' and DOI '"+e.doi+"' already exists in DB.")
        e.delete()
        continue

    messages.append("Added "+str(records)+" submissions to database.")
    return messages

# This function appends the data to the list, prepending it with a title number if there is more than one entry.
def append_with_titnum(data_list, data, titnum):
    if len(data_list) > 0:
        data_list.append(f"<b>{titnum})</b> {data}")
        if not data_list[0].startswith('<b>1)</b>'):
            data_list[0] = f"<b>1)</b> {data_list[0]}"
    else:
        data_list.append(data)

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
                    messages.append(
                        "Warning: Header '" + seq_record.description + "' not parseable. Skipping fasta record.")
                    continue
                protid = m.group(1)
                prot_desc = m.group(2)
                prot_species = m.group(3)

                gvid = ''
                gv = re.search("GV=(.+?)\s*$", seq_record.description)
                if gv:
                    gvid = gv.group(1)

                protein_exists = ProteinInfo.objects.filter(pid=protid).exists()

                if not protein_exists:
                    if not gvid:
                        protinfo = ProteinInfo(header=seq_record.description, pid=protid, seq=seq_record.seq,
                                               desc=prot_desc, species=prot_species)
                        protinfo.save()
                        count = count + 1
                    else:
                        messages.append(
                            "Error: Protein ID " + protid + " not found for variant " + gvid + ". You must first add the original protein before adding variants.")
                else:
                    if gvid:
                        gv_check = ProteinVariant.objects.filter(protein__pid=protid, pvid=gvid)
                        if gv_check.count() > 0:
                            messages.append("Variant " + gvid + " already exists for protein " + protid + ". Skipping.")
                        else:
                            # Assuming the relationship is ForeignKey; thus, using 'first()' to get the ProteinInfo instance
                            idcheck = ProteinInfo.objects.filter(pid=protid).first()
                            pv = ProteinVariant(seq=seq_record.seq, pvid=gvid, protein=idcheck)
                            pv.save()
                            count = count + 1
                    else:
                        messages.append(
                            "Protein ID " + protid + " already exists (and sequence is not a variant). Skipping.")
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

def xlsx_to_tsv(path):
    (root,ext) = os.path.splitext(path)
    tsv_path = root + '.tsv'
    #This is NOISY!  Ignore output.
    subprocess.call('%s "%s" "%s" 2> /dev/null' % (settings.XLS_TO_TSV,path,tsv_path),shell=True)
    return tsv_path
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
    unique_func = sorted([func['function'] for func in functions])

    return unique_func

#Added RK 8/22/23 returns list of species to the html page from settings.translatelist
def spec_list(request):
    common_to_sci = {}
    for entry in settings.SPEC_TRANSLATE_LIST:
        common_name, sci_name = entry
        if common_name in common_to_sci:
            common_to_sci[common_name].append(sci_name)
        else:
            common_to_sci[common_name] = [sci_name]

    return common_to_sci

#function that exports the entire database for download by user
def export_database(request):

    full_db_export = (
        PeptideInfo.objects
        .select_related('protein')  # JOIN with ProteinInfo
        .prefetch_related('functions', 'functions__references')  # LEFT JOIN with Function and Reference
        .values(
            'peptide', 'protein_id', 'protein__desc', 'protein__species', 'intervals',
            'functions__function', 'functions__references__additional_details',
            'functions__references__ic50','functions__references__inhibition_type',
            'functions__references__inhibited_microorganisms',
            'functions__references__ptm', 'functions__references__title',
            'functions__references__authors', 'functions__references__abstract',
            'functions__references__doi'
        )
        .order_by('protein__desc')  # Order by 'protein__desc' in ascending alphabetical order
    )
    # Create a mapping from protein_id to pid
    protein_id_to_pid = {protein.id: protein.pid for protein in ProteinInfo.objects.all()}

    # Create an HttpResponse object with appropriate CSV headers.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="database.tsv"'

    writer = csv.writer(response, delimiter='\t')  # Use tab delimiter for TSV
    # Write header
    writer.writerow([
        'peptide', 'protein_pid', 'protein_desc', 'protein_species', 'intervals',
        'function', 'additional_details', 'ic50', 'inhibition_type', 'inhibited_microorganisms','ptm', 'title', 'authors', 'abstract', 'doi'
    ])

    # Write actual rows
    for row in full_db_export:
        writer.writerow([
            row.get('peptide', ''),
            protein_id_to_pid.get(row.get('protein_id', ''), ''),  # Convert protein_id to pid
            row.get('protein__desc', ''),
            row.get('protein__species', ''),
            row.get('intervals', ''),
            row.get('functions__function', ''),
            row.get('functions__references__additional_details', ''),
            row.get('functions__references__ic50', ''),
            row.get('functions__references__inhibition_type', ''),
            row.get('functions__references__inhibited_microorganisms', ''),
            row.get('functions__references__ptm', ''),
            row.get('functions__references__title', ''),
            row.get('functions__references__authors', ''),
            row.get('functions__references__abstract', ''),
            row.get('functions__references__doi', '')
        ])

    return response

#Function clears the temp directory at the onset of peptide_search in views.py
def clear_temp_directory(directory_path):
    # Get all directories in the path
    dirs = [f for f in os.scandir(directory_path) if f.is_dir()]

    # Sort the directories by modification time, most recent first
    dirs.sort(key=lambda x: os.path.getmtime(x.path), reverse=True)

    # Keep the 10 most recent directories, delete the rest
    for dir_entry in dirs[25:]:
        try:
            shutil.rmtree(dir_entry.path)
        except Exception as e:
            pass  # Handle or log the exception as needed

# init db to git repo
def git_init(modeladmin, request, queryset):
    # Fetch GITHUB_PAT from environment variables
    github_pat = os.environ.get("GITHUB_PAT")

    try:
        if not github_pat:
            modeladmin.message_user(request, "GITHUB_PAT environment variable is not set.")
            return

        # Initialize Git if it's not already initialized
        subprocess.run(["git", "init"], check=True)

        # Configure Git user
        subprocess.run(["git", "config", "--global", "user.email", "contact-mbpdb@oregonstate.edu"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "Rusty"], check=True)

        # Add the directory to the safe directory list
        subprocess.run(["git", "config", "--global", "--add", "safe.directory", "/app/include/peptide"], check=True)

        remote_url = f"https://{github_pat}@github.com/mbpdb/mbpdb.git"
        # Check if 'origin' remote exists
        result = subprocess.run(["git", "remote"], capture_output=True, text=True)
        if "origin" in result.stdout.split():
            subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)
        else:
            subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
        # Fetch origin
        subprocess.run(["git", "fetch", "origin"], check=True)

        # switch to main branch
        # subprocess.run(["git", "clean", "-f", "-d"], check=True)
        #subprocess.run(["git", "checkout", "main"], check=True)

        # Run Django migrations to ensure all tables exist
        #subprocess.run(["python3", "manage.py", "migrate"], check=True)

        modeladmin.message_user(request, "Git init and migrate were successful.")
        
    except Exception as e:
        modeladmin.message_user(request, f"Git init failed: {e}")

# pushes db to git repo
def git_push(modeladmin, request, queryset):
    try:
        # Adds and commits all changes, respecting .gitignore
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Updated db"], check=True)

        # Push changes to remote new branch
        subprocess.run(["git", "push", "origin", "main"], check=True)

        modeladmin.message_user(request, "Git push was successful.")

    except Exception as e:
        modeladmin.message_user(request, f"Git push failed: {e}")


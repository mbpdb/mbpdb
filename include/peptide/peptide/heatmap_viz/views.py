"""
Django views for the Heatmap Visualization web app.
"""
import json
import os
import uuid
import base64

import pandas as pd
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET, require_http_methods

from .services import data_processor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_work_dir(request) -> str:
    work_dir = request.session.get('hm_work_dir')
    if work_dir and os.path.isdir(work_dir):
        return work_dir
    work_dir = os.path.join('/tmp', 'hm_' + str(uuid.uuid4()))
    os.makedirs(work_dir, mode=0o777, exist_ok=True)
    request.session['hm_work_dir'] = work_dir
    return work_dir


def _save_df(work_dir: str, name: str, df: pd.DataFrame):
    df.to_pickle(os.path.join(work_dir, f'{name}.pkl'))


def _load_df(work_dir: str, name: str) -> pd.DataFrame | None:
    path = os.path.join(work_dir, f'{name}.pkl')
    return pd.read_pickle(path) if os.path.exists(path) else None


def _save_json(work_dir: str, name: str, data):
    with open(os.path.join(work_dir, f'{name}.json'), 'w') as f:
        json.dump(data, f)


def _load_json(work_dir: str, name: str):
    path = os.path.join(work_dir, f'{name}.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def index(request):
    return render(request, 'peptide/heatmap.html')


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

@require_POST
def upload(request):
    """
    Accept merged CSV + optional FASTA file.
    POST body: multipart with 'merged_file' and optionally 'fasta_file'.
    """
    merged_file = request.FILES.get('merged_file')
    if not merged_file:
        return JsonResponse({'error': 'No merged data file uploaded.'}, status=400)

    df, group_data_dict, protein_dict, col_order, err = data_processor.load_merged_file(
        merged_file, merged_file.name
    )
    if err:
        return JsonResponse({'error': f'Could not load file: {err}'}, status=400)

    # Optional FASTA file – update protein_dict with sequences
    fasta_file = request.FILES.get('fasta_file')
    fasta_msg = None
    if fasta_file:
        merged_pids = set(df['Protein'].unique()) if 'Protein' in df.columns else None
        fasta_proteins, fasta_err = data_processor.load_fasta_file(fasta_file, merged_pids)
        if fasta_err:
            fasta_msg = f'FASTA warning: {fasta_err}'
        else:
            for pid, pdata in fasta_proteins.items():
                if pid in protein_dict:
                    protein_dict[pid].update(pdata)
                else:
                    protein_dict[pid] = pdata

    work_dir = _get_work_dir(request)
    _save_df(work_dir, 'merged_df', df)
    _save_json(work_dir, 'group_data_dict', group_data_dict)
    _save_json(work_dir, 'protein_dict', protein_dict)
    _save_json(work_dir, 'col_order', col_order)

    options = data_processor.get_selector_options(df, group_data_dict, protein_dict, col_order)

    warnings = []
    if fasta_msg:
        warnings.append(fasta_msg)

    return JsonResponse({
        'success': True,
        'filename': merged_file.name,
        'rows': len(df),
        'proteins': options['proteins'],
        'var_keys': options['var_keys'],
        'has_functions': options['has_functions'],
        'warnings': warnings,
    })


# ---------------------------------------------------------------------------
# Transfer from Data Transformation
# ---------------------------------------------------------------------------

@require_POST
def transfer_from_dt(request):
    """Load merged_df directly from the data transformation session."""
    import io
    dt_work_dir = request.session.get('dt_work_dir')
    if not dt_work_dir or not os.path.isdir(dt_work_dir):
        return JsonResponse(
            {'error': 'No data transformation session found. Please complete data transformation first.'},
            status=400,
        )
    dt_pkl = os.path.join(dt_work_dir, 'merged_df.pkl')
    if not os.path.exists(dt_pkl):
        return JsonResponse(
            {'error': 'No processed data found. Please click "Process Data" in the wizard first.'},
            status=400,
        )

    df = pd.read_pickle(dt_pkl)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    df_hm, group_data_dict, protein_dict, col_order, err = data_processor.load_merged_file(buf, 'merged_df.csv')
    if err:
        return JsonResponse({'error': f'Could not process data: {err}'}, status=400)

    work_dir = _get_work_dir(request)
    _save_df(work_dir, 'merged_df', df_hm)
    _save_json(work_dir, 'group_data_dict', group_data_dict)
    _save_json(work_dir, 'protein_dict', protein_dict)
    _save_json(work_dir, 'col_order', col_order)

    options = data_processor.get_selector_options(df_hm, group_data_dict, protein_dict, col_order)
    return JsonResponse({
        'success': True,
        'filename': 'Data Transformation output',
        'rows': len(df_hm),
        'proteins': options['proteins'], 'var_keys': options['var_keys'],
        'has_functions': options['has_functions'], 'warnings': [],
    })


# ---------------------------------------------------------------------------
# Transfer from Data Analysis
# ---------------------------------------------------------------------------

@require_POST
def transfer_from_da(request):
    """Load merged_df directly from the data analysis session."""
    import io
    da_work_dir = request.session.get('da_work_dir')
    if not da_work_dir or not os.path.isdir(da_work_dir):
        return JsonResponse(
            {'error': 'No data analysis session found. Please upload a file in Data Analysis first.'},
            status=400,
        )
    da_pkl = os.path.join(da_work_dir, 'merged_df.pkl')
    if not os.path.exists(da_pkl):
        return JsonResponse(
            {'error': 'No processed data found in Data Analysis session.'},
            status=400,
        )

    df = pd.read_pickle(da_pkl)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    df_hm, group_data_dict, protein_dict, col_order, err = data_processor.load_merged_file(buf, 'merged_df.csv')
    if err:
        return JsonResponse({'error': f'Could not process data: {err}'}, status=400)

    work_dir = _get_work_dir(request)
    _save_df(work_dir, 'merged_df', df_hm)
    _save_json(work_dir, 'group_data_dict', group_data_dict)
    _save_json(work_dir, 'protein_dict', protein_dict)
    _save_json(work_dir, 'col_order', col_order)

    options = data_processor.get_selector_options(df_hm, group_data_dict, protein_dict, col_order)
    return JsonResponse({
        'success': True,
        'filename': 'Data Analysis output',
        'rows': len(df_hm),
        'proteins': options['proteins'], 'var_keys': options['var_keys'],
        'has_functions': options['has_functions'], 'warnings': [],
    })


# ---------------------------------------------------------------------------
# Fetch protein sequence (UniProt)
# ---------------------------------------------------------------------------

@require_POST
def fetch_sequence(request):
    """
    Fetch sequence for a protein from UniProt if not already available.
    POST body (JSON): {"protein_id": "P12345"}
    """
    try:
        body = json.loads(request.body)
        protein_id = body.get('protein_id', '').strip()
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    if not protein_id:
        return JsonResponse({'error': 'protein_id required.'}, status=400)

    work_dir = request.session.get('hm_work_dir')
    if not work_dir:
        return JsonResponse({'error': 'No session. Please upload a file first.'}, status=400)

    protein_dict = _load_json(work_dir, 'protein_dict') or {}

    # Already have sequence?
    existing = protein_dict.get(protein_id, {})
    if existing.get('sequence'):
        return JsonResponse({'success': True, 'cached': True, 'protein_id': protein_id})

    seq = data_processor.fetch_sequence_from_uniprot(protein_id)
    if not seq:
        return JsonResponse({'error': f'Could not fetch sequence for {protein_id}.'}, status=404)

    protein_dict.setdefault(protein_id, {})['sequence'] = seq
    _save_json(work_dir, 'protein_dict', protein_dict)

    return JsonResponse({
        'success': True, 'cached': False,
        'protein_id': protein_id, 'length': len(seq),
    })


# ---------------------------------------------------------------------------
# Get specific options (for bio_or_pep dropdown)
# ---------------------------------------------------------------------------

@require_POST
def get_specific_options(request):
    """
    Return options for specific_select_multiple based on bio_or_pep value.
    POST body (JSON): {"bio_or_pep": "2", "selected_proteins": [...]}
    """
    try:
        body = json.loads(request.body)
        bio_or_pep = body.get('bio_or_pep', 'no')
        selected_proteins = body.get('selected_proteins', [])
        selected_var_keys = body.get('selected_var_keys', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    work_dir = request.session.get('hm_work_dir')
    if not work_dir:
        return JsonResponse({'error': 'No session. Please upload a file first.'}, status=400)

    merged_df = _load_df(work_dir, 'merged_df')
    if merged_df is None:
        return JsonResponse({'error': 'Session data missing.'}, status=400)

    options = data_processor.get_specific_options(
        merged_df, bio_or_pep,
        selected_proteins or None,
        selected_var_keys or None,
    )
    return JsonResponse({'options': options})


# ---------------------------------------------------------------------------
# Plot endpoint
# ---------------------------------------------------------------------------

@require_POST
def plot(request):
    """
    Generate heatmap images.
    POST body (JSON): {selected_proteins, selected_var_keys, plot_params}
    Returns base64 PNG images.
    """
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    work_dir = request.session.get('hm_work_dir')
    if not work_dir:
        return JsonResponse({'error': 'No session. Please upload a file first.'}, status=400)

    merged_df = _load_df(work_dir, 'merged_df')
    group_data_dict = _load_json(work_dir, 'group_data_dict')
    protein_dict = _load_json(work_dir, 'protein_dict')

    if merged_df is None or group_data_dict is None:
        return JsonResponse({'error': 'Session data missing. Please re-upload your file.'}, status=400)

    selected_proteins = body.get('selected_proteins', [])
    selected_var_keys = body.get('selected_var_keys', [])
    plot_params = body.get('plot_params', {})

    if not selected_proteins or not selected_var_keys:
        return JsonResponse({'error': 'Please select at least one protein and one variable.'}, status=400)

    # Check sequences – if missing, report which need fetching
    missing_seqs = [
        pid for pid in selected_proteins
        if not protein_dict.get(pid, {}).get('sequence', '')
    ]
    if missing_seqs:
        return JsonResponse({
            'error': 'Missing protein sequences.',
            'missing_sequences': missing_seqs,
            'message': (
                f'Sequences for {", ".join(missing_seqs)} are not available. '
                'Please upload a FASTA file or enable UniProt lookup.'
            ),
        }, status=422)

    # Build available_data_variables_dict
    available, build_msgs = data_processor.build_available_data_variables(
        merged_df, protein_dict, group_data_dict,
        selected_proteins, selected_var_keys,
    )

    if not available:
        return JsonResponse({
            'error': 'Could not build plot data.',
            'messages': build_msgs,
        }, status=400)

    # Generate heatmap
    portrait_b64, landscape_b64, compact_json, \
        portrait_interactive, landscape_interactive, plot_msgs = data_processor.generate_heatmap(
            available, plot_params
        )

    all_msgs = build_msgs + plot_msgs

    if portrait_b64 is None and landscape_b64 is None and compact_json is None \
            and portrait_interactive is None and landscape_interactive is None:
        return JsonResponse({
            'error': 'No heatmap generated.',
            'messages': all_msgs,
        }, status=400)

    return JsonResponse({
        'success': True,
        'portrait':              portrait_b64,
        'landscape':             landscape_b64,
        'compact':               compact_json,
        'portrait_interactive':  portrait_interactive,
        'landscape_interactive': landscape_interactive,
        'messages': all_msgs,
    })


# ---------------------------------------------------------------------------
# Save / download compact interactive plot as HTML
# ---------------------------------------------------------------------------

@require_POST
def save_compact_plot(request):
    """Save a client-generated compact plot HTML to the session work dir."""
    try:
        data = json.loads(request.body)
        html_content = data.get('html', '')
    except Exception:
        return JsonResponse({'error': 'Invalid body.'}, status=400)

    if not html_content:
        return JsonResponse({'error': 'No HTML content provided.'}, status=400)

    work_dir = _get_work_dir(request)
    plot_path = os.path.join(work_dir, 'compact_plot.html')
    with open(plot_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return JsonResponse({'success': True})


@require_GET
def download_compact_plot(request):
    """Return the previously saved compact plot as a self-contained HTML file."""
    work_dir = request.session.get('hm_work_dir')
    if not work_dir:
        return HttpResponse('No session data found.', status=400)

    plot_path = os.path.join(work_dir, 'compact_plot.html')
    if not os.path.exists(plot_path):
        return HttpResponse('No compact plot has been generated yet.', status=404)

    with open(plot_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="heatmap_compact.html"'
        return response


# ---------------------------------------------------------------------------
# Download plot as PNG
# ---------------------------------------------------------------------------

@require_POST
def download_plot(request):
    """
    Accept base64 PNG from frontend, decode, return as file attachment.
    POST body (JSON): {"image_b64": "...", "orientation": "portrait"}
    """
    try:
        body = json.loads(request.body)
        b64 = body.get('image_b64', '')
        orientation = body.get('orientation', 'portrait')
    except Exception:
        return HttpResponse('Invalid request.', status=400)

    if not b64:
        return HttpResponse('No image data.', status=400)

    img_bytes = base64.b64decode(b64)
    filename = f'heatmap_{orientation}.png'
    response = HttpResponse(img_bytes, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

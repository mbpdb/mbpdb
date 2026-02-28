"""
Shared UI utility functions used across heatmap_visualization and data_analysis notebooks.

Importing this module does NOT trigger matplotlib or plotly — all heavy-library
usage stays inside the notebook methods that invoke these helpers.
"""

import os
import base64
import pandas as pd
from IPython.display import display, HTML
import ipywidgets as widgets


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------

def safe_concat(dfs, **kwargs):
    """Safely concatenate DataFrames, dropping all-NA columns before merging."""
    if not dfs:
        return pd.DataFrame()

    cleaned_dfs = []
    for df in dfs:
        if isinstance(df, pd.DataFrame) and not df.empty:
            df = df.dropna(axis=1, how='all')
            cleaned_dfs.append(df)

    if not cleaned_dfs:
        return pd.DataFrame()

    common_cols = set.intersection(*[set(df.columns) for df in cleaned_dfs])
    filtered_dfs = [df[list(common_cols)] for df in cleaned_dfs]
    return pd.concat(filtered_dfs, **kwargs)


def extract_non_zero_non_nan_values(df):
    """Return a flat list of all non-null, non-zero values from a DataFrame."""
    values = []
    for col in df.columns:
        col_values = pd.to_numeric(df[col], errors='coerce')
        col_values = col_values.dropna()
        col_values = col_values[col_values != 0]
        values.extend(col_values.tolist())
    return values


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def redact_string_descriptions(input_str, max_length=35):
    """Truncate a protein/function description to max_length characters."""
    if not isinstance(input_str, str):
        return str(input_str)
    if len(input_str) <= max_length:
        return input_str
    return input_str[:max_length - 3] + '...'


# ---------------------------------------------------------------------------
# Download link helpers
# ---------------------------------------------------------------------------

def create_file_download_link(file_path, label):
    """
    Create an ipywidgets HTML download link for a file on disk.

    Returns a ``widgets.HTML`` anchor element, or an error widget if the
    file does not exist.
    """
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            content = f.read()
        b64_content = base64.b64encode(content).decode('utf-8')
        return widgets.HTML(f"""
            <a download="{os.path.basename(file_path)}"
               href="data:application/octet-stream;base64,{b64_content}"
               style="color: #0366d6; text-decoration: none; margin-left: 20px; font-size: 14px;">
                {label}
            </a>
        """)
    return widgets.HTML(f"""
        <span style="color: red; margin-left: 20px; font-size: 14px;">
            File "{file_path}" not found!
        </span>
    """)


def generate_auto_download_link(content, filename, filetype='text/csv'):
    """
    Generate an HTML snippet that immediately triggers a browser download.

    ``content`` may be a ``pd.DataFrame`` (converted to CSV) or a ``str``/``bytes``.
    Returns an HTML string (suitable for ``display(HTML(...))``).
    """
    if isinstance(content, pd.DataFrame):
        content = content.to_csv(index=False) if filetype == 'text/csv' else content.to_csv(index=True)
    if isinstance(content, str):
        content = content.encode()
    b64 = base64.b64encode(content).decode()
    return f"""
        <a id="download_link" href="data:{filetype};base64,{b64}"
           download="{filename}"
           style="display: none;">
            Download {filename}
        </a>
        <script>
            document.getElementById('download_link').click();
        </script>
    """


# ---------------------------------------------------------------------------
# UI widget helpers
# ---------------------------------------------------------------------------

def create_help_icon(tooltip_text):
    """Return an ipywidgets HTML question-circle icon with a tooltip."""
    icon_html = '<i class="fa fa-question-circle" style="color: #007bff;"></i>'
    return widgets.HTML(
        f'<div title="{tooltip_text}" style="display: inline-block; margin-left: 2px;">{icon_html}</div>'
    )


def display_warning(message):
    """Display a Bootstrap-styled warning banner inside the current Output context."""
    warning_html = f"""
    <div style='color: #856404; background-color: #fff3cd; border: 1px solid #ffeeba;
                border-radius: 4px; padding: 10px; margin: 10px 0;'>
        <strong>Warning:</strong> {message}
    </div>
    """
    display(HTML(warning_html))


# ---------------------------------------------------------------------------
# Custom widgets
# ---------------------------------------------------------------------------

class EllipsisSelectMultiple(widgets.SelectMultiple):
    """SelectMultiple that applies CSS ``text-overflow: ellipsis`` to long items."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dom_classes = ['ellipsis-select']
        display(HTML("""
        <style>
        .ellipsis-select select option {
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
        }
        </style>
        """))

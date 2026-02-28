"""
BaseDataTransformation — shared scaffolding for the DataTransformation classes
used in heatmap_visualization.ipynb and data_analysis.ipynb.

Both notebooks define their own DataTransformation subclass that extends this
base with notebook-specific logic (FASTA uploading, group extraction, etc.).
"""

import os
import io
import base64
import traceback
import pandas as pd
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets

from .ui_helpers import create_file_download_link


class BaseDataTransformation:
    """
    Minimal shared scaffold for DataTransformation classes.

    Provides:
    - ``create_download_link`` — file-on-disk → ``widgets.HTML`` anchor
    - ``_load_data``           — read CSV/TSV/XLSX from an upload widget file object
    - ``_display_status``      — show a styled status message in ``self.output_area``
    """

    # ------------------------------------------------------------------
    # Download link (delegates to ui_helpers for a single implementation)
    # ------------------------------------------------------------------

    def create_download_link(self, file_path, label):
        """Create a ``widgets.HTML`` download anchor for a file on disk."""
        return create_file_download_link(file_path, label)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _load_data(self, file_obj, required_columns, file_type):
        """
        Load a CSV, TSV, or XLSX file from an ipywidgets FileUpload file object.

        Parameters
        ----------
        file_obj : ipywidgets FileInfo
            The file entry from ``widgets.FileUpload.value[0]``.
        required_columns : list[str]
            Columns that must be present after loading.
        file_type : str
            Human-readable label used in error messages (e.g. ``"Merged"``).

        Returns
        -------
        tuple[pd.DataFrame | None, str]
            ``(dataframe, "yes")`` on success, ``(None, "no")`` on failure.
        """
        try:
            content = file_obj.content
            filename = file_obj.name
            extension = filename.split('.')[-1].lower()
            file_stream = io.BytesIO(content)

            if extension == 'csv':
                df = pd.read_csv(file_stream)
            elif extension in ('txt', 'tsv'):
                df = pd.read_csv(file_stream, delimiter='\t')
            elif extension == 'xlsx':
                df = pd.read_excel(file_stream)
            else:
                raise ValueError(f"Unsupported file format: .{extension}")

            df.columns = df.columns.str.strip()

            # Subclasses may override validate_and_standardize_columns
            if hasattr(self, 'validate_and_standardize_columns'):
                try:
                    df = self.validate_and_standardize_columns(df)
                except ValueError as e:
                    display(HTML(f'<b style="color:red;">{file_type} File Error: {e}</b>'))
                    return None, 'no'

            missing = set(required_columns) - set(df.columns)
            if missing:
                display(HTML(
                    f'<b style="color:red;">{file_type} File Error: '
                    f'Missing required columns: {", ".join(sorted(missing))}</b>'
                ))
                return None, 'no'

            return df, 'yes'

        except Exception as e:
            display(HTML(f'<b style="color:red;">{file_type} File Error: {str(e)}</b>'))
            return None, 'no'

    # ------------------------------------------------------------------
    # Status display helper
    # ------------------------------------------------------------------

    def _display_status(self, message, level='info'):
        """
        Show a styled status message inside ``self.output_area`` if it exists,
        otherwise fall through to a plain ``display(HTML(...))`` call.

        Parameters
        ----------
        message : str
            The message text (HTML allowed).
        level : str
            One of ``'info'`` (blue), ``'success'`` (green),
            ``'warning'`` (orange), ``'error'`` (red).
        """
        colour_map = {
            'info':    '#17a2b8',
            'success': '#28a745',
            'warning': '#ffc107',
            'error':   '#dc3545',
        }
        colour = colour_map.get(level, '#17a2b8')
        html = f'<b style="color:{colour};">{message}</b>'

        if hasattr(self, 'output_area') and self.output_area is not None:
            with self.output_area:
                display(HTML(html))
        else:
            display(HTML(html))

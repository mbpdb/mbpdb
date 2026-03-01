"""
Plotting service for the Data Analysis web app.
Extracted from data_analysis.ipynb Plotter class.
All functions take a DataAnalysisState object and return a Plotly Figure.
"""
import traceback

import numpy as np
import pandas as pd

from .data_processor import (
    DataAnalysisState,
    contains_function,
    get_color_sequence,
    get_single_color,
    redact_string_descriptions,
)


def _safe_log(val, fallback=1e-10):
    return np.log10(max(float(val), fallback))


# ---------------------------------------------------------------------------
# Title / label helpers
# ---------------------------------------------------------------------------

def _make_title(state: DataAnalysisState) -> str:
    title = state.plot_title
    if not title:
        parts = []
        if state.plot_filter not in ('No Filter',):
            if state.selected_proteins and state.plot_filter in ('Selected Protein(s)', 'Both'):
                parts.append('Filtered By: ' + ', '.join(state.selected_proteins[:3]))
            if state.selected_functions and state.plot_filter in ('Selected Function(s)', 'Both'):
                parts.append('Function: ' + ', '.join(state.selected_functions[:3]))
        title = ' | '.join(parts) if parts else 'Data Analysis'
    return title


# ---------------------------------------------------------------------------
# Plot 1: Total peptides (By Sample, No Filter, Absolute)
# ---------------------------------------------------------------------------

def plot_total_peptides(state: DataAnalysisState):
    import plotly.graph_objects as go

    data = state.total_peptide_results_dict
    if not data:
        return None

    first_color = get_single_color(state.color_scheme)
    use_log = state.log_transform
    groups = list(data.keys())

    abundances = [data[g]['total_Abundance'] for g in groups]
    counts = [data[g]['unique_peptides'] for g in groups]
    abundance_sems = [data[g]['abundance_sem'] for g in groups]
    count_sems = [data[g]['count_sem'] for g in groups]

    if use_log:
        abundances = [_safe_log(v) for v in abundances]
        counts = [_safe_log(v) for v in counts]
        abundance_sems = [
            data[g]['abundance_sem'] / (data[g]['total_Abundance'] * np.log(10))
            if data[g]['total_Abundance'] > 0 else 0
            for g in groups
        ]
        count_sems = [
            data[g]['count_sem'] / (data[g]['unique_peptides'] * np.log(10))
            if data[g]['unique_peptides'] > 0 else 0
            for g in groups
        ]
        y_prefix = 'Log<sub>10</sub> '
        tickfmt = '.2f'
    else:
        y_prefix = ''
        tickfmt = '.1e'

    COMMON_LAYOUT = dict(
        template='plotly_white',
        height=800, width=1000,
        margin=dict(t=100, l=100, r=100),
        showlegend=False,
        font=dict(color='black'),
    )
    AXIS_STYLE = dict(
        showline=True, linewidth=1, linecolor='black',
        mirror=False, gridcolor='lightgray', showgrid=True, zeroline=False,
    )

    if state.use_count:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=groups, y=counts, name='Peptide Count',
            marker=dict(color=first_color, line=dict(color='black', width=1)),
            error_y=dict(type='data', array=count_sems, visible=True,
                         thickness=1.5, width=4, color='#000000'),
        ))
        y_axis_title = f'{y_prefix}Unique Peptide Count'
        ticksuffix = ''
        fig.update_layout(
            **COMMON_LAYOUT,
            title=dict(text=_make_title(state), y=0.95, x=0.5, xanchor='center',
                       yanchor='top', font=dict(size=18, color='black')),
            xaxis=dict(title='Sample', **AXIS_STYLE, tickangle=-35,
                       title_font=dict(size=18, color='black'),
                       tickfont=dict(size=16, color='black')),
            yaxis=dict(title=y_axis_title, tickformat=tickfmt,
                       title_font=dict(size=18, color='black'),
                       tickfont=dict(size=16, color='black'), **AXIS_STYLE),
        )
    else:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=groups, y=abundances, name='Abundance',
            marker=dict(color=first_color, line=dict(color='black', width=1)),
            error_y=dict(type='data', array=abundance_sems, visible=True,
                         thickness=1.5, width=4, color='#000000'),
        ))
        y_axis_title = f'{y_prefix}Summed Abundance'
        fig.update_layout(
            **COMMON_LAYOUT,
            title=dict(text=_make_title(state), y=0.95, x=0.5, xanchor='center',
                       yanchor='top', font=dict(size=18, color='black')),
            xaxis=dict(title=state.xlabel or 'Sample', **AXIS_STYLE, tickangle=-35,
                       title_font=dict(size=18, color='black'),
                       tickfont=dict(size=16, color='black')),
            yaxis=dict(title=state.ylabel or y_axis_title, tickformat=tickfmt,
                       title_font=dict(size=18, color='black'),
                       tickfont=dict(size=16, color='black'), **AXIS_STYLE),
        )
    if use_log and getattr(state, 'y_axis_format', 'linear') == 'power':
        _power_ticks(fig)
    return fig


# ---------------------------------------------------------------------------
# Plot 2: Grouped bar plot
# ---------------------------------------------------------------------------

def create_grouped_bar_plot(state: DataAnalysisState):
    import plotly.graph_objects as go

    orientation = state.orientation
    plot_filter = state.plot_filter
    selected_groups = state.selected_groups
    use_count = state.use_count
    use_log = state.log_transform

    if orientation == 'By Function' or (orientation == 'By Sample' and plot_filter == 'Selected Function(s)'):
        if not state.function_distribution_dict:
            return None
        if orientation == 'By Sample':
            categories = selected_groups
            bar_groups = state.selected_functions
            color_seq = get_color_sequence(len(bar_groups), state.color_scheme)
            color_map = {item: color_seq[i] for i, item in enumerate(bar_groups)}
        else:
            categories = state.selected_functions
            bar_groups = selected_groups
            color_seq = get_color_sequence(len(selected_groups), state.color_scheme)
            color_map = {g: color_seq[i] for i, g in enumerate(selected_groups)}

        display_cats = [redact_string_descriptions(c) for c in categories]
        n_bars = len(bar_groups)
        bar_width = 0.8 / max(n_bars, 1)
        fig = go.Figure()

        for idx, bar_group in enumerate(bar_groups):
            x_pos = [i + (idx - n_bars / 2 + 0.5) * bar_width for i in range(len(categories))]
            values, hover = [], []
            disp_bg = redact_string_descriptions(bar_group)

            for cat in categories:
                if orientation == 'By Sample':
                    item, group = bar_group, cat
                else:
                    item, group = cat, bar_group

                entry = state.function_distribution_dict.get(item, {})
                if state.is_relative:
                    v = entry.get('count_relative' if use_count else 'abundance_relative', {}).get(group, 0)
                else:
                    v = entry.get('counts' if use_count else 'Abundance', {}).get(group, 0)
                if use_log:
                    v = _safe_log(v)
                values.append(v)
                hover.append(f"{item} / {group}: {v:.4g}")

            fig.add_trace(go.Bar(
                x=x_pos, y=values, name=disp_bg,
                marker=dict(color=color_map.get(bar_group, '#999'), line=dict(color='black', width=0.5)),
                width=bar_width * 0.9,
                hovertext=hover, hoverinfo='text',
            ))

        fig.update_layout(
            **_common_layout(state),
            xaxis=dict(tickvals=list(range(len(categories))), ticktext=display_cats,
                       tickangle=-35, title=state.xlabel or 'Category',
                       **_axis_style()),
            yaxis=dict(title=state.ylabel or ('Log<sub>10</sub> ' if use_log else '') + state.metric_name,
                       **_axis_style()),
            barmode='group',
            legend=dict(title=dict(text=state.legend_title or 'Item'),
                        font=dict(size=12)),
        )
        if use_log and getattr(state, 'y_axis_format', 'linear') == 'power':
            _power_ticks(fig)
        return fig

    elif orientation == 'By Protein' or (orientation == 'By Sample' and plot_filter == 'Selected Protein(s)'):
        if state.protein_df is None or state.protein_df.empty:
            return None
        df = state.protein_df
        if orientation == 'By Sample':
            categories = selected_groups
            bar_groups_list = list(df['Description'])
            color_seq = get_color_sequence(len(bar_groups_list), state.color_scheme)
            color_map = {item: color_seq[i] for i, item in enumerate(bar_groups_list)}
        else:
            categories = list(df['Description'])
            bar_groups_list = selected_groups
            color_seq = get_color_sequence(len(selected_groups), state.color_scheme)
            color_map = {g: color_seq[i] for i, g in enumerate(selected_groups)}

        display_cats = [redact_string_descriptions(c) for c in categories]
        n_bars = len(bar_groups_list)
        bar_width = 0.8 / max(n_bars, 1)
        fig = go.Figure()

        for idx, bar_group in enumerate(bar_groups_list):
            x_pos = [i + (idx - n_bars / 2 + 0.5) * bar_width for i in range(len(categories))]
            values, hover = [], []
            disp_bg = redact_string_descriptions(bar_group)

            for cat in categories:
                if orientation == 'By Sample':
                    item, group = bar_group, cat
                    col = f'Rel_Avg_{group}' if state.is_relative else f'Avg_{group}'
                    row = df[df['Description'] == item]
                    v = float(row[col].values[0]) if len(row) > 0 and col in row.columns else 0
                else:
                    item, group = cat, bar_group
                    col = f'Rel_Avg_{group}' if state.is_relative else f'Avg_{group}'
                    row = df[df['Description'] == item]
                    v = float(row[col].values[0]) if len(row) > 0 and col in row.columns else 0
                if use_log:
                    v = _safe_log(v)
                values.append(v)
                hover.append(f"{item} / {group}: {v:.4g}")

            fig.add_trace(go.Bar(
                x=x_pos, y=values, name=disp_bg,
                marker=dict(color=color_map.get(bar_group, '#999'), line=dict(color='black', width=0.5)),
                width=bar_width * 0.9,
                hovertext=hover, hoverinfo='text',
            ))

        fig.update_layout(
            **_common_layout(state),
            xaxis=dict(tickvals=list(range(len(categories))), ticktext=display_cats,
                       tickangle=-35, title=state.xlabel or 'Category', **_axis_style()),
            yaxis=dict(title=state.ylabel or ('Log<sub>10</sub> ' if use_log else '') + state.metric_name,
                       **_axis_style()),
            barmode='group',
            legend=dict(title=dict(text=state.legend_title or 'Item'), font=dict(size=12)),
        )
        if use_log and getattr(state, 'y_axis_format', 'linear') == 'power':
            _power_ticks(fig)
        return fig

    elif plot_filter in ('No Filter', 'Both') and orientation == 'By Sample':
        # Total peptide absolute
        return plot_total_peptides(state)

    return None


# ---------------------------------------------------------------------------
# Plot 3: Stacked bar plot
# ---------------------------------------------------------------------------

def plot_stacked_bar_scaled(state: DataAnalysisState):
    import plotly.graph_objects as go

    selected_groups = state.selected_groups
    use_count = state.use_count
    use_log = state.log_transform
    plot_filter = state.plot_filter
    orientation = state.orientation

    # Determine data source
    if plot_filter in ('Selected Function(s)', 'Functional vs Non-Functional Peptides'):
        df = state.function_df
        items_col = 'Description'
        selected_items = state.selected_functions
    elif plot_filter == 'Selected Protein(s)':
        df = state.protein_df
        items_col = 'Description'
        selected_items = state.selected_proteins
    elif plot_filter == 'No Filter':
        # Fall back to total peptides stacked by group (one bar per group with sub-groupings)
        df = None
        selected_items = selected_groups
    else:
        df = state.function_df
        items_col = 'Description'
        selected_items = state.selected_functions

    if df is None or (hasattr(df, 'empty') and df.empty):
        return plot_total_peptides(state)

    color_seq = get_color_sequence(len(selected_items), state.color_scheme)
    color_map = {item: color_seq[i] for i, item in enumerate(selected_items)}
    if state.plot_minor and 'Minor Functions' in (state.function_distribution_dict or {}):
        color_map['Minor Functions'] = '#808080'

    fig = go.Figure()

    if orientation == 'By Sample':
        for i, item in enumerate(selected_items):
            row = df[df[items_col] == item] if df is not None else pd.DataFrame()
            values = []
            for g in selected_groups:
                if df is None or row.empty:
                    values.append(0)
                else:
                    col = (f'Rel_Count_{g}' if state.is_relative else f'Count_{g}') if use_count else \
                          (f'Rel_Avg_{g}' if state.is_relative else f'Avg_{g}')
                    v = float(row[col].values[0]) if col in row.columns else 0
                    if use_log:
                        v = _safe_log(v)
                    values.append(v)

            disp_name = redact_string_descriptions(item)
            fig.add_trace(go.Bar(
                name=disp_name, x=selected_groups, y=values,
                marker=dict(color=color_map.get(item, '#999'), line=dict(color='white', width=0.5)),
            ))
    else:
        # By Function / By Protein orientation - reverse axes
        for g in selected_groups:
            values = []
            for item in selected_items:
                row = df[df[items_col] == item] if df is not None else pd.DataFrame()
                if row.empty:
                    values.append(0)
                else:
                    col = (f'Rel_Count_{g}' if state.is_relative else f'Count_{g}') if use_count else \
                          (f'Rel_Avg_{g}' if state.is_relative else f'Avg_{g}')
                    v = float(row[col].values[0]) if col in row.columns else 0
                    if use_log:
                        v = _safe_log(v)
                    values.append(v)

            fig.add_trace(go.Bar(
                name=redact_string_descriptions(g),
                x=[redact_string_descriptions(it) for it in selected_items],
                y=values,
                marker=dict(line=dict(color='white', width=0.5)),
            ))

    y_title = ('Relative ' if state.is_relative else '') + \
               ('Log<sub>10</sub> ' if use_log else '') + state.metric_name
    fig.update_layout(
        **_common_layout(state),
        barmode='stack',
        xaxis=dict(title=state.xlabel or 'Sample', tickangle=-35, **_axis_style()),
        yaxis=dict(title=state.ylabel or y_title, **_axis_style()),
        legend=dict(title=dict(text=state.legend_title or 'Item'), font=dict(size=12)),
    )
    if use_log and getattr(state, 'y_axis_format', 'linear') == 'power':
        _power_ticks(fig)
    return fig


# ---------------------------------------------------------------------------
# Plot 4: Pie charts
# ---------------------------------------------------------------------------

def create_pie_charts(state: DataAnalysisState):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    selected_groups = state.selected_groups
    use_count = state.use_count
    plot_filter = state.plot_filter
    orientation = state.orientation

    if plot_filter in ('Selected Function(s)', 'Functional vs Non-Functional Peptides'):
        df = state.function_df
        items_col = 'Description'
        items = state.selected_functions
    elif plot_filter == 'Selected Protein(s)':
        df = state.protein_df
        items_col = 'Description'
        items = state.selected_proteins
    else:
        # No Filter / Both → one pie per sample showing total distribution
        metrics = state.abundance_count_by_sample_dict
        labels = list(metrics.keys())
        vals = [v['unique_peptides'] if use_count else v['total_Abundance'] for v in metrics.values()]
        colors = get_color_sequence(len(labels), state.color_scheme)
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=labels, values=vals,
            marker_colors=colors,
            textposition='inside', textinfo='percent',
            hovertemplate="Sample: %{label}<br>Value: %{value:.2e}<br><extra></extra>",
        ))
        fig.update_layout(**_common_layout(state),
                          showlegend=True,
                          legend=dict(title=dict(text=state.legend_title or 'Sample')))
        return fig

    if df is None or df.empty:
        return None

    if orientation == 'By Sample':
        # One pie per sample
        n = len(selected_groups)
        cols = min(n, 3)
        rows = (n + cols - 1) // cols
        fig = make_subplots(rows=rows, cols=cols, specs=[[{'type': 'pie'}] * cols] * rows)

        for i, group in enumerate(selected_groups):
            row_idx = i // cols + 1
            col_idx = i % cols + 1
            col_key = (f'Count_{group}' if use_count else f'Avg_{group}')
            pie_df = df[df[col_key] > 0] if col_key in df.columns else df
            labels = list(pie_df[items_col])
            vals = [float(v) for v in pie_df.get(col_key, pd.Series([0] * len(pie_df)))]
            colors = get_color_sequence(len(labels), state.color_scheme)

            fig.add_trace(go.Pie(
                labels=[redact_string_descriptions(l) for l in labels],
                values=vals, name=group,
                marker_colors=colors,
                textposition='inside', textinfo='percent',
                title=dict(text=group, font=dict(size=14)),
                hovertemplate="%{label}: %{value:.2e}<br><extra></extra>",
            ), row=row_idx, col=col_idx)

        fig.update_layout(**_common_layout(state),
                          height=400 * rows, width=1000,
                          legend=dict(title=dict(text=state.legend_title or 'Item')))
        return fig
    else:
        # By Function/Protein: one pie per item
        items_to_plot = [it for it in items if it in df[items_col].values]
        n = len(items_to_plot)
        if n == 0:
            return None
        cols = min(n, 3)
        rows = (n + cols - 1) // cols
        fig = make_subplots(rows=rows, cols=cols, specs=[[{'type': 'pie'}] * cols] * rows)

        for i, item in enumerate(items_to_plot):
            row_idx = i // cols + 1
            col_idx = i % cols + 1
            labels = selected_groups
            row = df[df[items_col] == item]
            vals = [float(row.get(f'Count_{g}', 0).values[0] if not row.empty else 0)
                    if use_count else
                    float(row.get(f'Avg_{g}', pd.Series([0])).values[0] if not row.empty else 0)
                    for g in selected_groups]
            colors = get_color_sequence(len(labels), state.color_scheme)

            fig.add_trace(go.Pie(
                labels=labels, values=vals, name=item,
                marker_colors=colors,
                textposition='inside', textinfo='percent',
                title=dict(text=redact_string_descriptions(item), font=dict(size=12)),
                hovertemplate="%{label}: %{value:.2e}<br><extra></extra>",
            ), row=row_idx, col=col_idx)

        fig.update_layout(**_common_layout(state),
                          height=400 * rows, width=1000,
                          legend=dict(title=dict(text=state.legend_title or 'Sample')))
        return fig


# ---------------------------------------------------------------------------
# Plot 5: Correlation scatter
# ---------------------------------------------------------------------------

def create_correlation_plot(state: DataAnalysisState):
    from scipy.stats import pearsonr, spearmanr
    import plotly.graph_objects as go

    selected_groups = state.selected_groups
    df = state.filtered_df
    if df is None or len(selected_groups) != 2:
        return None

    g1, g2 = selected_groups[0], selected_groups[1]
    col1, col2 = f'Avg_{g1}', f'Avg_{g2}'
    if col1 not in df.columns or col2 not in df.columns:
        return None

    use_log = state.log_transform
    first_color = get_single_color(state.color_scheme)

    fdf = df[(df[col1] > 0) & (df[col2] > 0)].copy()
    if fdf.empty:
        return None

    if use_log:
        x_vals = np.log10(fdf[col1])
        y_vals = np.log10(fdf[col2])
        tickfmt = '.0f'
        x_label, y_label = f'Log₁₀ ({g1})', f'Log₁₀ ({g2})'
    else:
        x_vals = fdf[col1]
        y_vals = fdf[col2]
        tickfmt = '.1e'
        x_label, y_label = g1, g2

    corr_text = 'n/a'
    if len(fdf) > 1:
        if state.correlation_type == 'Pearson':
            corr, p = pearsonr(x_vals, y_vals)
            sym = 'r'
        else:
            corr, p = spearmanr(x_vals, y_vals)
            sym = 'ρ'
        p_str = 'p < 0.001' if p < 0.001 else f'p = {p:.3g}'
        corr_text = f'{sym} = {corr:.3f}, {p_str}'

    # Hover columns
    id_col = 'Unique Peptide ID'
    fn_col = 'function' if 'function' in fdf.columns else None
    pn_col = 'protein_name' if 'protein_name' in fdf.columns else None

    customdata = np.column_stack([
        fdf[id_col] if id_col in fdf.columns else [''] * len(fdf),
        fdf[fn_col].fillna('N/A') if fn_col else ['N/A'] * len(fdf),
        fdf[pn_col].fillna('N/A') if pn_col else ['N/A'] * len(fdf),
    ])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode='markers',
        name=f'Correlation: {corr_text}',
        marker=dict(color=first_color),
        customdata=customdata,
        hovertemplate=(
            '<b>Peptide:</b> %{customdata[0]}<br>'
            '<b>Function:</b> %{customdata[1]}<br>'
            '<b>Protein:</b> %{customdata[2]}<br>'
            '<extra></extra>'
        ),
    ))

    if len(fdf) > 1:
        z = np.polyfit(x_vals, y_vals, 1)
        x_range_vals = np.linspace(x_vals.min(), x_vals.max(), 100)
        fig.add_trace(go.Scatter(
            x=x_range_vals, y=np.poly1d(z)(x_range_vals),
            mode='lines', line=dict(color=first_color, dash='dash'),
            name='Trendline', showlegend=True,
            hovertemplate='<extra></extra>',
        ))

    ax_kw = dict(tickformat=tickfmt, showline=True, linewidth=1, linecolor='black',
                 gridcolor='lightgray', showgrid=True, zeroline=False,
                 tickfont=dict(size=14, color='black'),
                 title_font=dict(size=16, color='black'))

    leg_title = state.legend_title or f'{state.correlation_type} Correlation'
    fig.update_layout(
        title=dict(text=_make_title(state), x=0.5, xanchor='center',
                   font=dict(size=18, color='black')),
        xaxis=dict(title=x_label, **ax_kw),
        yaxis=dict(title=y_label, **ax_kw),
        height=500, width=650,
        template='plotly_white',
        legend=dict(title=dict(text=leg_title, font=dict(size=14, color='black')),
                    font=dict(size=13)),
        margin=dict(t=100, b=80, l=80, r=50),
    )
    if use_log and getattr(state, 'y_axis_format', 'linear') == 'power':
        _power_ticks(fig, y_axis='yaxis', x_axis='xaxis')
    return fig


def create_correlation_splom(state: DataAnalysisState):
    from scipy.stats import pearsonr, spearmanr
    import plotly.graph_objects as go

    selected_groups = state.selected_groups
    df = state.filtered_df
    if df is None or len(selected_groups) < 3:
        return None

    use_log = state.log_transform
    first_color = get_single_color(state.color_scheme)
    ct = state.correlation_type

    # Filter to positive values in all groups
    fdf = df.copy()
    valid_groups = []
    for g in selected_groups:
        col = f'Avg_{g}'
        if col in fdf.columns:
            fdf = fdf[fdf[col] > 0]
            valid_groups.append(g)

    if fdf.empty or len(valid_groups) < 3:
        return None

    dimensions = []
    all_vals = []
    for g in valid_groups:
        col = f'Avg_{g}'
        vals = np.log10(fdf[col]) if use_log else fdf[col]
        dimensions.append(dict(values=vals, label=f'Log₁₀ ({g})' if use_log else g))
        all_vals.extend(vals)

    id_col = 'Unique Peptide ID'
    fn_col = 'function' if 'function' in fdf.columns else None
    pn_col = 'protein_name' if 'protein_name' in fdf.columns else None
    customdata = np.column_stack([
        fdf[id_col] if id_col in fdf.columns else [''] * len(fdf),
        fdf[fn_col].fillna('N/A') if fn_col else ['N/A'] * len(fdf),
        fdf[pn_col].fillna('N/A') if pn_col else ['N/A'] * len(fdf),
    ])

    tickfmt = '.0f' if use_log else '.1e'
    splom = go.Splom(
        dimensions=dimensions,
        marker=dict(color=first_color, size=8, line=dict(width=1, color='white')),
        diagonal=dict(visible=False),
        showupperhalf=False,
        customdata=customdata,
        hovertemplate=(
            '<b>Peptide:</b> %{customdata[0]}<br>'
            '<b>Function:</b> %{customdata[1]}<br>'
            '<b>Protein:</b> %{customdata[2]}<br>'
            '<extra></extra>'
        ),
        showlegend=False,
    )

    corr_traces = []
    for i, g1 in enumerate(valid_groups):
        for j, g2 in enumerate(valid_groups):
            if i >= j:
                continue
            c1, c2 = f'Avg_{g1}', f'Avg_{g2}'
            x_vals = np.log10(fdf[c1]) if use_log else fdf[c1]
            y_vals = np.log10(fdf[c2]) if use_log else fdf[c2]
            if ct == 'Pearson':
                corr, p = pearsonr(x_vals, y_vals)
                sym = 'r'
            else:
                corr, p = spearmanr(x_vals, y_vals)
                sym = 'ρ'
            p_str = 'p < 0.001' if p < 0.001 else f'p = {p:.3g}'
            corr_traces.append(go.Scatter(
                x=[None], y=[None], mode='markers',
                marker=dict(color=first_color),
                name=f'{g1}–{g2}: {sym} = {corr:.3f}, {p_str}',
                showlegend=True,
            ))

    fig = go.Figure(data=[splom] + corr_traces)
    sz = 250 * len(valid_groups)
    leg_title = state.legend_title or f'{ct} Correlation'
    fig.update_layout(
        title=dict(text=_make_title(state), x=0.5, xanchor='center',
                   font=dict(size=18, color='black')),
        width=sz, height=sz,
        template='plotly_white',
        legend=dict(title=dict(text=leg_title, font=dict(size=14, color='black')),
                    font=dict(size=13), x=0.8, y=1),
    )
    # Apply consistent axis ranges/formats
    overall_min, overall_max = min(all_vals), max(all_vals)
    combined_range = [overall_min * 0.95, overall_max * 1.05]
    tick_vals = np.linspace(combined_range[0], combined_range[1], 6)
    for k in range(1, len(valid_groups) + 1):
        fig.update_layout({
            f'xaxis{k}': dict(range=combined_range, tickvals=tick_vals, tickformat=tickfmt,
                              tickfont=dict(size=12, color='black'), tickangle=45),
            f'yaxis{k}': dict(range=combined_range, tickvals=tick_vals, tickformat=tickfmt,
                              tickfont=dict(size=12, color='black')),
        })
    return fig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _power_ticks(fig, y_axis='yaxis', x_axis=None):
    """
    Replace numeric tick labels on log-transformed axes with 10^n HTML superscript format.
    Scans all trace y (and optionally x) values to determine integer tick range.
    """
    import math

    def _vals_from_traces(attr):
        out = []
        for trace in fig.data:
            raw = getattr(trace, attr, None)
            if raw is None:
                continue
            try:
                out.extend(v for v in raw if v is not None and not (isinstance(v, float) and math.isnan(v)))
            except TypeError:
                pass
        return out

    def _make_ticks(vals):
        if not vals:
            return None, None
        mn, mx = math.floor(min(vals)), math.ceil(max(vals))
        tv = list(range(mn, mx + 1))
        tt = [f'10<sup>{v}</sup>' if v >= 0 else f'10<sup>−{abs(v)}</sup>' for v in tv]
        return tv, tt

    y_vals = _vals_from_traces('y')
    tv, tt = _make_ticks(y_vals)
    if tv:
        fig.update_layout({y_axis: dict(tickvals=tv, ticktext=tt)})

    if x_axis:
        x_vals = _vals_from_traces('x')
        tv, tt = _make_ticks(x_vals)
        if tv:
            fig.update_layout({x_axis: dict(tickvals=tv, ticktext=tt)})


def _common_layout(state: DataAnalysisState) -> dict:
    return dict(
        template='plotly_white',
        height=800, width=1000,
        margin=dict(t=100, l=100, r=100),
        font=dict(color='black'),
        title=dict(text=_make_title(state), y=0.95, x=0.5,
                   xanchor='center', yanchor='top',
                   font=dict(size=18, color='black')),
    )


def _axis_style() -> dict:
    return dict(
        showline=True, linewidth=1, linecolor='black',
        mirror=False, gridcolor='lightgray', showgrid=True, zeroline=False,
        title_font=dict(size=18, color='black'),
        tickfont=dict(size=16, color='black'),
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_plot(merged_df: pd.DataFrame, group_data_dict: dict, protein_dict: dict, params: dict):
    """
    Main entry point: build state, run pipeline, generate appropriate plot.
    Returns (plotly_json_str, warnings_list).
    """
    warnings = []

    state = DataAnalysisState(merged_df, group_data_dict, protein_dict, params)

    try:
        state.run_pipeline()
    except Exception:
        warnings.append('Error during data processing: ' + traceback.format_exc())
        return None, warnings

    plot_type = state.plot_type
    orientation = state.orientation
    plot_filter = state.plot_filter
    use_count = state.use_count
    fig = None

    try:
        if plot_type == 'Grouped Bar Plots':
            if orientation == 'By Sample' and plot_filter in ('No Filter', 'Both') and not state.is_relative:
                fig = plot_total_peptides(state)
            else:
                fig = create_grouped_bar_plot(state)

        elif plot_type == 'Stacked Bar Plots':
            if plot_filter == 'Both':
                warnings.append(
                    "Plot Filter 'Both' is not supported for Stacked Bar Plots. "
                    "Please choose a single filter."
                )
            else:
                fig = plot_stacked_bar_scaled(state)

        elif plot_type == 'Pie Charts':
            fig = create_pie_charts(state)

        elif plot_type == 'Corr. Scatter Plots':
            n = len(state.selected_groups)
            if n < 2:
                warnings.append('Please select at least 2 groups for correlation analysis.')
            elif n == 2:
                fig = create_correlation_plot(state)
            else:
                fig = create_correlation_splom(state)
    except Exception:
        warnings.append('Error generating plot: ' + traceback.format_exc())
        return None, warnings

    if fig is None:
        warnings.append('No plot generated. Please check your selections and data.')
        return None, warnings

    return fig.to_json(), warnings

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


def _safe_log(val):
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None
    if np.isnan(v) or v <= 0:
        return None
    return np.log10(v)


# ---------------------------------------------------------------------------
# Title / label helpers
# ---------------------------------------------------------------------------

def _make_title(state: DataAnalysisState) -> str:
    title = state.plot_title
    if not title:
        parts = []
        if state.plot_filter not in ('No Filter',):
            if state.selected_proteins and state.plot_filter in ('Selected Protein(s)', 'Both'):
                parts.append('Filtered By: ' + ', '.join(state.selected_protein_names[:3]))
            if state.selected_functions and state.plot_filter in ('Selected Function(s)', 'Both'):
                parts.append('Function: ' + ', '.join(state.selected_functions[:3]))
        title = ' | '.join(parts) if parts else f'{state.abs_or_count} Distribution - {state.orientation}'
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
        count_label_text = [f"{c:.2f}" if use_log else f"{int(c):,}" for c in counts]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=groups, y=counts, name='Peptide Count',
            marker=dict(color=first_color, line=dict(color='black', width=1)),
            error_y=dict(type='data', array=count_sems, visible=True,
                         thickness=1.5, width=4, color='#000000'),
            hovertemplate=(
                "Group: %{x}<br>"
                "Unique Peptides: %{y:.0f}<br>"
                "SEM: %{error_y.array:.1f}<br>"
                "<extra></extra>"
            ),
        ))
        fig.add_trace(go.Scatter(
            x=groups,
            y=[c + (s * 1.2) for c, s in zip(counts, count_sems)],
            mode='text',
            text=count_label_text,
            textposition='top center',
            textfont=dict(size=12),
            showlegend=False,
            hoverinfo='none',
        ))
        y_axis_title = f'{y_prefix}Unique Peptide Count'
        if use_log:
            yaxis_kw = dict(tickformat=tickfmt, title_font=dict(size=18, color='black'),
                            tickfont=dict(size=16, color='black'), **AXIS_STYLE)
        else:
            yaxis_kw = dict(tickformat=',d', exponentformat='none',
                            title_font=dict(size=18, color='black'),
                            tickfont=dict(size=16, color='black'), **AXIS_STYLE)
        fig.update_layout(
            **COMMON_LAYOUT,
            title=dict(text=_make_title(state), y=0.95, x=0.5, xanchor='center',
                       yanchor='top', font=dict(size=18, color='black')),
            xaxis=dict(title='Sample', **AXIS_STYLE, tickangle=45,
                       title_font=dict(size=18, color='black'),
                       tickfont=dict(size=16, color='black')),
            yaxis=dict(title=y_axis_title, **yaxis_kw),
        )
    else:
        abundance_label_text = [f"{a:.2f}" if use_log else f"{a:.2e}" for a in abundances]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=groups, y=abundances, name='Abundance',
            marker=dict(color=first_color, line=dict(color='black', width=1)),
            error_y=dict(type='data', array=abundance_sems, visible=True,
                         thickness=1.5, width=4, color='#000000'),
            hovertemplate=(
                "Group: %{x}<br>"
                "Total Abundance: %{y:.2e}<br>"
                "SEM: %{error_y.array:.2e}<br>"
                "<extra></extra>"
            ),
        ))
        fig.add_trace(go.Scatter(
            x=groups,
            y=[a + s for a, s in zip(abundances, abundance_sems)],
            mode='text',
            text=abundance_label_text,
            textposition='top center',
            textfont=dict(size=14),
            showlegend=False,
            hoverinfo='none',
        ))
        y_axis_title = f'{y_prefix}Summed Abundance'
        if use_log:
            yaxis_kw = dict(tickformat=tickfmt, title_font=dict(size=18, color='black'),
                            tickfont=dict(size=16, color='black'), **AXIS_STYLE)
        else:
            yaxis_kw = dict(type='log', exponentformat='e',
                            title_font=dict(size=18, color='black'),
                            tickfont=dict(size=16, color='black'), **AXIS_STYLE)
        fig.update_layout(
            **COMMON_LAYOUT,
            title=dict(text=_make_title(state), y=0.95, x=0.5, xanchor='center',
                       yanchor='top', font=dict(size=18, color='black')),
            xaxis=dict(title=state.xlabel or 'Sample', **AXIS_STYLE, tickangle=45,
                       title_font=dict(size=18, color='black'),
                       tickfont=dict(size=16, color='black')),
            yaxis=dict(title=state.ylabel or y_axis_title, **yaxis_kw),
        )
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

    if orientation == 'By Function' or (orientation == 'By Sample' and plot_filter in ('Selected Function(s)', 'Functional vs Non-Functional Peptides')):
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

        # Minor Functions always shown in grey
        if 'Minor Functions' in color_map:
            color_map['Minor Functions'] = '#808080'

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
                abs_value = entry.get('counts' if use_count else 'Abundance', {}).get(group, 0)
                rel_value = entry.get('count_relative' if use_count else 'abundance_relative', {}).get(group, 0)
                if state.is_relative:
                    v = rel_value
                else:
                    v = abs_value
                    if use_log:
                        v = _safe_log(v)
                values.append(v)
                item_label = 'Function' if plot_filter in ('Selected Function(s)', 'Functional vs Non-Functional Peptides') else 'Protein'
                if state.is_relative:
                    hover.append(
                        f"{item_label}: {item}<br>"
                        f"Sample: {group}<br>"
                        f"Relative Contribution: {rel_value:.1f}%<br>"
                        f"{state.metric_name}: {abs_value:{state.num_format}}"
                    )
                else:
                    hover.append(
                        f"{item_label}: {item}<br>"
                        f"Sample: {group}<br>"
                        f"{state.metric_name}: {abs_value:{state.num_format}}<br>"
                        f"Relative Contribution: {rel_value:.1f}%"
                    )

            fn_color = color_map.get(bar_group, '#999')
            if bar_group in ('Minor Functions', 'Minor Proteins'):
                fn_color = '#808080'
            fig.add_trace(go.Bar(
                x=x_pos, y=values, name=disp_bg,
                marker=dict(color=fn_color, line=dict(color='black', width=0.5)),
                width=bar_width * 0.9,
                hovertext=hover, hoverinfo='text',
            ))

        y_title = state.ylabel or ('Log<sub>10</sub> ' if use_log else '') + state.metric_name
        yaxis_fn = _build_grouped_yaxis(state, use_log, use_count)
        fig.update_layout(
            **_common_layout(state),
            xaxis=dict(tickvals=list(range(len(categories))), ticktext=display_cats,
                       tickangle=45, title=state.xlabel or 'Category',
                       **_axis_style()),
            yaxis=dict(title=y_title, **yaxis_fn),
            barmode='group',
            hoverlabel=dict(bgcolor='white', font_size=12, font_family='Arial'),
            legend=dict(title=dict(text=state.legend_title or 'Item'),
                        yanchor='top', y=1.0, xanchor='left', x=1.05,
                        font=dict(size=12, color='black')),
        )
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

        # Minor Proteins always shown in grey
        if 'Minor Proteins' in color_map:
            color_map['Minor Proteins'] = '#808080'

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
                else:
                    item, group = cat, bar_group
                # Use Count columns when Peptide Count is selected, Avg columns for Abundance
                abs_col = f'Count_{group}' if use_count else f'Avg_{group}'
                rel_col = f'Rel_Count_{group}' if use_count else f'Rel_Avg_{group}'
                row = df[df['Description'] == item]
                abs_value = float(row[abs_col].values[0]) if len(row) > 0 and abs_col in row.columns else 0
                rel_value = float(row[rel_col].values[0]) if len(row) > 0 and rel_col in row.columns else 0
                if state.is_relative:
                    v = rel_value
                else:
                    v = abs_value
                    if use_log:
                        v = _safe_log(v)
                values.append(v)
                count_fmt = ',.0f' if use_count else state.num_format
                if state.is_relative:
                    hover.append(
                        f"Protein: {item}<br>"
                        f"Sample: {group}<br>"
                        f"Relative Contribution: {rel_value:.1f}%<br>"
                        f"{state.metric_name}: {abs_value:{count_fmt}}"
                    )
                else:
                    hover.append(
                        f"Protein: {item}<br>"
                        f"Sample: {group}<br>"
                        f"{state.metric_name}: {abs_value:{count_fmt}}<br>"
                        f"Relative Contribution: {rel_value:.1f}%"
                    )

            bar_color = color_map.get(bar_group, '#999')
            if bar_group == 'Minor Proteins':
                bar_color = '#808080'
            fig.add_trace(go.Bar(
                x=x_pos, y=values, name=disp_bg,
                marker=dict(color=bar_color, line=dict(color='black', width=0.5)),
                width=bar_width * 0.9,
                hovertext=hover, hoverinfo='text',
            ))

        y_title = state.ylabel or ('Log<sub>10</sub> ' if use_log else '') + state.metric_name
        yaxis_prot = _build_grouped_yaxis(state, use_log, use_count)
        fig.update_layout(
            **_common_layout(state),
            xaxis=dict(tickvals=list(range(len(categories))), ticktext=display_cats,
                       tickangle=45, title=state.xlabel or 'Category', **_axis_style()),
            yaxis=dict(title=y_title, **yaxis_prot),
            barmode='group',
            hoverlabel=dict(bgcolor='white', font_size=12, font_family='Arial'),
            legend=dict(title=dict(text=state.legend_title or 'Item'),
                        yanchor='top', y=1.0, xanchor='left', x=1.05,
                        font=dict(size=12, color='black')),
        )
        return fig

    elif plot_filter in ('No Filter', 'Both') and orientation == 'By Sample':
        # Total peptide absolute
        return plot_total_peptides(state)

    return None


# ---------------------------------------------------------------------------
# Plot 3: Stacked bar plot
# ---------------------------------------------------------------------------

def _plot_no_filter_stacked(state: DataAnalysisState):
    """Stacked bar for 'No Filter': single 'Total' bar with one segment per sample group."""
    import plotly.graph_objects as go

    data = state.total_peptide_results_dict
    if not data:
        return None

    groups = list(data.keys())
    use_count = state.use_count
    color_seq = get_color_sequence(len(groups), state.color_scheme)

    total_count = sum(data[g]['unique_peptides'] for g in groups) or 1
    total_abund = sum(data[g]['total_Abundance'] for g in groups) or 1

    fig = go.Figure()
    for i, g in enumerate(groups):
        abs_val = data[g]['unique_peptides'] if use_count else data[g]['total_Abundance']
        rel_val = (data[g]['unique_peptides'] / total_count * 100) if use_count \
                  else (data[g]['total_Abundance'] / total_abund * 100)
        y_val = rel_val if state.is_relative else abs_val
        metric_label = 'Peptide Count' if use_count else 'Abundance'
        hover = (
            f"Sample: {g}<br>"
            f"{metric_label}: {abs_val:{state.num_format}}<br>"
            f"Contribution: {rel_val:.2f}%"
        )
        fig.add_trace(go.Bar(
            name=g, x=['Total'], y=[y_val],
            marker=dict(color=color_seq[i], line=dict(color='white', width=0.5)),
            hovertext=[hover], hoverinfo='text',
        ))

    y_title = ('Relative ' if state.is_relative else '') + state.metric_name
    yaxis_kw = _axis_style()
    if state.is_relative:
        yaxis_kw['range'] = [0, 100]
    fig.update_layout(
        **_common_layout(state),
        barmode='stack',
        xaxis=dict(title='', **_axis_style()),
        yaxis=dict(title=state.ylabel or y_title, **yaxis_kw),
        hoverlabel=dict(bgcolor='white', font_size=12, font_family='Arial'),
        legend=dict(title=dict(text=state.legend_title or 'Sample'), font=dict(size=12)),
    )
    return fig


def plot_stacked_bar_scaled(state: DataAnalysisState):
    """
    Stacked bar plot matching notebook's plot_stacked_bar_scaled logic.

    By Sample orientation (x=groups, legend=items):
      - y_value = rel_value / 100 * total_sums[g]  where total_sums uses the
        proper per-group total (unique functional peptide count / actual functional
        abundance) to prevent double-counting multi-function peptides.

    By Function / By Protein orientation (x=items, legend=groups):
      - Uses function_distribution_dict / protein_sample_distribution_dict with
        'relative' key = group's contribution to the item's total.
      - y_value = (rel_percentage / 100) * item_total  for non-log absolute
      - y_value = (rel_percentage / 100) * log10(item_total)  for log
    """
    import plotly.graph_objects as go

    selected_groups = state.selected_groups
    use_count = state.use_count
    use_log = state.log_transform
    plot_filter = state.plot_filter
    orientation = state.orientation

    if plot_filter == 'No Filter':
        return _plot_no_filter_stacked(state)

    # ── Resolve data source and selected items ─────────────────────────────────
    is_func_filter = plot_filter in ('Selected Function(s)', 'Functional vs Non-Functional Peptides')
    is_prot_filter = plot_filter == 'Selected Protein(s)'
    is_both = plot_filter == 'Both'

    if is_func_filter:
        df = state.function_df
        items_col = 'Description'
        selected_items = state.selected_functions
        item_label = 'Function'
    elif is_prot_filter:
        df = state.protein_df
        items_col = 'Description'
        selected_items = state.selected_protein_names
        item_label = 'Protein'
    else:  # Both
        # Combine function and protein items
        fn_df = state.function_df
        pr_df = state.protein_df
        if (fn_df is None or fn_df.empty) and (pr_df is None or pr_df.empty):
            return plot_total_peptides(state)
        df = pd.concat([d for d in [fn_df, pr_df] if d is not None and not d.empty], ignore_index=True)
        items_col = 'Description'
        selected_items = list(state.selected_functions) + list(state.selected_protein_names)
        item_label = 'Item'

    if df is None or (hasattr(df, 'empty') and df.empty):
        return plot_total_peptides(state)

    # ── Build color map ────────────────────────────────────────────────────────
    color_seq = get_color_sequence(len(selected_items), state.color_scheme)
    color_map = {item: color_seq[i] for i, item in enumerate(selected_items)}
    if state.plot_minor and 'Minor Functions' in color_map:
        color_map['Minor Functions'] = '#808080'
    if state.plot_minor and 'Minor Proteins' in color_map:
        color_map['Minor Proteins'] = '#808080'

    fig = go.Figure()

    # ── By Sample orientation ──────────────────────────────────────────────────
    if orientation == 'By Sample':
        # Compute total_sums per group – matches notebook's approach of using the
        # real total (unique peptides / unique functional abundance) to prevent
        # stacked bars from summing to an inflated (double-counted) total.
        total_sums = {}
        for g in selected_groups:
            if use_count:
                if is_func_filter:
                    total_sums[g] = state.function_count_totals_dict.get(g, 0)
                elif is_prot_filter:
                    _pct = state.protein_count_bysample_dict.get(g, 0)
                    if not _pct and state.protein_df is not None and f'Count_{g}' in state.protein_df.columns:
                        _pct = int(state.protein_df[f'Count_{g}'].sum())
                    total_sums[g] = _pct
                else:  # Both
                    total_sums[g] = state.abundance_count_by_sample_dict.get(g, {}).get('unique_peptides', 0)
            else:  # abundance
                if is_func_filter:
                    total_sums[g] = state.function_abundance_totals_dict.get(g, 0)
                elif is_prot_filter:
                    sm = state.sum_df
                    col_key = f'Avg_{g}'
                    if sm is not None and col_key in sm['Sample'].values:
                        total_sums[g] = float(sm.loc[sm['Sample'] == col_key, 'Total_Sum'].values[0])
                    elif state.protein_df is not None and f'Avg_{g}' in state.protein_df.columns:
                        total_sums[g] = float(state.protein_df[f'Avg_{g}'].sum())
                    else:
                        total_sums[g] = 0.0
                else:  # Both
                    total_sums[g] = state.abundance_count_by_sample_dict.get(g, {}).get('total_Abundance', 0)

        for i, item in enumerate(selected_items):
            row = df[df[items_col] == item] if df is not None else pd.DataFrame()
            values = []
            hover_texts = []
            for g in selected_groups:
                if df is None or row.empty:
                    values.append(0)
                    hover_texts.append(f"No data for {item} in {g}")
                    continue

                abs_col = f'Count_{g}' if use_count else f'Avg_{g}'
                rel_col = f'Rel_Count_{g}' if use_count else f'Rel_Avg_{g}'
                abs_value = float(row[abs_col].values[0]) if abs_col in row.columns else 0.0
                rel_value = float(row[rel_col].values[0]) if rel_col in row.columns else 0.0

                total = total_sums.get(g, 0)
                if state.is_relative:
                    v = rel_value
                elif use_log:
                    log_total = _safe_log(total) if total > 0 else 0.0
                    v = rel_value / 100.0 * log_total
                else:
                    # Scale proportionally so bars sum to the true total
                    # (prevents double-counting of multi-function peptides)
                    v = rel_value / 100.0 * total if total > 0 else abs_value

                values.append(v)
                hover_texts.append(
                    f"{item_label}: {item}<br>"
                    f"Sample: {g}<br>"
                    f"Relative {state.metric_name}: {rel_value:.2f}%<br>"
                    f"Absolute {state.metric_name}: {abs_value:{state.num_format}}"
                )

            disp_name = redact_string_descriptions(item)
            color = color_map.get(item, '#999')
            if item in ('Minor Functions', 'Minor Proteins'):
                color = '#808080'
            fig.add_trace(go.Bar(
                name=disp_name, x=selected_groups, y=values,
                marker=dict(color=color, line=dict(color='white', width=0.5)),
                hovertext=hover_texts, hoverinfo='text',
            ))

        # Totals annotation (matches notebook's scatter-text trace above bars)
        if not state.is_relative:
            text_vals = []
            for g in selected_groups:
                total = total_sums.get(g, 0)
                if use_log and total > 0:
                    text_vals.append(f"{np.log10(max(total, 1e-10)):.2f}")
                elif use_count:
                    text_vals.append(f"{int(total):,}")
                else:
                    text_vals.append(f"{total:.2e}")
            y_totals = []
            for g in selected_groups:
                total = total_sums.get(g, 0)
                if use_log and total > 0:
                    y_totals.append(np.log10(max(total, 1e-10)))
                else:
                    y_totals.append(total)
            fig.add_trace(go.Scatter(
                x=selected_groups, y=y_totals,
                mode='text', text=text_vals,
                textposition='top center',
                textfont=dict(size=10 if len(selected_groups) > 12 else 12, color='black'),
                showlegend=True,
                name=f'Total {state.metric_name}',
                hoverinfo='none',
            ))

    # ── By Function / By Protein orientation ──────────────────────────────────
    else:
        # Build per-item totals dict from function_distribution_dict or protein_sample_distribution_dict
        # Uses 'relative'  = each group's contribution to the item's total
        item_data_dict = {}
        for item in selected_items:
            if plot_filter in ('Selected Function(s)', 'Functional vs Non-Functional Peptides', 'Both'):
                d = state.function_distribution_dict.get(item)
                if d is not None:
                    item_data_dict[item] = d
            if item not in item_data_dict and plot_filter in ('Selected Protein(s)', 'Both'):
                d = state.protein_sample_distribution_dict.get(item)
                if d is None:
                    # try matching by name from protein_df
                    if state.protein_df is not None:
                        pr = state.protein_df[state.protein_df['Description'] == item]
                        if not pr.empty:
                            row = pr.iloc[0]
                            tot_ab = sum(float(row.get(f'Avg_{g}', 0)) for g in selected_groups)
                            tot_ct = sum(float(row.get(f'Count_{g}', 0)) for g in selected_groups)
                            d = {
                                'Abundance': {g: float(row.get(f'Avg_{g}', 0)) for g in selected_groups},
                                'counts': {g: float(row.get(f'Count_{g}', 0)) for g in selected_groups},
                                'relative': {
                                    g: float(row.get(f'Avg_{g}', 0)) / tot_ab * 100 if tot_ab > 0 else 0.0
                                    for g in selected_groups
                                },
                                'count_relative_to_function': {
                                    g: float(row.get(f'Count_{g}', 0)) / tot_ct * 100 if tot_ct > 0 else 0.0
                                    for g in selected_groups
                                },
                                'total_Abundance': tot_ab,
                                'unique_peptide_count': int(row.get('unique_peptide_count', 0)),
                            }
                if d is not None:
                    item_data_dict[item] = d

        all_items = [it for it in selected_items if it in item_data_dict]
        display_items = [redact_string_descriptions(it) for it in all_items]
        colors = get_color_sequence(len(selected_groups), state.color_scheme)

        for gi, g in enumerate(selected_groups):
            values = []
            hover_texts = []
            for item in all_items:
                data = item_data_dict[item]

                # Use group's contribution to item total ('relative' key)
                # so stacked bars show distribution of this item across samples
                rel_key = 'count_relative_to_function' if use_count else 'relative'
                rel_percentage = data.get(rel_key, {}).get(g, 0.0)

                abs_value = (
                    data.get('counts' if use_count else 'Abundance', {}).get(g, 0.0)
                )
                item_total = (
                    data.get('unique_peptide_count', 0)
                    if use_count
                    else data.get('total_Abundance', 0.0)
                )

                if state.is_relative:
                    v = rel_percentage
                elif use_log:
                    log_total = _safe_log(item_total) if item_total > 0 else 0.0
                    v = rel_percentage / 100.0 * log_total
                else:
                    # Equivalent to abs_value but expressed via proportional total
                    # (same as notebook: total_Abundance * rel_percentage / 100)
                    v = item_total * (rel_percentage / 100.0) if item_total > 0 else abs_value

                values.append(v)
                abs_count_label = 'Count' if use_count else 'Abundance'
                hover_texts.append(
                    f"{item_label}: {item}<br>"
                    f"Sample: {g}<br>"
                    f"Sample's contribution: {rel_percentage:.2f}%<br>"
                    f"{abs_count_label} in sample: {abs_value:{state.num_format}}"
                )

            color = colors[gi] if gi < len(colors) else '#CCCCCC'
            fig.add_trace(go.Bar(
                name=redact_string_descriptions(g),
                x=display_items,
                y=values,
                marker=dict(color=color, line=dict(color='white', width=0.5)),
                hovertext=hover_texts, hoverinfo='text',
            ))

        # Totals above bars
        if not state.is_relative:
            text_vals = []
            y_totals = []
            for item in all_items:
                data = item_data_dict[item]
                total = (
                    data.get('unique_peptide_count', 0)
                    if use_count
                    else data.get('total_Abundance', 0.0)
                )
                if use_log and total > 0:
                    text_vals.append(f"{np.log10(max(total, 1e-10)):.2f}")
                    y_totals.append(np.log10(max(total, 1e-10)))
                elif use_count:
                    text_vals.append(f"{int(total):,}")
                    y_totals.append(total)
                else:
                    text_vals.append(f"{total:.2e}")
                    y_totals.append(total)
            fig.add_trace(go.Scatter(
                x=display_items, y=y_totals,
                mode='text', text=text_vals,
                textposition='top center',
                textfont=dict(size=12, color='black'),
                showlegend=True,
                name=f'Total {state.metric_name}',
                hoverinfo='none',
            ))

    # ── Layout ─────────────────────────────────────────────────────────────────
    y_title = ('Relative ' if state.is_relative else '') + \
               ('Log<sub>10</sub> ' if (use_log and not state.is_relative) else '') + state.metric_name
    yaxis_stk = _axis_style()
    if state.is_relative:
        yaxis_stk['range'] = [0, 100]
        yaxis_stk['tickformat'] = '.1f'
    elif use_count and not use_log:
        yaxis_stk['tickformat'] = ',d'
        yaxis_stk['exponentformat'] = 'none'
        yaxis_stk['showexponent'] = 'none'
    elif use_count and use_log:
        yaxis_stk['tickformat'] = '.1f'
        yaxis_stk['exponentformat'] = 'none'
    elif use_log:
        yaxis_stk['tickformat'] = '.1f'
        yaxis_stk['exponentformat'] = 'none'
    else:
        yaxis_stk['exponentformat'] = 'E'
        yaxis_stk['showexponent'] = 'all'

    xlabel = state.xlabel or ('Sample' if orientation == 'By Sample' else 'Function / Protein')
    fig.update_layout(**{
        **_common_layout(state),
        'barmode': 'stack',
        'xaxis': dict(title=xlabel, tickangle=-90 if orientation == 'By Sample' else 45, **_axis_style()),
        'yaxis': dict(title=state.ylabel or y_title, **yaxis_stk),
        'hoverlabel': dict(bgcolor='white', font_size=12, font_family='Arial'),
        'legend': dict(
            title=dict(text=state.legend_title or ('Item' if orientation == 'By Sample' else 'Sample')),
            font=dict(size=16, color='black'),
            yanchor='top', y=0.95, xanchor='left', x=1.05,
            bgcolor='rgba(255,255,255,0.9)',
        ),
        'height': 820, 'width': 1200,
        'margin': dict(t=100, l=100, r=100, b=100),
    })
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
        items = state.selected_protein_names
    else:
        # No Filter / Both → one pie per sample showing total distribution
        metrics = state.abundance_count_by_sample_dict
        labels = list(metrics.keys())
        vals = [v['unique_peptides'] if use_count else v['total_Abundance'] for v in metrics.values()]
        colors = get_color_sequence(len(labels), state.color_scheme)
        fig = go.Figure()
        _hover_fmt_nf = "Sample: %{label}<br>Value: %{value:,.0f}<br><extra></extra>" if use_count else "Sample: %{label}<br>Value: %{value:.2e}<br><extra></extra>"
        fig.add_trace(go.Pie(
            labels=labels, values=vals,
            marker_colors=colors,
            textposition='inside', textinfo='percent',
            hovertemplate=_hover_fmt_nf,
        ))
        fig.update_layout(**{**_common_layout(state),
                          'showlegend': True,
                          'legend': dict(title=dict(text=state.legend_title or 'Sample'))})
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
            if col_key in df.columns:
                pie_df = df[df[items_col].isin(items) & (df[col_key] > 0)]
            else:
                pie_df = df[df[items_col].isin(items)]
            labels = list(pie_df[items_col])
            vals = [float(v) for v in pie_df.get(col_key, pd.Series([0] * len(pie_df)))]
            colors = get_color_sequence(len(labels), state.color_scheme)
            colors = [
                '#808080' if lbl in ('Minor Proteins', 'Minor Functions') else c
                for lbl, c in zip(labels, colors)
            ]

            hover_fmt = "%{label}: %{value:,.0f}<br><extra></extra>" if use_count else "%{label}: %{value:.2e}<br><extra></extra>"
            fig.add_trace(go.Pie(
                labels=[redact_string_descriptions(l) for l in labels],
                values=vals, name=group,
                marker_colors=colors,
                textposition='inside', textinfo='percent',
                title=dict(text=group, font=dict(size=14)),
                hovertemplate=hover_fmt,
            ), row=row_idx, col=col_idx)

        fig.update_layout(**{**_common_layout(state),
                          'height': 400 * rows, 'width': 1000,
                          'legend': dict(title=dict(text=state.legend_title or 'Item'))})
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

            _item_hover_fmt = "%{label}: %{value:,.0f}<br><extra></extra>" if use_count else "%{label}: %{value:.2e}<br><extra></extra>"
            fig.add_trace(go.Pie(
                labels=labels, values=vals, name=item,
                marker_colors=colors,
                textposition='inside', textinfo='percent',
                title=dict(text=redact_string_descriptions(item), font=dict(size=12)),
                hovertemplate=_item_hover_fmt,
            ), row=row_idx, col=col_idx)

        fig.update_layout(**{**_common_layout(state),
                          'height': 400 * rows, 'width': 1000,
                          'legend': dict(title=dict(text=state.legend_title or 'Sample'))})
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
        x_label, y_label = f'Log<sub>10</sub> ({g1})', f'Log<sub>10</sub> ({g2})'
    else:
        x_vals = fdf[col1]
        y_vals = fdf[col2]
        tickfmt = '.1e'
        x_label, y_label = g1, g2

    corr_text = 'n/a'
    if len(fdf) > 1:
        if state.correlation_type == 'Pearson':
            corr, p = pearsonr(x_vals, y_vals)
            sym = '<i>r</i>'
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

    # Synchronized tick values for both axes (same range)
    x_min, x_max = float(x_vals.min()), float(x_vals.max())
    y_min, y_max = float(y_vals.min()), float(y_vals.max())
    overall_min = min(x_min, y_min)
    overall_max = max(x_max, y_max)
    combined_range = [overall_min * 0.95, overall_max * 1.05]
    if use_log:
        range_span = combined_range[1] - combined_range[0]
        if range_span > 5:
            tick_vals = list(np.arange(np.floor(combined_range[0]), np.ceil(combined_range[1]) + 1, 1))
        else:
            tick_vals = list(np.arange(np.floor(combined_range[0] * 2) / 2,
                                       np.ceil(combined_range[1] * 2) / 2 + 0.5, 0.5))
    else:
        tick_vals = list(np.linspace(combined_range[0], combined_range[1], 6))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode='markers',
        name=f'Correlation: {corr_text}',
        marker=dict(color=first_color),
        customdata=customdata,
        hovertemplate=(
            '<b>Peptide ID:</b> %{customdata[0]}<br>'
            '<b>Function:</b> %{customdata[1]}<br>'
            '<b>Protein:</b> %{customdata[2]}<br>'
            '<b>%{xaxis.title.text}:</b> %{x:' + tickfmt + '}<br>'
            '<b>%{yaxis.title.text}:</b> %{y:' + tickfmt + '}<br>'
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

    ax_kw = dict(tickformat=tickfmt, tickvals=tick_vals, nticks=5,
                 range=combined_range,
                 showline=True, linewidth=1, linecolor='black',
                 gridcolor='lightgray', showgrid=True, zeroline=False,
                 tickfont=dict(size=14, color='black'),
                 title_font=dict(size=16, color='black'))

    leg_title = state.legend_title or f'{state.correlation_type} Correlation Values'
    fig.update_layout(
        title=dict(text=_make_title(state), x=0.5, xanchor='center',
                   font=dict(size=18, color='black')),
        xaxis=dict(title=x_label, tickangle=45, **ax_kw),
        yaxis=dict(title=y_label, **ax_kw),
        height=500, width=600,
        template='plotly_white',
        showlegend=True,
        legend=dict(
            title=dict(text=leg_title, font=dict(size=16, color='black')),
            yanchor='top', y=0.99, xanchor='right', x=0.99,
            bgcolor='rgba(255, 255, 255, 0.8)',
            font=dict(size=14),
        ),
        margin=dict(t=100, b=80, l=80, r=50),
    )
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
        dimensions.append(dict(values=vals, label=f'Log<sub>10</sub> ({g})' if use_log else g))
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
        width=sz + 250, height=sz,
        template='plotly_white',
        legend=dict(title=dict(text=leg_title, font=dict(size=14, color='black')),
                    font=dict(size=13), x=1.01, y=1, yanchor='top'),
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

def _build_grouped_yaxis(state: DataAnalysisState, use_log: bool, use_count: bool) -> dict:
    """Return y-axis kwargs matching notebook grouped bar plot formatting."""
    kw = _axis_style()
    if state.is_relative:
        kw['range'] = [0, 100]
    elif use_count and use_log:
        kw['type'] = 'linear'
        kw['tickformat'] = '.1f'
        kw['exponentformat'] = 'none'
        kw['showexponent'] = 'none'
    elif use_count and not use_log:
        kw['type'] = 'linear'
        kw['tickformat'] = ',d'
        kw['exponentformat'] = 'none'
        kw['showexponent'] = 'none'
    elif not use_count and use_log:
        kw['type'] = 'linear'
        kw['tickformat'] = '.1f'
        kw['exponentformat'] = 'none'
        kw['showexponent'] = 'none'
    else:  # abundance, no log
        kw['type'] = 'linear'
        kw['exponentformat'] = 'E'
        kw['showexponent'] = 'all'
    return kw


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

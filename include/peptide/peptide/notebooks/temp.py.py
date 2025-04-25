available_data_variables = viz_handler.selector.available_data_variables
label_widgets_container = widgets.VBox([
    widgets.HTML("<p>Labels will appear here when data is loaded</p>")
], layout=widgets.Layout(
    width='100%',
    height='auto',
    margin='0px'
))

def update_label_order_widgets(available_data_variables, label_widgets_container):
    """Update existing label/order widgets with current data in a grid layout"""
    # Create new widgets list
    widgets_list = []
    
    # Populate rows - each available_data_variable becomes a row
    for i, (var, info) in enumerate(available_data_variables.items(), 1):
        # Create row with HTML text for all except the input field
        # Set fixed widths and use ellipsis for overflow
        row_widgets = [
            # Number - smaller width
            widgets.HTML(f"<div style='width:20px; padding:2px;'>{i})</div>"),
            
            # Label - use ellipsis for overflow
            widgets.HTML(f"<div style='width:100px; padding:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{info['label']}'>{info['label']}</div>"),
            
            # Protein Species - use ellipsis for overflow
            widgets.HTML(f"<div style='width:50px; padding:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{info.get('protein_species', '')}'>{info.get('protein_species', '')}</div>"),
            
            # Protein Name - use ellipsis for overflow
            widgets.HTML(f"<div style='width:100px; padding:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{info.get('protein_name', '')}'>{info.get('protein_name', '')}</div>"),
            
            # Only the edit field remains as a widget - fixed width
            widgets.Text(
                value=info['label'],
                layout=widgets.Layout(width='150px')
            )
        ]
        
        # Create row with horizontal box - no horizontal overflow
        row = widgets.HBox(
            row_widgets, 
            layout=widgets.Layout(
                width='500px',
                margin='2px 0',
                overflow='hidden',
                min_height='30px'
            )
        )
        
        widgets_list.append(row)
    
    # Update the container's children directly instead of creating a new container
    label_widgets_container.children = widgets_list
    
    # Also update the container's layout to ensure proper sizing
    label_widgets_container.layout.width = '540px'
    label_widgets_container.layout.height = '340px'
    label_widgets_container.layout.padding = '10px'
    label_widgets_container.layout.overflow = 'auto'

update_label_order_widgets(available_data_variables, label_widgets_container)
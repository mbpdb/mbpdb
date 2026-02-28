# Initialize the data transformer
data_transformer = DataTransformation()
heatmap_data_handler = HeatmapDataHandler(data_transformer)
plot_handler = HeatmapPlotHandler(data_transformer)

data_transformer.setup_data_loading_ui()

# Initialize and display the visualization handler
viz_handler = DynamicVisualizationHandler(data_transformer)
viz_handler.display()
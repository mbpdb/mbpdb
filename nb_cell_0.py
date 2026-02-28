# Core data processing libraries
import pandas as pd
import numpy as np

# Visualization libraries
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
from matplotlib.colors import Normalize
import matplotlib.lines as mlines
import matplotlib.patches as patches
import seaborn as sns
from itertools import cycle

# Utility imports
import re, io, warnings, os, copy, base64, gc, traceback, time
from io import BytesIO
from functools import partial
from itertools import combinations
from pathlib import Path

# Jupyter-specific imports
from traitlets import HasTraits, Instance, observe
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from ipywidgets import (
    interact, interactive, fixed, interact_manual,
    GridspecLayout, VBox, HBox, Layout, Output
)
#from ipydatagrid import DataGrid

# Initialize settings
import _settings as settings
from utils.uniprot_client import UniProtClient
warnings.simplefilter(action='ignore', category=FutureWarning)

# Declare global variables
global spec_translate_list, valid_discrete_cmaps, valid_gradient_cmaps
global default_hm_color, default_lp_color, default_avglp_color
global hm_selected_color, cmap, lp_selected_color
global avglp_selected_color, avg_cmap, port_hm_settings
global chuck_size, plot_heatmap, plot_zero, legend_title
global data_transformer, HeatmapPlotHandler

def initialize_global_variables():
    """Initialize all global variables used in the notebook."""
    global spec_translate_list, valid_discrete_cmaps, valid_gradient_cmaps
    global default_hm_color, default_lp_color, default_avglp_color
    global hm_selected_color, cmap, lp_selected_color
    global avglp_selected_color, avg_cmap, port_hm_settings
    global chuck_size, plot_heatmap, plot_zero, legend_title
    global data_transformer, HeatmapPlotHandler
    
    # Global variables from settings
    spec_translate_list = settings.SPEC_TRANSLATE_LIST
    valid_discrete_cmaps = settings.valid_discrete_cmaps
    valid_gradient_cmaps = settings.all_gradient_cmaps
    
    # Define default values for the color maps
    default_hm_color = 'RdYlGn_r'
    #default_hm_color = 'Purples'
    
    default_lp_color = 'Set3'
    default_avglp_color = 'Dark2'
    
    # Define the color map for the heatmap
    hm_selected_color = default_hm_color
    cmap = plt.get_cmap(hm_selected_color)
    
    # Define the color map for the individual line plots
    lp_selected_color = default_lp_color
    
    # Define the color for the averaged line plots
    avglp_selected_color = default_avglp_color
    avg_cmap = plt.get_cmap(avglp_selected_color)
    
    # Define settings for different numbers of variables
    port_hm_settings = {
        #num_var: (lineplot_height, scale_factor)
        1: (35, 0.075),
        2: (20, 0.125),
        3: (20, 0.15),
        4: (20, 0.175),
        5: (20, 0.225),
        6: (20, 0.25),
        7: (20, 0.275),
        8: (20, 0.3),
        9: (20, 0.325),
        10: (20, 0.36),
        11: (20, 0.38),
        12: (20, 0.41)
    }
    
    chuck_size = 78
    plot_heatmap, plot_zero = 'yes', 'no'
    legend_title = ['Sample Type:','Peptide Counts:','Bioactivity Function:','Peptide Interval:', 'Average Abundance:']
    
    data_transformer = HeatmapPlotHandler = None

# Call the function to initialize all global variables
initialize_global_variables()

import matplotlib.pyplot as plt

# List of valid discrete colormaps based on the provided image
valid_discrete_cmaps = [
    'Accent', 'Dark2', 'Paired', 'Pastel1', 'Pastel2', 
    'Set1', 'Set2', 'Set3', 'tab10', 'tab20', 'tab20b', 'tab20c'
]

# Provided list of gradient colormaps
valid_gradient_cmaps = [
    'Blues', 'BrBG', 'BuGn', 'BuPu', 'CMRmap', 'GnBu', 'Greens', 'Greys', 'OrRd', 
    'Oranges', 'PRGn', 'PiYG', 'PuBu', 'PuBuGn', 'PuOr', 'PuRd', 'Purples', 'RdBu', 
    'RdGy', 'RdPu', 'RdYlBu', 'RdYlGn', 'Reds', 'Spectral', 'Wistia', 'YlGn', 'YlGnBu', 
    'YlOrBr', 'YlOrRd', 'afmhot', 'autumn', 'binary', 'bone', 'brg', 'bwr', 'cool', 
    'coolwarm', 'copper', 'cubehelix', 'flag', 'gist_earth', 'gist_gray', 'gist_heat', 
    'gist_ncar', 'gist_rainbow', 'gist_stern', 'gist_yarg', 'gnuplot', 'gnuplot2', 'gray', 
    'hot', 'hsv', 'jet', 'nipy_spectral', 'ocean', 'pink', 'prism', 'rainbow', 'seismic', 
    'spring', 'summer', 'terrain', 'winter', 'grey', 'gist_grey', 'gist_yerg', 'Grays',
    'Blues_r', 'BrBG_r', 'BuGn_r', 'BuPu_r', 'CMRmap_r', 'GnBu_r', 'Greens_r', 'Greys_r', 
    'OrRd_r', 'Oranges_r', 'PRGn_r', 'PiYG_r', 'PuBu_r', 'PuBuGn_r', 'PuOr_r', 'PuRd_r', 
    'Purples_r', 'RdBu_r', 'RdGy_r', 'RdPu_r', 'RdYlBu_r', 'RdYlGn_r', 'Reds_r', 
    'Spectral_r', 'Wistia_r', 'YlGn_r', 'YlGnBu_r', 'YlOrBr_r', 'YlOrRd_r', 'afmhot_r', 
    'autumn_r', 'binary_r', 'bone_r', 'brg_r', 'bwr_r', 'cool_r', 'coolwarm_r', 'copper_r', 
    'cubehelix_r', 'flag_r', 'gist_earth_r', 'gist_gray_r', 'gist_heat_r', 'gist_ncar_r', 
    'gist_rainbow_r', 'gist_stern_r', 'gist_yarg_r', 'gnuplot_r', 'gnuplot2_r', 'gray_r', 
    'hot_r', 'hsv_r', 'jet_r', 'nipy_spectral_r', 'ocean_r', 'pink_r', 'prism_r', 
    'rainbow_r', 'seismic_r', 'spring_r', 'summer_r', 'terrain_r', 'winter_r'
]

# plot;y color schemes
plotly_colors = [
                ('Viridis', 'Viridis'), ('Cividis', 'Cividis'),
                ('Inferno', 'Inferno'), ('Magma', 'Magma'),
                ('Plasma', 'Plasma'), ('Warm', 'Warm'),
                ('Cool', 'Cool'), ('Hot', 'Hot'),
                ('Jet', 'Jet'), ('Blues', 'Blues'),
                ('Bluered', 'Bluered'), ('Blugrn', 'Blugrn'),
                ('Greens', 'Greens'), ('Gnbu', 'GnBu'),
                ('Purples', 'Purples'), ('Pubu', 'PuBu'),
                ('Purd', 'PuRd'), ('Purp', 'Purp'),
                ('Oranges', 'Oranges'), ('Reds', 'Reds'),
                ('Orrd', 'OrRd'), ('Spectral', 'Spectral'),
                ('RdBu', 'RdBu'), ('RdYlBu', 'RdYlBu'),
                ('RdYlGn', 'RdYlGn'), ('PiYG', 'PiYG'),
                ('PRGn', 'PRGn'), ('BrBG', 'BrBG'),
                ('RdGy', 'RdGy'), ('Rainbow', 'Rainbow'),
                ('IceFire', 'IceFire'), ('Edge', 'Edge'),
                ('HSV', 'HSV'), ('Twilight', 'Twilight'),
                ('Mrybm', 'Mrybm'), ('Mygbm', 'Mygbm'),
            ]

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

SPEC_TRANSLATE_LIST = [
    ['Human', 'homo sapiens', 'human'],
    ['Bovine', 'bos taurus', 'bovin'],
    ['Sheep', 'ovis aries'],
    ['Goat', 'capra hircus'],
    ['Pig', 'sus scrofa'],
    ['Yak', 'bos mutus'],
    ['Rabbit', 'oryctolagus cuniculus'],
    ['Donkey', 'equus asinus'],
    ['Camel', 'camelus dromedarius'],
    ['Buffalo', 'bubalus bubalis'],
    ['Horse', 'equus caballus'],
    ['Rat', 'rattus norvegicus'],
    ['Fallow deer', 'dama dama'],
    ['Red deer', 'cervus elaphus'],
    ['Reindeer', 'rangifer tarandus'],
    ['American bison', 'bison bison'],
    ['Elephant', 'elephas maximus'],
    ['Mouse', 'mus musculus']
]

legend_title = ['Sample Type:','Peptide Counts:','Bioactivity Function:','Peptide Interval:', 'Average Absorbance:']


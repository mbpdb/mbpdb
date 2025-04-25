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
    # Sequential
    ('Viridis', 'Viridis'), ('Cividis', 'Cividis'),
    ('Inferno', 'Inferno'), ('Magma', 'Magma'),
    ('Plasma', 'Plasma'), ('Hot', 'Hot'),
    ('Jet', 'Jet'), ('Blues', 'Blues'),
    ('Greens', 'Greens'), ('Reds', 'Reds'),
    ('Purples', 'Purples'), ('Oranges', 'Oranges'),
    ('OrRd', 'OrRd'), ('PuRd', 'PuRd'), 
    ('PuBu', 'PuBu'), ('GnBu', 'GnBu'),
    ('BuGn', 'BuGn'), ('BuPu', 'BuPu'),
    
    # Diverging
    ('Spectral', 'Spectral'), ('RdBu', 'RdBu'), 
    ('RdYlBu', 'RdYlBu'), ('RdYlGn', 'RdYlGn'),
    ('PiYG', 'PiYG'), ('PRGn', 'PRGn'), 
    ('BrBG', 'BrBG'), ('RdGy', 'RdGy'),
    
    # Cyclical
    ('IceFire', 'IceFire'), ('Edge', 'Edge'),
    ('HSV', 'HSV'), ('Twilight', 'Twilight'),
    
    # Qualitative (good for categorical data)
    ('Plotly', 'Plotly'), ('D3', 'D3'),
    ('G10', 'G10'), ('T10', 'T10'),
    ('Alphabet', 'Alphabet'), ('Set1', 'Set1'),
    ('Set2', 'Set2'), ('Set3', 'Set3'),
    ('Pastel1', 'Pastel1'), ('Pastel2', 'Pastel2'),
    ('Paired', 'Paired')
]


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
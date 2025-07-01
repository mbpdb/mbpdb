import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def create_preview(html_file, output_file):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Get absolute path to HTML file
    html_path = os.path.abspath(html_file)
    driver.get(f'file://{html_path}')
    
    # Wait for plot to load
    time.sleep(2)
    
    # Get plot element and take screenshot
    plot = driver.find_element('css selector', '.plotly-graph-div')
    plot.screenshot(output_file)
    
    driver.quit()

def main():
    # Create output directory if it doesn't exist
    os.makedirs('previews', exist_ok=True)
    
    # Process scatter plots
    for i in range(1, 3):
        html_file = f'scatter_plot_{i}.html'
        output_file = f'previews/scatter_plot_{i}.png'
        create_preview(html_file, output_file)
    
    # Process protein plots
    for i in range(1, 6):
        html_file = f'protein_plot_{i}.html'
        output_file = f'previews/protein_plot_{i}.png'
        create_preview(html_file, output_file)

if __name__ == '__main__':
    main() 
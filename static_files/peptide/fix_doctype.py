import os

def add_doctype(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add DOCTYPE if not present
    if not content.startswith('<!DOCTYPE html>'):
        content = '<!DOCTYPE html>\n' + content
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Added DOCTYPE to {file_path}")

def main():
    # Process scatter plots
    for i in range(1, 3):
        html_file = f'scatter_plot_{i}.html'
        if os.path.exists(html_file):
            add_doctype(html_file)
    
    # Process protein plots
    for i in range(1, 6):
        html_file = f'protein_plot_{i}.html'
        if os.path.exists(html_file):
            add_doctype(html_file)

if __name__ == '__main__':
    main() 
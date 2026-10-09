import os
import re

base_dir = os.path.dirname(os.path.abspath(__file__))

def clean_file(filepath, pattern, replace_with=''):
    if not os.path.exists(filepath): return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(pattern, replace_with, content, flags=re.MULTILINE | re.IGNORECASE)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Clean PS1 scripts
for ps1_file in ['status.ps1', 'setup.ps1', 'scripts/status.ps1', 'scripts/setup.ps1']:
    clean_file(os.path.join(base_dir, ps1_file), r'^.*firebase.*\\r?\\n', '')

# README
readme_path = os.path.join(base_dir, 'README.md')
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Remove Phase 3
    content = re.sub(r'### Phase 3.*?###', '###', content, flags=re.DOTALL)
    # Remove any line that contains firebase
    lines = content.split('\\n')
    new_lines = [line for line in lines if 'firebase' not in line.lower()]
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write('\\n'.join(new_lines))

print("Cleanup script executed.")

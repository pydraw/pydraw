##################################
# Compile Script
# Compiles pydraw module into single-file script.
# Author: Noah Coetsee
##################################

import os
import time

time_start = time.time()

input_module = 'pydraw'
input_files = []

header_file = 'tools/header.txt'

# open the __init__.py file to read the order in which to write the module
with open(os.path.join(input_module, '__init__.py'), 'r') as file:
    for line in file:
        import_location = line.split(' ')[1]

        # get rid of the pydraw. in 'from pydraw.<file>'
        import_location = import_location.replace(input_module + '.', '')

        input_files.append(os.path.join(input_module, import_location + '.py'))
        print(f'Detected Subpackage {import_location} in module: {input_module}')


output_file = f'compiled/{input_module}.py'

with open(output_file, 'w') as output:
    with open(header_file, 'r') as header:
        header_txt = header.read()
        header_txt += '\n'

        version = 'x.x.x'
        with open('setup.py', 'r') as setup:
            for line in setup:
                if line.strip().startswith('version'):
                    version = line.split('"')[1]

        header_txt = header_txt.replace('{version}', version)
        output.write(header_txt)

    for input_file in input_files:
        with open(input_file, 'r') as file:
            # Replace any module-import statements. It doesn't matter now.
            filtered = file.read().replace(f'from {input_module}', f'# from {input_module}')
            filtered = filtered.replace(f'import {input_module}', f'# import {input_module}')
            filtered = filtered.replace('{version}', '1.0.0')
            output.write(filtered)
            output.write('\n\n')  # double space between files.

print(f'\nCompilation completed in {time.time() - time_start}s')

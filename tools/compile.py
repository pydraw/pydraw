##################################
# Compile Script
# Compiles pydraw module into single-file script.
# Author: Noah Coetsee
##################################

import os
import time


time_start = time.time()
input_files = [
    'pydraw/overload.py',
    'pydraw/errors.py',
    'pydraw/util.py',
    'pydraw/color.py',
    'pydraw/location.py',
    'pydraw/events.py',
    'pydraw/render.py',
    'pydraw/runtime.py',
    'pydraw/backends/tk.py',
    'pydraw/screen.py',
    'pydraw/scene.py',
    'pydraw/objects.py',
]
header_file = 'tools/header.txt'
output_file = 'compiled/pydraw.py'


def version():
    with open('setup.py', 'r') as setup:
        for line in setup:
            if line.strip().startswith('version'):
                return line.split('"')[1]
    return 'x.x.x'


def inline(source):
    lines = []
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith('from pydraw') or stripped.startswith('import pydraw'):
            indent = line[:len(line) - len(stripped)]
            lines.append(indent + '# ' + stripped)
        else:
            lines.append(line.rstrip())
    return '\n'.join(lines)


with open(output_file, 'w') as output:
    with open(header_file, 'r') as header:
        output.write(header.read().replace('{version}', version()))
        output.write('\n\n')

    for input_file in input_files:
        print('Inlining {}'.format(input_file))
        with open(input_file, 'r') as source:
            output.write(inline(source.read()))
            output.write('\n\n')

print('\nCompilation completed in {}s'.format(time.time() - time_start))

import re

filename = 'colors.txt'

with open(filename, 'r') as file:
    with open('output.txt', 'w') as output:
        for line in file:
            newline = ''
            count = 0
            for character in line:
                if character == '\'':
                    if count % 2 == 0:
                        newline = newline + 'Color(\''
                    else:
                        newline = newline + '\')'

                    count += 1
                else:
                    newline = newline + character

            print(newline)

            # modify the line
            output.write(newline)

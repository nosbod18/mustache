from mustache import render, ParseError
import json

template = r'''######## {{name}} ########
# {{&desc}}
rendered = render('{{&template}}', {{&data}}{{^data}}{}{{/data}}{{#partials}}, {{.}}{{/partials}})
print('{{name}}...\x1b[32mok\x1b[0m' if rendered == '{{&expected}}' else '{{name}}...\x1b[31mfail\x1b[0m')

'''


output = 'from mustache import render\n\n'

for suite in ('comments', 'delimiters', 'interpolation', 'inverted', 'sections', 'partials', '~lambdas', '~dynamic-names'):
    with open(f'spec/specs/{suite}.json') as f:
        data = json.loads(f.read())

        try:
            output += render("\n################################################################################\nprint('\\n\\x1b[1;34m{{suite}}\\x1b[0m:')\n################################################################################\n\n", {'suite': suite})
        except ParseError as e:
            print(e.msg)

        for test in data['tests']:
            test['desc'] = test['desc'].replace('\r', r'\r').replace('\n', r'\n')
            test['template'] = test['template'].replace('\\', r'\\').replace('\'', r'\'').replace('\r', r'\r').replace('\n', r'\n')
            test['expected'] = test['expected'].replace('\\', r'\\').replace('\'', r'\'').replace('\r', r'\r').replace('\n', r'\n')

            if isinstance(test['data'], str):
                string = test['data'].replace('"', r'\"')
                test['data'] = f'"{string}"'

            if suite == '~lambdas':
                test['data']['lambda'] = test['data']['lambda']['python']

            try:
                output += render(template, test)
            except ParseError as e:
                print(e.msg)

with open(f'tests.py', 'w') as f:
    f.write(output)
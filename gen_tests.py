import mustache
import json
import re

with open('tests.mustache') as f:
    template = f.read()
    data = {'suites': []}

    for suite in ('comments', 'delimiters', 'interpolation', 'inverted', 'sections', 'partials', '~lambdas', '~dynamic-names'):
        with open(f'spec/specs/{suite}.json') as f:
            tests = json.loads(f.read())['tests']
            data['suites'].append({'name': suite, 'tests': tests})

            for test in tests:
                test['desc'] = test['desc'].replace('\r', r'\r').replace('\n', r'\n')
                test['template'] = test['template'].replace('\\', r'\\').replace('\'', r'\'').replace('\r', r'\r').replace('\n', r'\n')
                test['expected'] = test['expected'].replace('\\', r'\\').replace('\'', r'\'').replace('\r', r'\r').replace('\n', r'\n')

                if isinstance(test['data'], str):
                    string = test['data'].replace('"', r'\"')
                    test['data'] = f'"{string}"'

                if suite == '~lambdas':
                    test['data']['lambda'] = test['data']['lambda']['python']

    try:
        output = mustache.render(template, data)
        output = re.sub("'lambda( .*)?: (.*)'", r"lambda\1: \2", output) # remove quotes surrounding lambdas
    except mustache.ParseError as e:
        print(e.msg)

    with open('tests.py', 'w') as f:
        f.write(output)
import json
import re

stub = '''
######## {0} ########
# {1}
assert mustache.render('{2}', {3}) == '{4}'
'''

names = ['interpolation']

for name in names:
    with open(f'spec/specs/{name}.json', 'r') as f:
        tests = json.loads(f.read())['tests']

    generated = 'import mustache\n\n'

    for test in tests:
        generated += stub.format(
            re.sub(r'\W+', '_', test['name'].lower()),
            test['desc'],
            test['template'].strip(),
            test['data'] if isinstance(test['data'], dict) else [test['data']],
            test['expected'].strip())
        
    with open(f'test.{name}.py', 'w') as f:
        f.write(generated)
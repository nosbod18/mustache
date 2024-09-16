# mustache
Implements all modules required by the spec (comments, delimiters, interpolation, sections, inverted, partials) along with lambdas and dynamic names.

## Usage

### Simple Example
```python
import mustache
import json

def render(output_path, template_path, data_path, partials_dict):
    with open(output_path) as output, open(template_path) as template, open(data_path) as data:
        template = template.read()
        data = json.loads(data.read())
        output.write(mustache.render(template, data, partials_dict))

render('index.html', 'template.mustache', 'data.json', {})
```
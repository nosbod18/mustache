# mustache
Implements all modules required by the spec along with lambdas and dynamic names.

Use `mustache.render(template, data, partials)` to render a template or `mustache.parse(template)` to get a list of nodes to render later. See `gen_tests.py` and `tests.mustache` for an example

To see `mustache` work and run the tests:
```
$ python gen_test.py
$ python tests.py
```
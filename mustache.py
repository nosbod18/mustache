import re

class MustacheError(Exception):
    pass


class Context:
    def __init__(self, *items):
        self.stack = list(items)

    def push(self, data: dict):
        self.stack.append(data)

    def pop(self):
        self.stack.pop()

    def get(self, key: str):
        if key == '.':
            return self.stack[-1] if len(self.stack) > 0 else None

        parts = key.split('.')

        for item in reversed(self._stack):
            result = self._get(item, parts[0])
            if result is not None:
                return result

        for part in parts[1:]:
            result = self._get(result, part)
            if result is None:
                break

        return result
    
    def _get(context, key):
        if isinstance(context, dict) and key in context:
            return context[key]
        elif type(context).__module__ != __builtins__ and hasattr(context, key):
            return getattr(context, key)
        return None


class Node:
    def __init__(self, token: str | None = None):
        self.token = token
        self.children = []

    def __str__(self):
        return self.to_str()

    def add(self, child):
        self.children.append(child)

    def render(self, context: Context) -> str:
        return ''.join(child.render(context) for child in self.children)

    def to_str(self, depth=0):
        output = ['·  ' * depth + f'{self.__class__.__name__}']
        output.extend(child.to_str(depth + 1) for child in self.children)
        return '\n'.join(output)


class Literal(Node):
    def render(self, context: Context) -> str:
        return self.token


class Variable(Node):
    def __init__(self, token: str, escaped: bool):
        super().__init__(token)
        self.escaped = escaped

    def render(self, context: Context) -> str:
        value = context.get(self.token)

        if not value:
            return ''
        else:
            value = str(value)

        if self.escaped:
            return value\
                .replace('&', '&amp;')\
                .replace('"', '&quot;')\
                .replace('<', '&lt;')\
                .replace('>', '&gt;')
        else:
            return value


class Section(Node):
    def __init__(self, token: str, tag: str):
        super().__init__(token)
        self.inverted = (tag == '^')

    def render(self, context: Context) -> str:
        output = []
        value = context.get(self.token)

        if self.inverted:
            value = not value

        if isinstance(value, list):
            for item in value:
                output.extend(self.render_scope(context, item))
        elif isinstance(value, dict):
            output = self.render_scope(context, value)
        elif value:
            output = self.render_scope(context, None)

        return ''.join(output)
    
    def render_scope(self, context: Context, scope: dict | None) -> str:
        context.push(scope)
        output = [child.render(context) for child in self.children]
        context.pop()
        return output


def _advance(template: str, substr: str) -> tuple[str, str]:
    try:
        token, template = template.split(substr, 1)
        return (token, template)
    except ValueError:
        return (template, '')


def _tokenize(template: str):# -> list[tuple[str, str]]:
    template = re.sub(r'\s+', ' ', template)
    template = template.strip()

    TAGS = ['!', '{', '&', '#', '^', '/']
    tokens = []

    while template:
        token, template = _advance(template, '{{')

        if token:
            tokens.append((token, ''))
            if not template:
                break

        token, template = _advance(template, '}}')
        tag = token[0]
        token = token.strip()

        if tag in TAGS:
            token = token[1:]

        if tag == '{':
            if not template:
                raise MustacheError('Unclosed "{{{"')
            elif template[0] == '}':
                template = template[1:]
                tag = '&'

        tokens.append((token, tag))

    return tokens


def parse(template: str) -> Node:
    ast = [Node()]

    for token, tag in _tokenize(template):
        scope = ast[-1]

        if not tag:
            scope.add(Literal(token))
        elif tag in ['#', '^']:
            node = Section(token, tag)
            scope.add(node)
            ast.append(node)
        elif tag == '/':
            ast.pop()
        else:
            scope.add(Variable(token, tag != '&'))

    return ast.pop()


def render(template: str, data):
    ast = parse(template)
    return ast.render(Context(data))


print(render('Hello, {{.}}!', ['world']))
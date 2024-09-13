import html
import textwrap

class Span:
    def __init__(self, start, end):
        self.start = start
        self.end = end


class ParseError(SyntaxError):
    def __init__(self, msg, span, template):
        line = Span(template.rfind('\n', 0, span.start) + 1, template.find('\n', span.start))
        row = template.count('\n', 0, span.start) + 1
        col = span.start - line.start + 4 # 4 leading spaces

        msg = f'{msg}, line {row}\n    {template[line.start:(line.end if line.end != -1 else len(template))]}\n' + ' ' * col + '^' * (span.end - span.start - 1)
        super().__init__(msg)


class Context(list):
    def get(self, key, default = None):
        if key == '.':
            return self[-1]

        chain = key.split('.')
        value = None

        for scope in reversed(self):
            value = self.scoped_get(chain[0], scope, default)
            if value is not default:
                break

        for link in chain[1:]:
            value = self.scoped_get(link, value, default)
            if not value:
                break

        return value

    def scoped_get(self, key, scope, default = None):
        if callable(scope):
            scope = scope()
        if isinstance(scope, dict):
            return scope[key] if key in scope else default
        if isinstance(scope, list):
            return scope[int(key)] if key.isdigit() and int(key) < len(scope) else default
        return getattr(scope, key, default)


class Node:
    def __init__(self, token, key, tag, template, delims):
        s = template[key.start:key.end]

        self._token = token
        self._key = Span(key.start + (len(s) - len(s.lstrip())), key.end - (len(s) - len(s.rstrip())))
        self._tag = tag
        self._template = template
        self.delims = delims

        line = Span(template.rfind('\n', 0, token.start) + 1, template.find('\n', token.end) + 1 or len(template))
        self.before = template[line.start:token.start]
        self.after = template[token.end:line.end]
        self.standalone = (not self.before or self.before.isspace()) and (not self.after or self.after.isspace())
        self.span = line if not isinstance(self, Interpolation) and self.standalone else Span(token.start, token.end) # copy token so changes to self.span don't affect token

    def __repr__(self):
        return f"{type(self).__name__}('{self.key}')"

    @property
    def tag(self):
        return self._template[self._tag]

    @property
    def key(self):
        return self._template[self._key.start:self._key.end]

    @property
    def token(self):
        return self._template[self._token.start:self._token.end]

    def render(self, ctx, partials):
        return ''


class Literal(Node):
    def __init__(self, token, template):
        super().__init__(token, token, token.start, template, ['', ''])

    def __repr__(self):
        token = self.token.replace('\n', r'\n')
        return f"Literal('{token}')"

    def render(self, ctx, partials):
        return self.token


class Interpolation(Node):
    def render(self, ctx, partials):
        value = ctx.get(self.key)
        if callable(value):
            value = render(str(value()), ctx, partials) if value.__name__ == '<lambda>' else value()
        return html.escape(value) if self.tag not in ('&', '{') and isinstance(value, str) else str(value or '')


class Section(Node):
    def __init__(self, token, key, tag, template, delims):
        super().__init__(token, key, tag, template, delims)
        self.body = parse(template, delims, self.span.end, self.key)

        if len(self.body) == 0 or self.body[-1].tag != '/':
            raise ParseError(f"Section '{self.tag + self.key}' was not closed", self.span, template)

        self.closing = self.body.pop()
        self.text = template[self.span.end:self.closing.span.start]
        self.span.end = self.closing.span.end

    def __repr__(self):
        return f'{super().__repr__()}: {self.body}'

    def render(self, ctx, partials):
        value = ctx.get(self.key)
        if (self.tag == '#' and not value) or (self.tag == '^' and value):
            return ''

        if self.tag == '^':
            return render(self.body, ctx, partials, self.delims)

        if callable(value):
            if value.__name__ == '<lambda>':
                return render(str(value(self.text)), ctx, partials, self.delims)
            return value(self.text, lambda template, data=None: render(template, Context(ctx + [data]) if data else ctx, partials, self.delims))

        if not isinstance(value, list):
            value = [value]

        return ''.join(render(self.body, Context(ctx + [item]), partials, self.delims) for item in value)


class Partial(Node):
    def render(self, ctx, partials):
        value = partials.get(ctx.get(self.key[1:].strip()) if self.key[0] == '*' else self.key)
        if self.standalone:
            value = textwrap.indent(value, self.before)
        return render(value, ctx, partials) if value else ''


class Delimiter(Node):
    def __init__(self, token, key, tag, template, delims):
        super().__init__(token, key, tag, template, delims)
        self.delims = self.key.split()
        if len(self.delims) != 2:
            raise ParseError('Invalid delimiters', token, template)


NODES = {'&': Interpolation, '{': Interpolation, '#': Section, '^': Section, '>': Partial, '=': Delimiter, '/': Node, '!': Node}


def next_token(template, delims, index):
    token = Span(template.find(delims[0], index), len(template))
    if token.start == -1:
        return None

    token.end = template.find(delims[1], token.start + len(delims[0])) + len(delims[1])
    if token.end == -1 + len(delims[1]) or token.end > len(template):
        raise ParseError(f"'{delims[1]}' was never closed", Span(token.start, len(template)), template)

    key = Span(token.start + len(delims[0]), token.end - len(delims[1]))
    if key.start > len(template):
        raise ParseError(f"'{delims[0]}' was never closed", token, template)

    tag = key.start
    if template[tag] in NODES:
        key.start += 1

    return token, key, tag


def parse(template, delims = ['{{', '}}'], index = 0, current_section_key = None):
    ast = []

    while index < len(template):
        token = next_token(template, delims, index)
        if token is None:
            if index < len(template):
                ast.append(Literal(Span(index, len(template)), template))
            break
        token, key, tag = token

        if template[tag] == '{' and delims == ['{{', '}}']:
            if token.end >= len(template) or template[token.end] != '}':
                raise ParseError("Expected '{'", token, template)
            token.end += 1

        if template[tag] == '=':
            key.end -= 1
            if template[key.end] != '=':
                raise ParseError("Expected '='", token, template)

        node = NODES.get(template[tag], Interpolation)(token, key, tag, template, delims)

        if node.span.start > index:
            ast.append(Literal(Span(index, node.span.start), template))
        ast.append(node)

        if node.tag == '/':
            if node.key != current_section_key:
                raise ParseError(f"Section '{node.tag + node.key}' was not opened", token, template)
            break

        index = node.span.end

        if type(node) is Delimiter:
            delims = node.delims

    return ast


def render(template_or_ast, data = {}, partials = {}, delims = ['{{', '}}']):
    ast = parse(template_or_ast, delims) if type(template_or_ast) is str else template_or_ast
    ctx = Context([data]) if type(data) is not Context else data
    return ''.join(node.render(ctx, partials) for node in ast)
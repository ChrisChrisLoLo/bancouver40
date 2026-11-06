"""Minimal KiCad s-expression reader/writer (lists of str/Sym, strings keep quotes info)."""
import re

class Sym(str):
    """bare symbol (unquoted atom)"""

_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)

def parse(text):
    stack, cur = [], []
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == '':
                break
            raise ValueError('bad token at %d: %r' % (pos, text[pos:pos + 40]))
        pos = m.end()
        if m.group(1):
            stack.append(cur); cur = []
        elif m.group(2):
            done = cur; cur = stack.pop(); cur.append(done)
        elif m.group(3) is not None:
            cur.append(m.group(3).replace('\\"', '"').replace('\\\\', '\\'))
        else:
            cur.append(Sym(m.group(4)))
    return cur[0] if len(cur) == 1 else cur

def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

def dump(x, ind=0):
    if isinstance(x, list):
        if not x:
            return '()'
        simple = all(not isinstance(e, list) for e in x)
        if simple and len(x) < 12:
            return '(' + ' '.join(dump(e) for e in x) + ')'
        out = '(' + dump(x[0])
        for e in x[1:]:
            if isinstance(e, list):
                out += '\n' + '\t' * (ind + 1) + dump(e, ind + 1)
            else:
                out += ' ' + dump(e)
        return out + '\n' + '\t' * ind + ')'
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, (int, float)):
        return fmt(x)
    return q(x)

def fmt(v):
    if isinstance(v, int):
        return str(v)
    s = ('%.6f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s

def find(x, key):
    """first child list starting with key"""
    for e in x:
        if isinstance(e, list) and e and e[0] == key:
            return e
    return None

def findall(x, key):
    return [e for e in x if isinstance(e, list) and e and e[0] == key]

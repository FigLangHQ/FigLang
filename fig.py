import sys
from lexer import tokenize
from parser import parse
from runtime import Runtime

FIGLANG_HINTS = {
    'saay':      'say',
    'iff':       'if',
    'iss':       'is',
    'sayy':      'say',
    'otherewise':'otherwise',
    'otherwisse':'otherwise',
    'repeet':    'repeat',
    'tmes':      'times',
    'timees':    'times',
    'wheneever': 'whenever',
    'untill':    'until',
    'assk':      'ask',
    'mor than':  'is above',
    'more than': 'is above',
    'less than': 'is below',
    'greater than': 'is above',
    'same as':   'is',
    'equals':    'is',
    'equal to':  'is',
    'otherwise if': 'but if',
    'else if':   'but if',
    'else':      'otherwise',
    'elif':      'but if',
    'print':     'say',
    'echo':      'say',
    'input':     'ask',
    'var':       'just write: name is value',
    'let':       'just write: name is value',
    'const':     'just write: name is value',
    'def ':      'zone called',
    'function':  'zone called',
    'return':    'give back',
    'while':     'until',
    'for ':      'for each',
    'foreach':   'for each',
}

def suggest(source):
    suggestions = []
    lines = source.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.strip().lower()
        for wrong, correct in FIGLANG_HINTS.items():
            if wrong in stripped:
                suggestions.append(
                    f"  line {i}: did you mean '{correct}' "
                    f"instead of '{wrong}'?"
                )
    return suggestions

def format_error(kind, msg, line=None):
    print()
    print('=' * 50)
    print(f'  FigLang {kind}')
    if line:
        print(f'  on line {line}')
    print(f'  {msg}')
    print('=' * 50)
    print()

def main():
    if len(sys.argv) < 2:
        print("Usage: python fig.py yourfile.fig")
        return

    filename = sys.argv[1]

    try:
        with open(filename, 'r') as f:
            source = f.read()
    except FileNotFoundError:
        format_error('Error', f"file '{filename}' not found")
        return

    # controlla suggerimenti sulla sintassi
    hints = suggest(source)

    try:
        tokens = tokenize(source)
    except SyntaxError as e:
        msg = str(e)
        format_error('Syntax Error', msg)
        if hints:
            print('  Hints:')
            for h in hints: print(h)
        return

    try:
        ast = parse(tokens)
    except SyntaxError as e:
        msg = str(e)
        # estrai il numero di linea dal messaggio
        line = None
        if 'line' in msg:
            try:
                line = msg.split('line')[-1].strip().split()[0]
            except: pass
        format_error('Syntax Error', msg, line)
        if hints:
            print('  Hints:')
            for h in hints: print(h)
        return

    runtime = Runtime()

        # warnings
    try:
        from warnings_fig import analyze
        warns = analyze(ast, source)
        if warns:
            print()
            for w in warns:
                print(f'  [!] {w}')
            print()
    except Exception:
        pass

    try:
        runtime.run(ast)
    except NameError as e:
        msg = str(e)
        format_error('Error', msg)
        # suggerisci variabili simili
        var_name = msg.split("'")[1] if "'" in msg else None
        if var_name:
            similar = [
                k for k in runtime.variables.keys()
                if k.startswith(var_name[0])
            ]
            if similar:
                print(f"  Did you mean one of: {', '.join(similar)}?")
                print()
    except ValueError as e:
        format_error('Value Error', str(e))
    except FileNotFoundError as e:
        format_error('File Error', str(e))
    except ZeroDivisionError:
        format_error('Math Error', 'cannot divide by zero')
    except RecursionError:
        format_error('Loop Error', 'infinite loop detected')
    except TypeError as e:
        msg = str(e)
        if 'str' in msg and 'int' in msg:
            format_error('Type Error',
                'cannot do math between text and number\n'
                '  make sure both values are numbers')
        else:
            format_error('Type Error', msg)
    except Exception as e:
        format_error('Error', str(e))

main()
def analyze(ast, source):
    warnings = []
    lines = source.split('\n')

    assigned = set()
    used = set()
    whenevers = []
    requires = {}

    def check_node(node):
        if node is None:
            return
        kind = node[0]

        if kind == 'assign':
            assigned.add(node[1])

        elif kind == 'say':
            _collect_vars(node[1], used)

        elif kind == 'if':
            _, cond, body, elifs, else_body = node
            _collect_vars_cond(cond, used)
            for s in body: check_node(s)
            for ec, eb in elifs:
                _collect_vars_cond(ec, used)
                for s in eb: check_node(s)
            for s in else_body: check_node(s)

        elif kind == 'whenever':
            _, cond, body = node
            whenevers.append((cond, body))
            _collect_vars_cond(cond, used)
            for s in body: check_node(s)

        elif kind == 'repeat':
            _, n, body = node
            _collect_vars(n, used)
            # warning: repeat 0 times
            if n == ('number', 0):
                warnings.append(
                    'Warning: repeat 0 times does nothing'
                )
            for s in body: check_node(s)

        elif kind == 'until':
            _, cond, body = node
            _collect_vars_cond(cond, used)
            body_assigns = [s for s in body if s and s[0] == 'assign']
            cond_vars = set()
            _collect_vars_cond(cond, cond_vars)
            body_var_names = {s[1] for s in body_assigns}
            if cond_vars and not cond_vars.intersection(body_var_names):
                warnings.append(
                    f'Warning: possible infinite loop in "until" - '
                    f'condition variables {cond_vars} never change in body'
                )
            for s in body: check_node(s)

        elif kind == 'require':
            _, name, constraints = node
            requires[name] = constraints

        elif kind == 'for_each':
            _, var, col, body = node
            assigned.add(var)
            _collect_vars(col, used)
            for s in body: check_node(s)

        elif kind == 'zone_def':
            _, name, body = node
            assigned.add(name)
            for s in body: check_node(s)

    for stmt in ast:
        check_node(stmt)

    # variabili assegnate ma mai usate
    never_used = assigned - used - {'it'}
    for var in never_used:
        warnings.append(
            f'Warning: variable "{var}" is assigned but never used'
        )

    # variabili con require ma mai assegnate
    for name in requires:
        if name not in assigned:
            warnings.append(
                f'Warning: require on "{name}" but "{name}" '
                f'is never assigned'
            )

    return warnings


def _collect_vars(expr, used):
    if expr is None or not isinstance(expr, tuple):
        return
    if expr[0] == 'var':
        used.add(expr[1])
    elif expr[0] == 'binop':
        _collect_vars(expr[2], used)
        _collect_vars(expr[3], used)
    elif expr[0] in ('memory', 'highest_of', 'lowest_of',
                     'collection_op', 'str_op'):
        if len(expr) > 2:
            used.add(expr[2])
    elif expr[0] == 'list':
        for item in expr[1]:
            _collect_vars(item, used)


def _collect_vars_cond(cond, used):
    if cond is None or not isinstance(cond, tuple):
        return
    kind = cond[0]
    if kind in ('compare', 'between', 'is_empty',
                'not_empty', 'trend', 'hits', 'changes',
                'contains', 'starts_with'):
        _collect_vars(cond[1], used)
        if len(cond) > 2 and isinstance(cond[2], tuple):
            _collect_vars(cond[2], used)
        if len(cond) > 3 and isinstance(cond[3], tuple):
            _collect_vars(cond[3], used)
    elif kind == 'logical':
        _collect_vars_cond(cond[2], used)
        _collect_vars_cond(cond[3], used)
    elif kind == 'expr_cond':
        _collect_vars(cond[1], used)
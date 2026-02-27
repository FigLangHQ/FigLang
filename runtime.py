import time
import json
import os
import re
import random
from datetime import datetime


class Variable:
    def __init__(self, value, certainty='definitely'):
        self.value = value
        self.certainty = certainty
        self.history = [value]
        self.limits = []
        self.annotations = {}

    def set(self, value, certainty='definitely'):
        old = self.value
        self.value = value
        self.certainty = certainty
        self.history.append(value)
        self._apply_limits()
        return old

    def _apply_limits(self):
        for d, lim in self.limits:
            if d == 'below' and self.value < lim: self.value = lim
            elif d == 'above' and self.value > lim: self.value = lim

    def previous(self):
        return self.history[-2] if len(self.history) >= 2 else self.value

    def highest(self):
        n = [x for x in self.history if isinstance(x, (int, float))]
        return max(n) if n else self.value

    def lowest(self):
        n = [x for x in self.history if isinstance(x, (int, float))]
        return min(n) if n else self.value

    def is_going_up(self):
        return len(self.history) >= 2 and self.history[-1] > self.history[-2]

    def is_going_down(self):
        return len(self.history) >= 2 and self.history[-1] < self.history[-2]


class Runtime:
    def __init__(self):
        self.variables = {}
        self.zones = {}
        self.roles = {}
        self.whenevers = []
        self.every_counters = {}
        self.everys = []
        self.watchers = set()
        self.requires = {}
        self.states = {}
        self.state_transitions = {}
        self.state_current = {}
        self.reactions = {}
        self.snapshots = {}
        self.groups = {}
        self.tables = {}
        self.maps = {}
        self.aliases = {}
        self.logs = []
        self.debug_mode = False
        self.timer_start = None
        self.timer_value = 0
        self.elapsed = 0

    def run(self, statements):
        for s in statements:
            self.execute(s)

    def execute(self, stmt):
        if stmt is None: return
        kind = stmt[0]
        if self.debug_mode: print(f"  [debug] {kind}")

        # Check alias first
        if kind == 'call_method' and stmt[2] in self.aliases:
            for s in self.aliases[stmt[2]]:
                self.execute(s)
            return

        dispatch = {
            'assign': self.exec_assign, 'say': self.exec_say,
            'say_transform': self.exec_say_transform,
            'say_context': self.exec_say_context,
            'ask': self.exec_ask, 'if': self.exec_if,
            'until': self.exec_until, 'given': self.exec_given,
            'repeat': self.exec_repeat, 'count': self.exec_count,
            'for_each': self.exec_for_each,
            'whenever': self.exec_whenever_def,
            'every': self.exec_every_def,
            'assume': self.exec_assume, 'require': self.exec_require,
            'set_limits': self.exec_set_limits,
            'pipeline': self.exec_pipeline, 'try': self.exec_try,
            'zone_def': self.exec_zone_def, 'do_zone': self.exec_do_zone,
            'role_def': self.exec_role_def,
            'watch': self.exec_watch, 'unwatch': self.exec_unwatch,
            'explain': self.exec_explain, 'debug': self.exec_debug,
            'snapshot_take': self.exec_snapshot_take,
            'snapshot_restore': self.exec_snapshot_restore,
            'remember': self.exec_remember, 'recall': self.exec_recall,
            'forget': self.exec_forget, 'check': self.exec_check,
            'listen': self.exec_listen,
            'use': self.exec_use,
            'measure_time': self.exec_measure_time,
            'wait': self.exec_wait,
            'react': self.exec_react,
            'state_def': self.exec_state_def,
            'state_start': self.exec_state_start,
            'state_become': self.exec_state_become,
            'state_transition': self.exec_state_transition,
            'annotate': self.exec_annotate,
            'group_def': self.exec_group_def,
            'add_to_group': self.exec_add_to_group,
            'link': self.exec_link,
            'read_file': self.exec_read_file,
            'write_file': self.exec_write_file,
            'append_file': self.exec_append_file,
            'lines_of': self.exec_lines_of,
            'table_def': self.exec_table_def,
            'map_def': self.exec_map_def,
            'show_list': self.exec_show_list,
            'show_bar': self.exec_show_bar,
            'show_sorted': self.exec_show_sorted,
            'validate': self.exec_validate,
            'log': self.exec_log,
            'save_logs': self.exec_save_logs,
            'after': self.exec_after,
            'start_timer': self.exec_start_timer,
            'stop_timer': self.exec_stop_timer,
            'compare_vals': self.exec_compare,
            'alias': self.exec_alias,
            'chain': self.exec_chain,
            'clamp': self.exec_clamp,
            'expr': lambda s: self.evaluate(s[1]),
        }
        h = dispatch.get(kind)
        if h: h(stmt)

    # ─── ASSIGN ────────────────────────────────────────
    def exec_assign(self, stmt):
        _, name, val_expr, certainty = stmt
        value = self.evaluate(val_expr)
        old = None
        if name in self.variables:
            old = self.variables[name].set(value, certainty)
        else:
            self.variables[name] = Variable(value, certainty)
        if self.debug_mode:
            print(f"  [assign] {name} = {value}")
        if name in self.watchers and old is not None and old != value:
            print(f"  [watch] {name} changed: {old} -> {value}")
        if name in self.requires:
            for c in self.requires[name]:
                self.check_constraint(name, value, c)
        self.check_whenevers()
        self.check_everys(name)
        self.check_reactions(name)
        

    # ─── SAY ───────────────────────────────────────────
    def exec_say(self, stmt):
        _, expr = stmt
        print(self.to_string(self.evaluate(expr)))

    def exec_say_transform(self, stmt):
        _, expr, transform = stmt
        v = self.to_string(self.evaluate(expr))
        if transform == 'uppercase':    print(v.upper())
        elif transform == 'lowercase':  print(v.lower())
        elif transform == 'capitalized': print(v.title())

    def exec_say_context(self, stmt):
        _, expr = stmt
        name = expr[1] if expr[0] == 'var' else None
        value = self.evaluate(expr)
        if name and name in self.variables:
            var = self.variables[name]
            a = var.annotations
            out = f"{name}"
            if a.get('owned_by'): out += f" ({a['owned_by']}'s)"
            if a.get('described_as'): out += f" [{a['described_as']}]"
            out += f": {self.to_string(value)}"
            if a.get('measured_in'): out += f" {a['measured_in']}"
            print(out)
        else:
            print(self.to_string(value))

    # ─── ASK ───────────────────────────────────────────
    def exec_ask(self, stmt):
        _, prompt, name = stmt
        answer = self._try_number(input(prompt + " "))
        self.variables[name] = Variable(answer)

    # ─── IF ────────────────────────────────────────────
    def exec_if(self, stmt):
        _, cond, body, elifs, else_body = stmt
        if self.eval_condition(cond):
            for s in body: self.execute(s)
            return
        for ec, eb in elifs:
            if self.eval_condition(ec):
                for s in eb: self.execute(s)
                return
        for s in else_body: self.execute(s)

    # ─── UNTIL ─────────────────────────────────────────
    def exec_until(self, stmt):
        _, cond, body = stmt
        i = 0
        while not self.eval_condition(cond):
            for s in body: self.execute(s)
            i += 1
            if i >= 10000:
                print("FigLang: until loop exceeded max iterations"); break

    # ─── GIVEN ─────────────────────────────────────────
    def exec_given(self, stmt):
        _, cond, body = stmt
        if self.eval_condition(cond):
            for s in body: self.execute(s)

    # ─── REPEAT ────────────────────────────────────────
    def exec_repeat(self, stmt):
        _, n_expr, body = stmt
        for _ in range(int(self.evaluate(n_expr))):
            for s in body: self.execute(s)

    # ─── COUNT ─────────────────────────────────────────
    def exec_count(self, stmt):
        _, s_expr, e_expr, body = stmt
        for i in range(int(self.evaluate(s_expr)), int(self.evaluate(e_expr)) + 1):
            self.variables['it'] = Variable(i)
            for s in body: self.execute(s)

    # ─── FOR EACH ──────────────────────────────────────
    def exec_for_each(self, stmt):
        _, var, col_expr, body = stmt
        col = self.evaluate(col_expr)
        if isinstance(col, list):
            for item in col:
                self.variables[var] = Variable(item)
                self.variables['it'] = Variable(item)
                for s in body: self.execute(s)

    # ─── WHENEVER ──────────────────────────────────────
    def exec_whenever_def(self, stmt):
        _, cond, body = stmt
        self.whenevers.append((cond, body))

    def check_whenevers(self):
        for cond, body in self.whenevers:
            if self.eval_condition(cond):
                for s in body: self.execute(s)

    # ─── EVERY ─────────────────────────────────────────
    def exec_every_def(self, stmt):
        _, n_expr, name, body = stmt
        n = int(self.evaluate(n_expr))
        entry = (n, name, body)
        self.everys.append(entry)
        self.every_counters[id(entry)] = 0

    def check_everys(self, changed):
        for entry in self.everys:
            n, name, body = entry
            if name == changed:
                key = id(entry)
                self.every_counters[key] = self.every_counters.get(key, 0) + 1
                if self.every_counters[key] >= n:
                    self.every_counters[key] = 0
                    for s in body: self.execute(s)

    # ─── ASSUME ────────────────────────────────────────
    def exec_assume(self, stmt):
        _, name, val_expr = stmt
        if name not in self.variables:
            self.variables[name] = Variable(self.evaluate(val_expr))

    # ─── REQUIRE ───────────────────────────────────────
    def exec_require(self, stmt):
        _, name, constraints = stmt
        if name not in self.requires: self.requires[name] = []
        self.requires[name].extend(constraints)

    def check_constraint(self, name, value, c):
        kind = c[0]
        if kind == 'above':
            lim = self.evaluate(c[1])
            if not (value > lim):
                raise ValueError(f"FigLang: '{name}' must be above {lim}, got {value}")
        elif kind == 'below':
            lim = self.evaluate(c[1])
            if not (value < lim):
                raise ValueError(f"FigLang: '{name}' must be below {lim}, got {value}")
        elif kind == 'between':
            lo, hi = self.evaluate(c[1]), self.evaluate(c[2])
            if not (lo <= value <= hi):
                raise ValueError(f"FigLang: '{name}' must be between {lo} and {hi}, got {value}")
        elif kind == 'not':
            bad = self.evaluate(c[1])
            if value == bad:
                raise ValueError(f"FigLang: '{name}' must not be {bad}, got {value}")
        elif kind == 'not_empty':
            if value == '' or value is None:
                raise ValueError(f"FigLang: '{name}' must not be empty")

    # ─── LIMITS ────────────────────────────────────────
    def exec_set_limits(self, stmt):
        _, name, limits = stmt
        if name not in self.variables:
            self.variables[name] = Variable(0)
        self.variables[name].limits = [(d, self.evaluate(v)) for d, v in limits]

    # ─── PIPELINE ──────────────────────────────────────
    def exec_pipeline(self, stmt):
        _, src_expr, steps = stmt
        data = self.evaluate(src_expr)
        if not isinstance(data, list): data = [data]
        for step in steps:
            if step[0] == 'keep':
                val = self.evaluate(step[2])
                data = [x for x in data if (x > val if step[1] == 'above' else x < val)]
            elif step[0] == 'double':  data = [x * 2 for x in data]
            elif step[0] == 'sort':    data = sorted(data)
            elif step[0] == 'reverse': data = list(reversed(data))
            elif step[0] == 'say_each':
                for item in data: print(self.to_string(item))

    # ─── TRY ───────────────────────────────────────────
    def exec_try(self, stmt):
        _, body, fallback = stmt
        try: self.execute(body)
        except Exception:
            if fallback: self.execute(fallback)

    # ─── ZONE ──────────────────────────────────────────
    def exec_zone_def(self, stmt):
        _, name, body = stmt
        self.zones[name] = body

    def exec_do_zone(self, stmt):
        _, name, again = stmt
        if name in self.zones:
            for s in self.zones[name]: self.execute(s)
        elif name in self.aliases:
            for s in self.aliases[name]: self.execute(s)
        else:
            raise NameError(f"FigLang: zone '{name}' is not defined")

    # ─── ROLE ──────────────────────────────────────────
    def exec_role_def(self, stmt):
        _, name, body = stmt
        self.roles[name] = body

    # ─── WATCH ─────────────────────────────────────────
    def exec_watch(self, stmt):
        _, name = stmt
        self.watchers.add(name)
        print(f"  [watch] now watching '{name}'")

    def exec_unwatch(self, stmt):
        _, name = stmt
        self.watchers.discard(name)
        print(f"  [watch] stopped watching '{name}'")

    # ─── EXPLAIN ───────────────────────────────────────
    def exec_explain(self, stmt):
        _, name = stmt
        if name not in self.variables:
            print(f"FigLang: '{name}' is not defined"); return
        var = self.variables[name]
        v = var.value
        print(f"\n── explain: {name} ──────────────────")
        print(f"  current value   : {self.to_string(v)}")
        print(f"  certainty       : {var.certainty}")
        print(f"  type            : {self._type_name(v)}")
        print(f"  changed         : {len(var.history) - 1} time(s)")
        print(f"  history         : {var.history}")
        if isinstance(v, (int, float)):
            print(f"  highest ever    : {var.highest()}")
            print(f"  lowest ever     : {var.lowest()}")
            t = "going up" if var.is_going_up() else "going down" if var.is_going_down() else "stable"
            print(f"  trend           : {t}")
        if len(var.history) >= 2:
            print(f"  previous value  : {var.previous()}")
        if var.limits: print(f"  limits          : {var.limits}")
        if var.annotations:
            for k, val in var.annotations.items():
                print(f"  {k:<16}: {val}")
        if name in self.requires:
            print(f"  requirements    : {self.requires[name]}")
        if name in self.state_current:
            print(f"  current state   : {self.state_current[name]}")
            if name in self.states:
                print(f"  possible states : {self.states[name]}")
        print(f"────────────────────────────────────\n")

    # ─── DEBUG ─────────────────────────────────────────
    def exec_debug(self, stmt):
        _, mode = stmt
        self.debug_mode = mode
        print(f"  [debug] {'on' if mode else 'off'}")

    # ─── SNAPSHOT ──────────────────────────────────────
    def exec_snapshot_take(self, stmt):
        _, name = stmt
        snap = {}
        for k, var in self.variables.items():
            snap[k] = {'value': var.value, 'certainty': var.certainty,
                       'history': list(var.history)}
        self.snapshots[name] = snap
        print(f"  [snapshot] saved '{name}'")

    def exec_snapshot_restore(self, stmt):
        _, name = stmt
        if name not in self.snapshots:
            print(f"FigLang: snapshot '{name}' not found"); return
        for k, data in self.snapshots[name].items():
            v = Variable(data['value'], data['certainty'])
            v.history = data['history']
            self.variables[k] = v
        print(f"  [snapshot] restored '{name}'")

    # ─── REMEMBER / RECALL / FORGET ────────────────────
    def exec_remember(self, stmt):
        _, name, key = stmt
        if name not in self.variables: return
        with open(f".figlang_{key}.json", 'w') as f:
            json.dump({'value': self.variables[name].value}, f)
        print(f"  [remember] saved '{name}' as '{key}'")

    def exec_recall(self, stmt):
        _, key, name = stmt
        path = f".figlang_{key}.json"
        if not os.path.exists(path):
            print(f"FigLang: no memory for '{key}'"); return
        with open(path) as f:
            self.variables[name] = Variable(json.load(f)['value'])
        print(f"  [recall] loaded '{key}' into '{name}'")

    def exec_forget(self, stmt):
        _, key = stmt
        path = f".figlang_{key}.json"
        if os.path.exists(path): os.remove(path); print(f"  [forget] deleted '{key}'")
        else: print(f"FigLang: no memory for '{key}'")

    # ─── CHECK ─────────────────────────────────────────
    def exec_check(self, stmt):
        _, cond = stmt
        result = self.eval_condition(cond)
        label = self._condition_label(cond)
        print(f"  {'✓' if result else '✗ FAILED:'} {label}")

    def _condition_label(self, cond):
        kind = cond[0]
        if kind == 'compare':
            _, left, op, right, _ = cond
            ops = {'eq':'is','not_eq':'is not','gt':'is above','lt':'is below',
                'gte':'is at least','lte':'is at most'}
            return f"{self._expr_label(left)} {ops.get(op,op)} {self._expr_label(right)}"
        elif kind == 'between':
            _, left, lo, hi, _ = cond
            return f"{self._expr_label(left)} is between {self._expr_label(lo)} and {self._expr_label(hi)}"
        elif kind == 'is_empty':
            return f"{self._expr_label(cond[1])} is empty"
        elif kind == 'not_empty':
            return f"{self._expr_label(cond[1])} is not empty"
        elif kind == 'contains':
            return f"{self._expr_label(cond[1])} contains {self._expr_label(cond[2])}"
        return str(cond)

    def _expr_label(self, expr):
        if expr is None: return '?'
        if isinstance(expr, (int, float)): return str(expr)
        if isinstance(expr, str): return expr
        if isinstance(expr, bool): return 'true' if expr else 'false'
        if isinstance(expr, tuple):
            if expr[0] == 'var':    return expr[1]
            if expr[0] == 'number': return str(expr[1])
            if expr[0] == 'string': return f'"{expr[1]}"'
            if expr[0] == 'binop' and expr[1] == 'concat':
                return f"{self._expr_label(expr[2])} and {self._expr_label(expr[3])}"
        return str(expr)

    # ─── LISTEN ────────────────────────────────────────
    def exec_listen(self, stmt):
        _, mode, options, name = stmt
        while True:
            raw = input("> ").strip()
            if mode == 'number':
                try:
                    v = float(raw) if '.' in raw else int(raw)
                    self.variables[name] = Variable(v); break
                except ValueError: print("  Please enter a valid number.")
            elif mode == 'yes_no':
                if raw.lower() in ('yes','y'):
                    self.variables[name] = Variable(True); break
                elif raw.lower() in ('no','n'):
                    self.variables[name] = Variable(False); break
                else: print("  Please answer yes or no.")
            elif mode == 'one_of':
                opts = self.evaluate(options)
                if raw in opts:
                    self.variables[name] = Variable(raw); break
                else: print(f"  Choose one of: {', '.join(str(o) for o in opts)}")
            else:
                self.variables[name] = Variable(raw); break

    # ─── MEASURE ───────────────────────────────────────
    def exec_measure_time(self, stmt):
        _, body = stmt
        start = time.time()
        for s in body: self.execute(s)
        self.elapsed = time.time() - start
        self.variables['elapsed_time'] = Variable(round(self.elapsed, 4))

    # ─── WAIT ──────────────────────────────────────────
    def exec_wait(self, stmt):
        _, amt_expr = stmt
        time.sleep(self.evaluate(amt_expr))

    # ─── REACT ─────────────────────────────────────────
    def exec_react(self, stmt):
        _, name, deps, body = stmt
        self.reactions[name] = (deps, body)

    def check_reactions(self, changed):
        for rname, (deps, body) in self.reactions.items():
            if changed in deps:
                for s in body: self.execute(s)

    # ─── STATES ────────────────────────────────────────
    def exec_state_def(self, stmt):
        _, name, states = stmt
        self.states[name] = states
        self.variables[name] = Variable(None)

    def exec_state_start(self, stmt):
        _, name, state = stmt
        if name in self.states and state not in self.states[name]:
            raise ValueError(f"FigLang: '{state}' is not valid for '{name}'")
        self.state_current[name] = state
        self.variables[name] = Variable(state)

    def exec_state_become(self, stmt):
        _, name, new_state = stmt
        current = self.state_current.get(name)
        if name in self.state_transitions:
            allowed = self.state_transitions[name].get(current, [])
            if new_state not in allowed:
                raise ValueError(f"FigLang: '{name}' cannot go from '{current}' to '{new_state}'")
        self.state_current[name] = new_state
        self.variables[name] = Variable(new_state)
        if self.debug_mode: print(f"  [state] {name}: {current} -> {new_state}")

    def exec_state_transition(self, stmt):
        _, name, fr, to = stmt
        if name not in self.state_transitions:
            self.state_transitions[name] = {}
        if fr not in self.state_transitions[name]:
            self.state_transitions[name][fr] = []
        self.state_transitions[name][fr].append(to)

    # ─── ANNOTATE ──────────────────────────────────────
    def exec_annotate(self, stmt):
        _, name, ann = stmt
        if name not in self.variables:
            self.variables[name] = Variable(None)
        self.variables[name].annotations.update(ann)

    # ─── GROUPS ────────────────────────────────────────
    def exec_group_def(self, stmt):
        _, name, item_type = stmt
        self.groups[name] = {'type': item_type, 'items': []}
        self.variables[name] = Variable([])

    def exec_add_to_group(self, stmt):
        _, item_expr, group = stmt
        item = self.evaluate(item_expr)
        if group in self.groups:
            self.groups[group]['items'].append(item)
            self.variables[group].value = self.groups[group]['items']
        elif group in self.variables and isinstance(self.variables[group].value, list):
            self.variables[group].value.append(item)
        else:
            raise NameError(f"FigLang: group '{group}' not defined")

    # ─── LINK ──────────────────────────────────────────
    def exec_link(self, stmt):
        _, name, other, body = stmt
        self.whenevers.append((('changes', ('var', name), None), body))

    # ─── FILES ─────────────────────────────────────────
    def exec_read_file(self, stmt):
        _, fname_expr, var = stmt
        fname = self.to_string(self.evaluate(fname_expr))
        try:
            with open(fname) as f:
                self.variables[var] = Variable(f.read())
        except FileNotFoundError:
            raise FileNotFoundError(f"FigLang: file '{fname}' not found")

    def exec_write_file(self, stmt):
        _, content_expr, fname_expr = stmt
        content = self.to_string(self.evaluate(content_expr))
        fname = self.to_string(self.evaluate(fname_expr))
        with open(fname, 'w') as f: f.write(content)
        print(f"  [file] wrote to '{fname}'")

    def exec_append_file(self, stmt):
        _, content_expr, fname_expr = stmt
        content = self.to_string(self.evaluate(content_expr))
        fname = self.to_string(self.evaluate(fname_expr))
        with open(fname, 'a') as f: f.write(content + '\n')
        print(f"  [file] appended to '{fname}'")

    def exec_lines_of(self, stmt):
        _, fname_expr, var = stmt
        fname = self.to_string(self.evaluate(fname_expr))
        with open(fname) as f:
            self.variables[var] = Variable(f.read().strip().split('\n'))

    # ─── TABLE ─────────────────────────────────────────
    def exec_table_def(self, stmt):
        _, name, rows = stmt
        self.tables[name] = [[self.evaluate(cell) for cell in row] for row in rows]

    # ─── MAP ───────────────────────────────────────────
    def exec_map_def(self, stmt):
        _, name, body = stmt
        m = {}
        for s in body:
            if s and s[0] == 'assign':
                m[s[1]] = self.evaluate(s[2])
        self.maps[name] = m
        self.variables[name] = Variable(m)

    # ─── SHOW ──────────────────────────────────────────
    def exec_show_list(self, stmt):
        _, expr = stmt
        data = self.evaluate(expr)
        if isinstance(data, list):
            for i, item in enumerate(data, 1):
                print(f"  {i}. {self.to_string(item)}")

    def exec_show_bar(self, stmt):
        _, expr = stmt
        data = self.evaluate(expr)
        if isinstance(data, dict):
            mx = max(data.values()) if data else 1
            for k, v in data.items():
                bars = int((v / mx) * 20)
                print(f"  {str(k):<12} | {'█' * bars} {v}")
        elif isinstance(data, list):
            mx = max(data) if data else 1
            for i, v in enumerate(data):
                bars = int((v / mx) * 20)
                print(f"  {i:<12} | {'█' * bars} {v}")

    def exec_show_sorted(self, stmt):
        _, expr, col_expr = stmt
        name = expr[1] if expr[0] == 'var' else None
        if name and name in self.tables:
            col = int(self.evaluate(col_expr)) - 1
            rows = sorted(self.tables[name], key=lambda r: r[col] if col < len(r) else 0)
            for row in rows:
                print("  " + " | ".join(self.to_string(c) for c in row))

    # ─── VALIDATE ──────────────────────────────────────
    def exec_validate(self, stmt):
        _, vtype, expr = stmt
        val = self.to_string(self.evaluate(expr))
        result = False
        if vtype == 'email':
            result = bool(re.match(r'^[\w.-]+@[\w.-]+\.\w+$', val))
        elif vtype == 'url':
            result = bool(re.match(r'^https?://[\w.-]+\.\w+', val))
        elif vtype == 'number':
            try: float(val); result = True
            except: result = False
        print(f"  validate {vtype} \"{val}\": {'true' if result else 'false'}")

    # ─── LOG ───────────────────────────────────────────
    def exec_log(self, stmt):
        _, msg_expr, level = stmt
        msg = self.to_string(self.evaluate(msg_expr))
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        levels = {'info': '', 'warning': 'WARNING: ', 'error': 'ERROR: '}
        entry = f"[{ts}] {levels.get(level, '')}{msg}"
        self.logs.append(entry)
        print(f"  {entry}")

    def exec_save_logs(self, stmt):
        _, fname_expr = stmt
        fname = self.to_string(self.evaluate(fname_expr))
        with open(fname, 'w') as f:
            f.write('\n'.join(self.logs))
        print(f"  [log] saved {len(self.logs)} entries to '{fname}'")

    # ─── AFTER ─────────────────────────────────────────
    def exec_after(self, stmt):
        _, amt_expr, body = stmt
        time.sleep(self.evaluate(amt_expr))
        for s in body: self.execute(s)

    # ─── TIMER ─────────────────────────────────────────
    def exec_start_timer(self, stmt):
        self.timer_start = time.time()

    def exec_stop_timer(self, stmt):
        if self.timer_start:
            self.timer_value = round(time.time() - self.timer_start, 4)
            self.variables['timer'] = Variable(self.timer_value)

    # ─── COMPARE ───────────────────────────────────────
    def exec_compare(self, stmt):
        _, a_expr, b_expr = stmt
        a = self.evaluate(a_expr)
        b = self.evaluate(b_expr)
        na = self._expr_label(a_expr)
        nb = self._expr_label(b_expr)
        print(f"\n── compare ──────────────────────")
        print(f"  {na} = {self.to_string(a)}")
        print(f"  {nb} = {self.to_string(b)}")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            diff = b - a
            sign = '+' if diff >= 0 else ''
            print(f"  difference: {sign}{diff}")
            if a != 0:
                pct = round(((b - a) / abs(a)) * 100, 1)
                print(f"  {nb} is {abs(pct)}% {'higher' if pct >= 0 else 'lower'}")
        elif isinstance(a, list) and isinstance(b, list):
            both = [x for x in a if x in b]
            only_a = [x for x in a if x not in b]
            only_b = [x for x in b if x not in a]
            print(f"  in both     : {both}")
            print(f"  only in {na} : {only_a}")
            print(f"  only in {nb} : {only_b}")
        elif isinstance(a, str) and isinstance(b, str):
            print(f"  same: {'yes' if a == b else 'no'}")
            print(f"  length: {len(a)} vs {len(b)}")
        print(f"─────────────────────────────────\n")

    # ─── ALIAS ─────────────────────────────────────────
    def exec_alias(self, stmt):
        _, name, body = stmt
        self.aliases[name] = body

    # ─── CHAIN ─────────────────────────────────────────
    def exec_chain(self, stmt):
        _, target, steps = stmt
        val = self.to_string(self.variables[target].value) if target in self.variables else target
        for step in steps:
            if step == 'clean':      val = val.strip()
            elif step == 'capitalize': val = val.title()
            elif step == 'uppercase': val = val.upper()
            elif step == 'lowercase': val = val.lower()
            elif step == 'say':      print(val)
        self.variables[target] = Variable(val)

    # ─── CLAMP ─────────────────────────────────────────
    def exec_clamp(self, stmt):
        _, target, lo_expr, hi_expr, do_say = stmt
        val = self.evaluate(('var', target))
        lo = self.evaluate(lo_expr)
        hi = self.evaluate(hi_expr)
        val = max(lo, min(hi, val))
        self.variables[target] = Variable(val)
        if do_say: print(self.to_string(val))

    # ─── USE ─────────────────────────────────────────
    def exec_use(self, stmt):
        _, path = stmt
        if not path.endswith('.fig'):
            path = path + '.fig'
        
        search_paths = [
            path,
            os.path.join('libs', path),
            os.path.join(os.path.dirname(path), 'libs', path),
        ]
        
        found = None
        for p in search_paths:
            if os.path.exists(p):
                found = p
                break
        
        if not found:
            raise FileNotFoundError(
                f"FigLang: library '{path}' not found"
            )
        
        with open(found, 'r') as f:
            source = f.read()
        
        from lexer import tokenize
        from parser import parse
        
        tokens = tokenize(source)
        ast = parse(tokens)
        self.run(ast)
        
        if self.debug_mode:
            print(f"  [use] loaded '{found}'")

    # ─── EVALUATE ──────────────────────────────────────
    def evaluate(self, expr):
        if expr is None: return None
        kind = expr[0]

        if kind == 'number':  return expr[1]
        elif kind == 'string': return expr[1]
        elif kind == 'bool':   return expr[1]
        elif kind == 'list':   return [self.evaluate(i) for i in expr[1]]

        elif kind == 'var':
            name = expr[1]
            if name in self.variables: return self.variables[name].value
            if name in self.state_current: return self.state_current[name]
            return name  # treat as string for states etc

        elif kind == 'memory':
            _, mt, name = expr
            if name not in self.variables:
                raise NameError(f"FigLang: '{name}' not defined")
            var = self.variables[name]
            if mt == 'previous': return var.previous()
            if mt == 'history':  return var.history
            if mt == 'highest':  return var.highest()
            if mt == 'lowest':   return var.lowest()

        elif kind == 'collection_op':
            _, op, name = expr
            val = self.variables[name].value if name in self.variables else []
            if not isinstance(val, list): val = [val]
            nums = [x for x in val if isinstance(x, (int, float))]
            if op == 'average': return sum(nums) / len(nums) if nums else 0
            if op == 'total':   return sum(nums)
            if op == 'sorted':  return sorted(val)
            if op == 'reversed': return list(reversed(val))

        elif kind == 'str_op':
            op = expr[1]; name = expr[2]
            val = self.to_string(self.variables[name].value if name in self.variables else name)
            if op == 'uppercase':   return val.upper()
            if op == 'lowercase':   return val.lower()
            if op == 'capitalized': return val.title()
            if op == 'length':      return len(val)
            if op == 'without':     return val.replace(self.to_string(self.evaluate(expr[3])), '')
            if op == 'repeated':    return val * int(self.evaluate(expr[3]))
            if op == 'first_n':     return val[:int(self.evaluate(expr[3]))]
            if op == 'last_n':      return val[-int(self.evaluate(expr[3])):]

        elif kind == 'math_op':
            op = expr[1]
            if op == 'percent':
                return (self.evaluate(expr[2]) / 100) * self.evaluate(expr[3])
            val = self.evaluate(expr[2])
            if op == 'half':   return val / 2
            if op == 'double': return val * 2
            if op == 'square': return val ** 2
            if op == 'round':  return round(val)

        elif kind == 'time_op':
            now = datetime.now()
            if expr[1] == 'time':    return now.strftime('%H:%M:%S')
            if expr[1] == 'date':    return now.strftime('%Y-%m-%d')
            if expr[1] == 'day':     return now.strftime('%A')
            if expr[1] == 'elapsed': return self.variables.get('elapsed_time', Variable(0)).value

        elif kind == 'convert':
            _, uf, ut, val_expr = expr
            val = self.evaluate(val_expr)
            conversions = {
                ('celsius','fahrenheit'):     lambda v: v * 9/5 + 32,
                ('fahrenheit','celsius'):     lambda v: (v - 32) * 5/9,
                ('kilometers','miles'):       lambda v: v * 0.621371,
                ('miles','kilometers'):       lambda v: v * 1.60934,
                ('bytes','kilobytes'):        lambda v: v / 1024,
                ('kilobytes','bytes'):        lambda v: v * 1024,
                ('kilobytes','megabytes'):    lambda v: v / 1024,
                ('megabytes','kilobytes'):    lambda v: v * 1024,
                ('bytes','megabytes'):        lambda v: v / (1024*1024),
                ('seconds_u','minutes'):     lambda v: v / 60,
                ('minutes','seconds_u'):     lambda v: v * 60,
                ('seconds_u','hours'):       lambda v: v / 3600,
                ('hours','seconds_u'):       lambda v: v * 3600,
                ('minutes','hours'):         lambda v: v / 60,
                ('hours','minutes'):         lambda v: v * 60,
                ('degrees','radians'):       lambda v: v * 3.14159265 / 180,
                ('radians','degrees'):       lambda v: v * 180 / 3.14159265,
            }
            fn = conversions.get((uf, ut))
            if fn: return round(fn(val), 4)
            raise ValueError(f"FigLang: cannot convert {uf} to {ut}")

        elif kind == 'random_between':
            lo = int(self.evaluate(expr[1]))
            hi = int(self.evaluate(expr[2]))
            return random.randint(lo, hi)

        elif kind == 'random_from':
            lst = self.evaluate(expr[1])
            return random.choice(lst) if lst else None

        elif kind == 'random_bool':
            return random.choice([True, False])

        elif kind == 'shuffled':
            lst = list(self.evaluate(expr[1]))
            random.shuffle(lst)
            return lst
        
        elif kind == 'highest_of':
            name = expr[1]
            if name not in self.variables:
                raise NameError(f"FigLang: '{name}' not defined")
            val = self.variables[name].value
            if isinstance(val, list):
                nums = [x for x in val if isinstance(x, (int, float))]
                return max(nums) if nums else None
            else:
                return self.variables[name].highest()

        elif kind == 'lowest_of':
            name = expr[1]
            if name not in self.variables:
                raise NameError(f"FigLang: '{name}' not defined")
            val = self.variables[name].value
            if isinstance(val, list):
                nums = [x for x in val if isinstance(x, (int, float))]
                return min(nums) if nums else None
            else:
                return self.variables[name].lowest()

        elif kind == 'format_number':
            val = self.evaluate(expr[1])
            return f"{val:,}" if isinstance(val, (int, float)) else str(val)

        elif kind == 'format_percent':
            val = self.evaluate(expr[1])
            return f"{val * 100}%" if isinstance(val, (int, float)) else str(val)

        elif kind == 'format_binary':
            val = int(self.evaluate(expr[1]))
            return bin(val)[2:]

        elif kind == 'format_hex':
            val = int(self.evaluate(expr[1]))
            return hex(val)[2:].upper()

        elif kind == 'format_round':
            val = self.evaluate(expr[1])
            n = int(self.evaluate(expr[2]))
            return round(val, n)

        elif kind == 'table_row':
            name, idx_expr = expr[1], expr[2]
            idx = int(self.evaluate(idx_expr)) - 1
            if name in self.tables and 0 <= idx < len(self.tables[name]):
                return self.tables[name][idx]
            return []

        elif kind == 'table_column':
            name, idx_expr = expr[1], expr[2]
            idx = int(self.evaluate(idx_expr)) - 1
            if name in self.tables:
                return [r[idx] for r in self.tables[name] if idx < len(r)]
            return []

        elif kind == 'map_access':
            map_name, field = expr[1], expr[2]
            if map_name in self.maps and field in self.maps[map_name]:
                return self.maps[map_name][field]
            raise NameError(f"FigLang: '{field}' not found in '{map_name}'")

        elif kind == 'timer_val':
            return self.timer_value

        elif kind == 'binop':
            _, op, le, re_ = expr
            l = self.evaluate(le)
            r = self.evaluate(re_)
            if op == 'concat':    return self.to_string(l) + self.to_string(r)
            if op == 'PLUS':      return l + r
            if op == 'MINUS':     return l - r
            if op == 'TIMES_OP':  return l * r
            if op == 'DIVIDE_OP': return l / r
            if op == 'GT':        return l > r
            if op == 'LT':        return l < r
            if op == 'GTE':       return l >= r
            if op == 'LTE':       return l <= r
            if op == 'EQ':        return l == r

        return None

    # ─── EVAL CONDITION ────────────────────────────────
    def eval_condition(self, cond):
        if cond is None: return False
        kind = cond[0]

        if kind == 'compare':
            _, le, op, right, certainty = cond
            l = self.evaluate(le)
            r = self.evaluate(right) if isinstance(right, tuple) else right
            result = False
            if op == 'eq':      result = l == r
            elif op == 'not_eq': result = l != r
            elif op == 'gt':    result = l > r
            elif op == 'lt':    result = l < r
            elif op == 'gte':   result = l >= r
            elif op == 'lte':   result = l <= r
            if result and certainty in ('probably', 'maybe'):
                return random.random() < (0.8 if certainty == 'probably' else 0.5)
            return result

        elif kind == 'between':
            _, le, lo, hi, _ = cond
            try:
                val, low, high = self.evaluate(le), self.evaluate(lo), self.evaluate(hi)
                return float(low) <= float(val) <= float(high)
            except: return False

        elif kind == 'is_empty':
            v = self.evaluate(cond[1])
            return v == '' or v is None or v == []

        elif kind == 'not_empty':
            v = self.evaluate(cond[1])
            return v != '' and v is not None and v != []

        elif kind == 'trend':
            _, le, d, _ = cond
            name = le[1] if le[0] == 'var' else None
            if name and name in self.variables:
                var = self.variables[name]
                return var.is_going_up() if d == 'up' else var.is_going_down()
            return False

        elif kind == 'hits':
            return self.evaluate(cond[1]) == self.evaluate(cond[2])

        elif kind == 'changes':
            name = cond[1][1] if cond[1][0] == 'var' else None
            if name and name in self.variables:
                var = self.variables[name]
                return len(var.history) >= 2 and var.history[-1] != var.history[-2]
            return False

        elif kind == 'contains':
            return self.to_string(self.evaluate(cond[2])) in self.to_string(self.evaluate(cond[1]))

        elif kind == 'starts_with':
            return self.to_string(self.evaluate(cond[1])).startswith(self.to_string(self.evaluate(cond[2])))

        elif kind == 'is_valid':
            _, vtype, val_expr, _ = cond
            val = self.to_string(self.evaluate(val_expr))
            if vtype == 'email': return bool(re.match(r'^[\w.-]+@[\w.-]+\.\w+$', val))
            if vtype == 'url':   return bool(re.match(r'^https?://[\w.-]+\.\w+', val))
            if vtype == 'number':
                try: float(val); return True
                except: return False
            return False

        elif kind == 'logical':
            _, op, lc, rc = cond
            if op == 'and': return self.eval_condition(lc) and self.eval_condition(rc)
            if op == 'or':  return self.eval_condition(lc) or self.eval_condition(rc)

        elif kind == 'expr_cond':
            return bool(self.evaluate(cond[1]))

        return False

    # ─── HELPERS ───────────────────────────────────────
    def to_string(self, value):
        if isinstance(value, bool): return 'true' if value else 'false'
        if isinstance(value, float):
            return str(int(value)) if value == int(value) else str(value)
        if isinstance(value, list):
            return '[' + ', '.join(self.to_string(x) for x in value) + ']'
        if isinstance(value, dict):
            return '{' + ', '.join(f'{k}: {self.to_string(v)}' for k, v in value.items()) + '}'
        return str(value)

    def _try_number(self, raw):
        try: return int(raw)
        except ValueError:
            try: return float(raw)
            except ValueError: return raw

    def _type_name(self, v):
        if isinstance(v, bool):  return 'boolean'
        if isinstance(v, int):   return 'integer'
        if isinstance(v, float): return 'decimal'
        if isinstance(v, str):   return 'text'
        if isinstance(v, list):  return 'collection'
        if isinstance(v, dict):  return 'map'
        return 'unknown'
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset=0):
        p = self.pos + offset
        return self.tokens[p] if p < len(self.tokens) else ('EOF', None, -1)

    def current(self):      return self.peek(0)
    def current_type(self):  return self.current()[0]
    def current_value(self): return self.current()[1]

    def eat(self, token_type=None):
        token = self.current()
        if token_type and token[0] != token_type:
            raise SyntaxError(
                f"FigLang: expected {token_type} but got "
                f"{token[0]} ('{token[1]}') on line {token[2]}")
        self.pos += 1
        return token

    def skip_newlines(self):
        while self.current_type() == 'NEWLINE': self.eat()

    def parse_block(self):
        stmts = []
        self.skip_newlines()
        while self.current_type() != 'EOF':
            if self.current_type() == 'NEWLINE':
                self.eat(); continue
            s = self.parse_statement()
            if s: stmts.append(s)
        return stmts
    
    def parse_use(self):
        self.eat('USE')
        path = self.eat('STRING')[1]
        return ('use', path)

    def parse_indented_block(self):
        stmts = []
        self.skip_newlines()
        stop = ('EOF', 'OTHERWISE', 'BUT')
        while self.current_type() not in stop:
            if self.current_type() == 'NEWLINE':
                self.eat(); continue
            s = self.parse_statement()
            if s: stmts.append(s)
            else: break
        return stmts

    def parse_statement(self):
        t = self.current_type()
        dispatch = {
            'SAY': self.parse_say, 'ASK': self.parse_ask,
            'IF': self.parse_if, 'UNTIL': self.parse_until,
            'GIVEN': self.parse_given, 'REPEAT': self.parse_repeat,
            'COUNT': self.parse_count, 'FOR': self.parse_for_each,
            'WHENEVER': self.parse_whenever, 'EVERY': self.parse_every,
            'ASSUME': self.parse_assume, 'REQUIRE': self.parse_require,
            'START': self.parse_pipeline, 'TRY': self.parse_try,
            'ZONE': self.parse_zone_def, 'DO': self.parse_do_zone,
            'ROLE': self.parse_role, 'WATCH': self.parse_watch,
            'UNWATCH': self.parse_unwatch, 'EXPLAIN': self.parse_explain,
            'DEBUG': self.parse_debug, 'SNAPSHOT': self.parse_snapshot,
            'RESTORE': self.parse_restore, 'REMEMBER': self.parse_remember,
            'RECALL': self.parse_recall, 'FORGET': self.parse_forget,
            'CHECK_THAT': self.parse_check, 'LISTEN_FOR': self.parse_listen,
            'MEASURE': self.parse_measure, 'WAIT': self.parse_wait,
            'ADD': self.parse_add_to_group,
            'READ': self.parse_read, 'WRITE': self.parse_write,
            'APPEND': self.parse_append, 'LINES_OF': self.parse_lines_of,
            'TABLE': self.parse_table, 'SHOW': self.parse_show,
            'VALIDATE': self.parse_validate, 'LOG': self.parse_log,
            'SAVE_LOGS': self.parse_save_logs, 'AFTER': self.parse_after,
            'START_TIMER': self.parse_start_timer,
            'STOP_TIMER': self.parse_stop_timer,
            'COMPARE': self.parse_compare, 'ALIAS': self.parse_alias,
            'CLEAN': self.parse_chain_clean, 'CLAMP': self.parse_clamp,
            'IDENT': self.parse_ident_statement,
        }
        handler = dispatch.get(t)
        if handler: return handler()
        if t in ('BUT', 'OTHERWISE'): return None
        if t == 'NEWLINE': self.eat(); return None
        self.eat(); return None

    # ─── SAY ───────────────────────────────────────────
    def parse_say(self):
        self.eat('SAY')
        expr = self.parse_expression()
        if self.current_type() == 'WITH_CTX':
            self.eat('WITH_CTX'); return ('say_context', expr)
        return ('say', expr)

    # ─── ASK ───────────────────────────────────────────
    def parse_ask(self):
        self.eat('ASK')
        prompt = self.eat('STRING')[1]
        self.eat('ARROW')
        name = self.eat('IDENT')[1]
        return ('ask', prompt, name)

    # ─── IF ────────────────────────────────────────────
    def parse_if(self):
        self.eat('IF')
        cond = self.parse_condition()
        self.eat('COLON'); self.skip_newlines()
        body = self.parse_indented_block()
        elifs, else_body = [], []
        while self.current_type() == 'BUT':
            self.eat('BUT'); self.eat('IF')
            ec = self.parse_condition()
            self.eat('COLON'); self.skip_newlines()
            eb = self.parse_indented_block()
            elifs.append((ec, eb))
        if self.current_type() == 'OTHERWISE':
            self.eat('OTHERWISE'); self.eat('COLON')
            self.skip_newlines()
            else_body = self.parse_indented_block()
        return ('if', cond, body, elifs, else_body)

    # ─── UNTIL ─────────────────────────────────────────
    def parse_until(self):
        self.eat('UNTIL')
        cond = self.parse_condition()
        self.eat('COLON'); self.skip_newlines()
        return ('until', cond, self.parse_indented_block())

    # ─── GIVEN ─────────────────────────────────────────
    def parse_given(self):
        self.eat('GIVEN')
        cond = self.parse_condition()
        self.eat('COLON'); self.skip_newlines()
        return ('given', cond, self.parse_indented_block())

    # ─── REPEAT ────────────────────────────────────────
    def parse_repeat(self):
        self.eat('REPEAT')
        n = self.parse_expression()
        self.eat('TIMES'); self.eat('COLON'); self.skip_newlines()
        return ('repeat', n, self.parse_indented_block())

    # ─── COUNT ─────────────────────────────────────────
    def parse_count(self):
        self.eat('COUNT'); self.eat('FROM')
        s = self.parse_expression()
        self.eat('TO')
        e = self.parse_expression()
        self.eat('COLON'); self.skip_newlines()
        return ('count', s, e, self.parse_indented_block())

    # ─── FOR EACH ──────────────────────────────────────
    def parse_for_each(self):
        self.eat('FOR'); self.eat('EACH')
        var = self.eat('IDENT')[1]
        self.eat('IN')
        col = self.parse_expression()
        self.eat('COLON'); self.skip_newlines()
        return ('for_each', var, col, self.parse_indented_block())

    # ─── WHENEVER ──────────────────────────────────────
    def parse_whenever(self):
        self.eat('WHENEVER')
        cond = self.parse_condition()
        self.eat('COLON'); self.skip_newlines()
        return ('whenever', cond, self.parse_indented_block())

    # ─── EVERY ─────────────────────────────────────────
    def parse_every(self):
        self.eat('EVERY')
        n = self.parse_expression()
        self.eat('TIMES')
        name = self.eat('IDENT')[1]
        self.eat('CHANGES'); self.eat('COLON'); self.skip_newlines()
        return ('every', n, name, self.parse_indented_block())

    # ─── ASSUME ────────────────────────────────────────
    def parse_assume(self):
        self.eat('ASSUME')
        name = self.eat('IDENT')[1]
        self.eat('IS')
        val = self.parse_expression()
        self.eat('UNLESS'); self.eat('DEFINED')
        return ('assume', name, val)

    # ─── REQUIRE ───────────────────────────────────────
    def parse_require(self):
        self.eat('REQUIRE')
        name = self.eat('IDENT')[1]
        self.eat('TO')
        if self.current_type() == 'IDENT' and self.current_value() == 'be':
            self.eat()
        constraints = []
        while self.current_type() not in ('NEWLINE', 'EOF'):
            t = self.current_type()
            if t == 'NOT':
                self.eat('NOT')
                if self.current_type() == 'EMPTY':
                    self.eat('EMPTY')
                    constraints.append(('not_empty',))
                else:
                    constraints.append(('not', self.parse_expression()))
            elif t == 'ABOVE':
                self.eat('ABOVE')
                constraints.append(('above', self.parse_expression()))
            elif t == 'BELOW':
                self.eat('BELOW')
                constraints.append(('below', self.parse_expression()))
            elif t == 'BETWEEN':
                self.eat('BETWEEN')
                low = self.parse_expression()
                if self.current_type() == 'AND': self.eat('AND')
                constraints.append(('between', low, self.parse_expression()))
            elif t == 'POSITIVE':
                self.eat('POSITIVE')
                constraints.append(('above', ('number', 0)))
            elif t == 'EMPTY':
                self.eat('EMPTY')
                constraints.append(('not_empty',))
            else:
                constraints.append(('eq', self.parse_expression()))
        return ('require', name, constraints)

    # ─── PIPELINE ──────────────────────────────────────
    def parse_pipeline(self):
        self.eat('START'); self.eat('WITH')
        src = self.parse_expression()
        steps = []
        while self.current_type() in ('KEEP','DOUBLE','SAY','COMMA','SORTED','REVERSED'):
            if self.current_type() == 'COMMA': self.eat('COMMA')
            if self.current_type() == 'KEEP':
                self.eat('KEEP')
                if self.current_type() == 'ABOVE':
                    self.eat('ABOVE'); steps.append(('keep','above',self.parse_expression()))
                elif self.current_type() == 'BELOW':
                    self.eat('BELOW'); steps.append(('keep','below',self.parse_expression()))
            elif self.current_type() == 'DOUBLE':
                self.eat('DOUBLE'); self.eat('EACH'); steps.append(('double',))
            elif self.current_type() == 'SORTED':
                self.eat('SORTED'); steps.append(('sort',))
            elif self.current_type() == 'REVERSED':
                self.eat('REVERSED'); steps.append(('reverse',))
            elif self.current_type() == 'SAY':
                self.eat('SAY'); self.eat('EACH'); steps.append(('say_each',))
        return ('pipeline', src, steps)

    # ─── TRY ───────────────────────────────────────────
    def parse_try(self):
        self.eat('TRY'); self.eat('TO')
        body = self.parse_statement()
        fallback = None
        if self.current_type() == 'BUT':
            self.eat('BUT')
            if self.current_type() == 'IF': self.eat('IF')
            if self.current_type() == 'IDENT': self.eat('IDENT')
            if self.current_type() == 'FAILS': self.eat('FAILS')
            fallback = self.parse_statement()
        return ('try', body, fallback)

    # ─── ZONE ──────────────────────────────────────────
    def parse_zone_def(self):
        self.eat('ZONE'); self.eat('CALLED')
        name = self.eat('IDENT')[1]
        self.eat('COLON'); self.skip_newlines()
        return ('zone_def', name, self.parse_indented_block())

    def parse_do_zone(self):
        self.eat('DO')
        name = self.eat('IDENT')[1]
        again = self.current_type() == 'AGAIN'
        if again: self.eat('AGAIN')
        return ('do_zone', name, again)

    # ─── ROLE ──────────────────────────────────────────
    def parse_role(self):
        self.eat('ROLE')
        name = self.eat('IDENT')[1]
        self.eat('HAS'); self.eat('COLON'); self.skip_newlines()
        return ('role_def', name, self.parse_indented_block())

    # ─── WATCH ─────────────────────────────────────────
    def parse_watch(self):
        self.eat('WATCH'); return ('watch', self.eat('IDENT')[1])

    def parse_unwatch(self):
        self.eat('UNWATCH'); return ('unwatch', self.eat('IDENT')[1])

    # ─── EXPLAIN ───────────────────────────────────────
    def parse_explain(self):
        self.eat('EXPLAIN'); return ('explain', self.eat('IDENT')[1])

    # ─── DEBUG ─────────────────────────────────────────
    def parse_debug(self):
        self.eat('DEBUG')
        if self.current_type() == 'ON': self.eat('ON'); return ('debug', True)
        if self.current_type() == 'OFF': self.eat('OFF'); return ('debug', False)
        return ('debug', True)

    # ─── SNAPSHOT ──────────────────────────────────────
    def parse_snapshot(self):
        self.eat('SNAPSHOT'); return ('snapshot_take', self.eat('STRING')[1])

    def parse_restore(self):
        self.eat('RESTORE'); return ('snapshot_restore', self.eat('STRING')[1])

    # ─── REMEMBER / RECALL / FORGET ────────────────────
    def parse_remember(self):
        self.eat('REMEMBER')
        name = self.eat('IDENT')[1]
        self.eat('AS')
        return ('remember', name, self.eat('STRING')[1])

    def parse_recall(self):
        self.eat('RECALL')
        key = self.eat('STRING')[1]
        self.eat('ARROW')
        return ('recall', key, self.eat('IDENT')[1])

    def parse_forget(self):
        self.eat('FORGET'); return ('forget', self.eat('STRING')[1])

    # ─── CHECK ─────────────────────────────────────────
    def parse_check(self):
        self.eat('CHECK_THAT')
        return ('check', self.parse_condition())

    # ─── LISTEN ────────────────────────────────────────
    def parse_listen(self):
        self.eat('LISTEN_FOR')
        if self.current_type() == 'NUMBER_KW':
            self.eat('NUMBER_KW'); self.eat('ARROW')
            return ('listen', 'number', None, self.eat('IDENT')[1])
        elif self.current_type() == 'YES':
            self.eat('YES'); self.eat('OR'); self.eat('NO'); self.eat('ARROW')
            return ('listen', 'yes_no', None, self.eat('IDENT')[1])
        elif self.current_type() == 'IDENT' and self.current_value() == 'one':
            self.eat('IDENT'); self.eat('OF')
            opts = self.parse_expression()
            self.eat('ARROW')
            return ('listen', 'one_of', opts, self.eat('IDENT')[1])
        else:
            self.eat('ARROW')
            return ('listen', 'any', None, self.eat('IDENT')[1])

    # ─── MEASURE ───────────────────────────────────────
    def parse_measure(self):
        self.eat('MEASURE'); self.eat('COLON'); self.skip_newlines()
        return ('measure_time', self.parse_indented_block())

    # ─── WAIT ──────────────────────────────────────────
    def parse_wait(self):
        self.eat('WAIT')
        amt = self.parse_expression()
        if self.current_type() in ('SECONDS_U', 'SECOND'): self.eat()
        return ('wait', amt)

    # ─── ADD TO GROUP ──────────────────────────────────
    def parse_add_to_group(self):
        self.eat('ADD')
        item = self.parse_expression()
        self.eat('TO')
        return ('add_to_group', item, self.eat('IDENT')[1])

    # ─── READ FILE ─────────────────────────────────────
    def parse_read(self):
        self.eat('READ')
        filename = self.parse_expression()
        self.eat('ARROW')
        return ('read_file', filename, self.eat('IDENT')[1])

    # ─── WRITE FILE ────────────────────────────────────
    def parse_write(self):
        self.eat('WRITE')
        content = self.parse_expression()
        self.eat('TO')
        return ('write_file', content, self.parse_expression())

    # ─── APPEND FILE ───────────────────────────────────
    def parse_append(self):
        self.eat('APPEND')
        content = self.parse_expression()
        self.eat('TO')
        return ('append_file', content, self.parse_expression())

    # ─── LINES OF FILE ─────────────────────────────────
    def parse_lines_of(self):
        self.eat('LINES_OF')
        filename = self.parse_expression()
        self.eat('ARROW')
        return ('lines_of', filename, self.eat('IDENT')[1])

    # ─── TABLE ─────────────────────────────────────────
    def parse_table(self):
        self.eat('TABLE')
        name = self.eat('IDENT')[1]
        self.eat('COLON'); self.skip_newlines()
        rows = []
        while self.current_type() in ('STRING','NUMBER','IDENT','TRUE','FALSE'):
            row = [self.parse_expression()]
            while self.current_type() == 'PIPE_SEP':
                self.eat('PIPE_SEP')
                row.append(self.parse_expression())
            rows.append(row)
            while self.current_type() == 'NEWLINE': self.eat()
        return ('table_def', name, rows)

    # ─── SHOW ──────────────────────────────────────────
    def parse_show(self):
        self.eat('SHOW')
        expr = self.parse_expression()
        if self.current_type() == 'AS_LIST':
            self.eat('AS_LIST'); return ('show_list', expr)
        elif self.current_type() == 'BAR_CHART':
            self.eat('BAR_CHART'); return ('show_bar', expr)
        elif self.current_type() == 'SORT_BY':
            self.eat('SORT_BY')
            col = self.parse_expression()
            return ('show_sorted', expr, col)
        return ('say', expr)

    # ─── VALIDATE ──────────────────────────────────────
    def parse_validate(self):
        self.eat('VALIDATE')
        vtype = self.eat('IDENT')[1]
        return ('validate', vtype, self.parse_expression())

    # ─── LOG ───────────────────────────────────────────
    def parse_log(self):
        self.eat('LOG')
        msg = self.parse_expression()
        level = 'info'
        if self.current_type() == 'WITH':
            self.eat('WITH'); self.eat('LEVEL')
            if self.current_type() == 'WARNING':
                self.eat('WARNING'); level = 'warning'
            elif self.current_type() == 'ERROR_LVL':
                self.eat('ERROR_LVL'); level = 'error'
            elif self.current_type() == 'INFO':
                self.eat('INFO'); level = 'info'
        return ('log', msg, level)

    # ─── SAVE LOGS ─────────────────────────────────────
    def parse_save_logs(self):
        self.eat('SAVE_LOGS')
        return ('save_logs', self.parse_expression())

    # ─── AFTER ─────────────────────────────────────────
    def parse_after(self):
        self.eat('AFTER')
        amt = self.parse_expression()
        if self.current_type() in ('SECONDS_U', 'SECOND'): self.eat()
        self.eat('COLON'); self.skip_newlines()
        return ('after', amt, self.parse_indented_block())

    # ─── TIMER ─────────────────────────────────────────
    def parse_start_timer(self):
        self.eat('START_TIMER'); return ('start_timer',)

    def parse_stop_timer(self):
        self.eat('STOP_TIMER'); return ('stop_timer',)

    # ─── COMPARE ───────────────────────────────────────
    def parse_compare(self):
        self.eat('COMPARE')
        a = self.parse_primary()
        self.eat('AND')
        return ('compare_vals', a, self.parse_primary())

    # ─── ALIAS ─────────────────────────────────────────
    def parse_alias(self):
        self.eat('ALIAS')
        name = self.eat('STRING')[1]
        self.eat('MEANS')
        if self.current_type() == 'COLON':
            self.eat('COLON'); self.skip_newlines()
            return ('alias', name, self.parse_indented_block())
        else:
            s = self.parse_statement()
            return ('alias', name, [s])

    # ─── CHAIN CLEAN ───────────────────────────────────
    def parse_chain_clean(self):
        self.eat('CLEAN')
        target = self.eat('IDENT')[1]
        steps = ['clean']
        while self.current_type() == 'THEN_CHAIN':
            self.eat('THEN_CHAIN')
            t = self.current_type()
            if t == 'CAPITALIZE':   self.eat(); steps.append('capitalize')
            elif t == 'UPPERCASE':  self.eat(); steps.append('uppercase')
            elif t == 'LOWERCASE':  self.eat(); steps.append('lowercase')
            elif t == 'SAY':        self.eat(); steps.append('say')
            elif t == 'IDENT':      steps.append(self.eat('IDENT')[1])
            else: break
        return ('chain', target, steps)

    # ─── CLAMP ─────────────────────────────────────────
    def parse_clamp(self):
        self.eat('CLAMP')
        target = self.eat('IDENT')[1]
        self.eat('BETWEEN')
        low = self.parse_expression()
        if self.current_type() == 'AND': self.eat('AND')
        high = self.parse_expression()
        do_say = False
        if self.current_type() == 'THEN_CHAIN':
            self.eat('THEN_CHAIN')
            if self.current_type() == 'SAY':
                self.eat('SAY'); do_say = True
        return ('clamp', target, low, high, do_say)

    # ─── IDENT STATEMENTS ──────────────────────────────
    def parse_ident_statement(self):
        name = self.eat('IDENT')[1]

        # name is ...
        if self.current_type() == 'IS':
            self.eat('IS')
            certainty = 'definitely'
            if self.current_type() == 'DEFINITELY':
                self.eat('DEFINITELY'); certainty = 'definitely'
            elif self.current_type() == 'PROBABLY':
                self.eat('PROBABLY'); certainty = 'probably'
            elif self.current_type() == 'MAYBE':
                self.eat('MAYBE'); certainty = 'maybe'

            if self.current_type() == 'NEVER':
                self.eat('NEVER'); self.eat('GOES')
                limits = []
                while self.current_type() in ('BELOW','ABOVE','OR'):
                    if self.current_type() == 'OR': self.eat('OR')
                    d = self.current_type().lower(); self.eat()
                    limits.append((d, self.parse_expression()))
                return ('set_limits', name, limits)

            if self.current_type() == 'A':
                saved = self.pos
                self.eat('A')
                if self.current_type() == 'IDENT' and self.current_value() == 'group':
                    self.eat('IDENT'); self.eat('OF')
                    return ('group_def', name, self.eat('IDENT')[1])
                self.pos = saved

            return ('assign', name, self.parse_expression(), certainty)

        # name reacts to X and Y:
        elif self.current_type() == 'REACT':
            self.eat('REACT')
            deps = [self.eat('IDENT')[1]]
            while self.current_type() == 'AND':
                self.eat('AND'); deps.append(self.eat('IDENT')[1])
            self.eat('COLON'); self.skip_newlines()
            return ('react', name, deps, self.parse_indented_block())

        # name and other are linked:
        elif self.current_type() == 'AND':
            saved = self.pos
            self.eat('AND')
            if self.current_type() == 'IDENT':
                other = self.eat('IDENT')[1]
                if self.current_type() == 'ARE':
                    self.eat('ARE')
                if self.current_type() == 'LINKED':
                    self.eat('LINKED'); self.eat('COLON'); self.skip_newlines()
                    return ('link', name, other, self.parse_indented_block())
            self.pos = saved
            return ('expr', ('var', name))

        # name has: (map definition)
        elif self.current_type() == 'HAS':
            saved = self.pos
            self.eat('HAS')
            if self.current_type() == 'COLON':
                self.eat('COLON'); self.skip_newlines()
                fields = []
                while self.current_type() == 'IDENT':
                    fname = self.eat('IDENT')[1]
                    if self.current_type() == 'IS':
                        self.eat('IS')
                        fval = self.parse_expression()
                        fields.append(('assign', fname, fval, 'definitely'))
                        self.skip_newlines()
                    else:
                        break
                return ('map_def', name, fields)
            self.pos = saved
            return ('expr', ('var', name))

        # name can be state1, state2
        elif self.current_type() == 'STATE':
            self.eat('STATE')
            states = [self.eat('IDENT')[1]]
            while self.current_type() == 'COMMA':
                self.eat('COMMA'); states.append(self.eat('IDENT')[1])
            return ('state_def', name, states)

        # name starts as state
        elif self.current_type() == 'STARTS_AS':
            self.eat('STARTS_AS')
            return ('state_start', name, self.eat('IDENT')[1])

        # name becomes state
        elif self.current_type() == 'BECOMES':
            self.eat('BECOMES')
            return ('state_become', name, self.eat('IDENT')[1])

        # name can go from X to Y
        elif self.current_type() == 'CAN_GO':
            self.eat('CAN_GO'); self.eat('FROM')
            fr = self.eat('IDENT')[1]
            self.eat('TO')
            return ('state_transition', name, fr, self.eat('IDENT')[1])

        # name described as "..."
        elif self.current_type() == 'ANNOTATE':
            self.eat('ANNOTATE')
            desc = self.eat('STRING')[1]
            ann = {'described_as': desc}
            while self.current_type() in ('MEASURED', 'OWNED'):
                if self.current_type() == 'MEASURED':
                    self.eat('MEASURED'); ann['measured_in'] = self.eat('STRING')[1]
                elif self.current_type() == 'OWNED':
                    self.eat('OWNED'); ann['owned_by'] = self.eat('STRING')[1]
            return ('annotate', name, ann)

        # name does action (method call)
        elif self.current_type() == 'IDENT':
            action = self.eat('IDENT')[1]
            args = []
            while self.current_type() not in ('NEWLINE', 'EOF'):
                args.append(self.parse_expression())
            return ('call_method', name, action, args)

        return ('expr', ('var', name))

    # ─── CONDITIONS ────────────────────────────────────
    def parse_condition(self):
        certainty = None
        if self.current_type() in ('DEFINITELY', 'PROBABLY', 'MAYBE'):
            certainty = self.current_type().lower(); self.eat()

        left = self.parse_expression()

        if self.current_type() == 'KEEPS':
            self.eat('KEEPS'); self.eat('GOING')
            d = self.current_type().lower(); self.eat()
            return ('trend', left, d, certainty)

        if self.current_type() == 'CHANGES':
            self.eat('CHANGES'); return ('changes', left, certainty)

        if self.current_type() == 'HITS':
            self.eat('HITS')
            return ('hits', left, self.parse_expression(), certainty)

        if self.current_type() == 'CONTAINS':
            self.eat('CONTAINS')
            return ('contains', left, self.parse_expression(), certainty)

        if self.current_type() == 'STARTS':
            self.eat('STARTS'); self.eat('WITH')
            return ('starts_with', left, self.parse_expression(), certainty)

        if self.current_type() == 'IS':
            self.eat('IS')
            if self.current_type() in ('DEFINITELY', 'PROBABLY', 'MAYBE'):
                certainty = self.current_type().lower(); self.eat()

            # is valid email/url/number
            if self.current_type() == 'VALID_EMAIL':
                self.eat('VALID_EMAIL'); return ('is_valid', 'email', left, certainty)
            if self.current_type() == 'VALID_URL':
                self.eat('VALID_URL'); return ('is_valid', 'url', left, certainty)
            if self.current_type() == 'VALID_NUM':
                self.eat('VALID_NUM'); return ('is_valid', 'number', left, certainty)

            negated = False
            if self.current_type() == 'NOT':
                self.eat('NOT'); negated = True

            if self.current_type() == 'AT':
                self.eat('AT')
                if self.current_type() == 'LEAST':
                    self.eat('LEAST'); op = 'gte'
                else:
                    self.eat('MOST'); op = 'lte'
                right = self.parse_expression()
            elif self.current_type() == 'ABOVE':
                self.eat('ABOVE'); op = 'gt'
                right = self.parse_expression()
            elif self.current_type() == 'BELOW':
                self.eat('BELOW'); op = 'lt'
                right = self.parse_expression()
            elif self.current_type() == 'BETWEEN':
                self.eat('BETWEEN')
                low = self.parse_primary()
                if self.current_type() == 'AND': self.eat('AND')
                high = self.parse_primary()
                return ('between', left, low, high, certainty)
            elif self.current_type() == 'EMPTY':
                self.eat('EMPTY')
                if negated: return ('not_empty', left, certainty)
                return ('is_empty', left, certainty)
            elif self.current_type() == 'TRUE':
                self.eat('TRUE'); right = True; op = 'eq'
            elif self.current_type() == 'FALSE':
                self.eat('FALSE'); right = False; op = 'eq'
            else:
                right = self.parse_expression(); op = 'eq'

            if negated and op == 'eq': op = 'not_eq'
            return ('compare', left, op, right, certainty)

        cond = ('expr_cond', left)
        while self.current_type() in ('AND', 'OR'):
            op = self.current_type().lower(); self.eat()
            cond = ('logical', op, cond, self.parse_condition())
        return cond

    # ─── EXPRESSIONS ───────────────────────────────────
    def parse_expression(self):
        left = self.parse_primary()

        while self.current_type() in ('PLUS','MINUS','TIMES_OP',
                                       'DIVIDE_OP','AND','GT','LT',
                                       'GTE','LTE','EQ'):
            op = self.current_type()
            if op == 'AND':
                self.eat('AND')
                right = self.parse_primary()
                left = ('binop', 'concat', left, right)
            else:
                self.eat()
                right = self.parse_primary()
                left = ('binop', op, left, right)

        # Post-expression modifiers
        if self.current_type() == 'FORMATTED':
            self.eat('FORMATTED'); left = ('format_number', left)
        elif self.current_type() == 'AS_PERCENTAGE':
            self.eat('AS_PERCENTAGE'); left = ('format_percent', left)
        elif self.current_type() == 'IN_BINARY':
            self.eat('IN_BINARY'); left = ('format_binary', left)
        elif self.current_type() == 'IN_HEX':
            self.eat('IN_HEX'); left = ('format_hex', left)
        elif self.current_type() == 'ROUNDED_TO':
            self.eat('ROUNDED_TO')
            n = self.parse_primary()
            if self.current_type() == 'DECIMALS': self.eat('DECIMALS')
            left = ('format_round', left, n)

        return left

    def parse_primary(self):
        t = self.current_type()

        if t == 'NUMBER':
            val = self.eat('NUMBER')[1]
            # Unit conversion: 100 celsius in fahrenheit
            units = ('CELSIUS','FAHRENHEIT','KILOMETERS','MILES',
                     'BYTES','KILOBYTES','MEGABYTES',
                     'SECONDS_U','MINUTES','HOURS',
                     'DEGREES','RADIANS')
            if self.current_type() in units:
                uf = self.current_type().lower(); self.eat()
                self.eat('IN')
                ut = self.current_type().lower(); self.eat()
                return ('convert', uf, ut, ('number', val))
            if self.current_type() == 'PERCENT':
                self.eat('PERCENT'); self.eat('OF')
                return ('math_op', 'percent', ('number', val), self.parse_expression())
            return ('number', val)

        elif t == 'STRING':
            return ('string', self.eat('STRING')[1])

        elif t == 'TRUE':
            self.eat('TRUE'); return ('bool', True)

        elif t == 'FALSE':
            self.eat('FALSE'); return ('bool', False)

        elif t == 'EMPTY':
            self.eat('EMPTY'); return ('string', '')

        elif t == 'LBRACKET':
            return self.parse_list()

        # Memory ops
        elif t == 'PREVIOUS':
            self.eat('PREVIOUS'); self.eat('VALUE'); self.eat('OF')
            return ('memory', 'previous', self.eat('IDENT')[1])

        elif t == 'HISTORY':
            self.eat('HISTORY'); self.eat('OF')
            return ('memory', 'history', self.eat('IDENT')[1])

        elif t == 'HIGHEST':
            self.eat('HIGHEST'); self.eat('OF')
            name = self.eat('IDENT')[1]
            # se è una lista usa collection_op, altrimenti memory
            return ('highest_of', name)

        elif t == 'LOWEST':
            self.eat('LOWEST'); self.eat('OF')
            name = self.eat('IDENT')[1]
            return ('lowest_of', name)

        # Collection ops
        elif t == 'AVERAGE':
            self.eat('AVERAGE'); self.eat('OF')
            return ('collection_op', 'average', self.eat('IDENT')[1])

        elif t == 'TOTAL':
            self.eat('TOTAL'); self.eat('OF')
            return ('collection_op', 'total', self.eat('IDENT')[1])

        elif t == 'SORTED':
            self.eat('SORTED')
            return ('collection_op', 'sorted', self.eat('IDENT')[1])

        elif t == 'REVERSED':
            self.eat('REVERSED')
            return ('collection_op', 'reversed', self.eat('IDENT')[1])

        # String ops
        elif t == 'LENGTH':
            self.eat('LENGTH'); self.eat('OF')
            return ('str_op', 'length', self.eat('IDENT')[1])

        elif t == 'FIRST':
            self.eat('FIRST'); n = self.parse_expression()
            self.eat('LETTERS'); self.eat('OF')
            return ('str_op', 'first_n', self.eat('IDENT')[1], n)

        elif t == 'LAST':
            self.eat('LAST'); n = self.parse_expression()
            self.eat('LETTERS'); self.eat('OF')
            return ('str_op', 'last_n', self.eat('IDENT')[1], n)

        # Math ops
        elif t == 'HALF':
            self.eat('HALF'); self.eat('OF')
            return ('math_op', 'half', self.parse_expression())

        elif t == 'DOUBLE':
            self.eat('DOUBLE'); self.eat('OF')
            return ('math_op', 'double', self.parse_expression())

        elif t == 'SQUARE':
            self.eat('SQUARE'); self.eat('OF')
            return ('math_op', 'square', self.parse_expression())

        elif t == 'ROUND':
            self.eat('ROUND')
            return ('math_op', 'round', self.parse_expression())

        # Time ops
        elif t == 'CURRENT':
            self.eat('CURRENT')
            if self.current_type() == 'TIME': self.eat('TIME'); return ('time_op', 'time')
            if self.current_type() == 'DATE': self.eat('DATE'); return ('time_op', 'date')
            if self.current_type() == 'DAY':  self.eat('DAY');  return ('time_op', 'day')
            return ('time_op', 'time')

        elif t == 'ELAPSED':
            self.eat('ELAPSED'); return ('time_op', 'elapsed')

        # Random ops
        elif t == 'RANDOM_NUM':
            self.eat('RANDOM_NUM')
            low = self.parse_primary()
            self.eat('AND')
            high = self.parse_primary()
            return ('random_between', low, high)

        elif t == 'RANDOM_ITEM':
            self.eat('RANDOM_ITEM')
            return ('random_from', self.parse_expression())

        elif t == 'RANDOM_BOOL':
            self.eat('RANDOM_BOOL'); return ('random_bool',)

        elif t == 'SHUFFLED':
            self.eat('SHUFFLED')
            return ('shuffled', self.parse_expression())

        # Table access
        elif t == 'ROW':
            self.eat('ROW'); idx = self.parse_expression()
            self.eat('OF'); return ('table_row', self.eat('IDENT')[1], idx)

        elif t == 'COLUMN':
            self.eat('COLUMN'); idx = self.parse_expression()
            self.eat('OF'); return ('table_column', self.eat('IDENT')[1], idx)

        # Timer
        elif t == 'TIMER':
            self.eat('TIMER'); return ('timer_val',)
        

        # Use
        elif t == 'USE': return self.parse_use()

        # Identifiers
        elif t == 'IDENT':
            name = self.eat('IDENT')[1]
            if self.current_type() == 'IN' and self.peek(1)[0] in ('UPPERCASE','LOWERCASE'):
                self.eat('IN')
                if self.current_type() == 'UPPERCASE':
                    self.eat('UPPERCASE'); return ('str_op', 'uppercase', name)
                elif self.current_type() == 'LOWERCASE':
                    self.eat('LOWERCASE'); return ('str_op', 'lowercase', name)

            if self.current_type() == 'CAPITALIZED':
                self.eat('CAPITALIZED'); return ('str_op', 'capitalized', name)
            if self.current_type() == 'WITHOUT':
                self.eat('WITHOUT')
                return ('str_op', 'without', name, self.parse_expression())
            if self.current_type() == 'REPEATED':
                self.eat('REPEATED'); n = self.parse_expression()
                self.eat('TIMES'); return ('str_op', 'repeated', name, n)
            if self.current_type() == 'PERCENT':
                self.eat('PERCENT'); self.eat('OF')
                return ('math_op', 'percent', ('var', name), self.parse_expression())
            # map access: field of mapname
            if self.current_type() == 'OF' and self.peek(1)[0] == 'IDENT':
                self.eat('OF')
                return ('map_access', self.eat('IDENT')[1], name)
            return ('var', name)

        return ('number', 0)

    def parse_list(self):
        self.eat('LBRACKET')
        items = []
        while self.current_type() != 'RBRACKET':
            items.append(self.parse_expression())
            if self.current_type() == 'COMMA': self.eat('COMMA')
        self.eat('RBRACKET')
        return ('list', items)


def parse(tokens):
    return Parser(tokens).parse_block()
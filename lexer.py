import re

TOKENS = [
    # Commenti
    ('COMMENT',     r'--[^\n]*'),

    # Spazi e newline
    ('NEWLINE',     r'\n'),
    ('SKIP',        r'[ \t]+'),

    # Frecce
    ('ARROW',       r'>>|->'),

    # Numeri
    ('NUMBER',      r'\d+(\.\d+)?'),

    # Stringhe
    ('STRING',      r'"[^"]*"'),

    # MULTI-PAROLA (devono stare prima delle singole)
    ('SNAPSHOT',    r'\btake snapshot\b'),
    ('RESTORE',     r'\brestore snapshot\b'),
    ('CHECK_THAT',  r'\bcheck that\b'),
    ('LISTEN_FOR',  r'\blisten for\b'),
    ('REACT',       r'\breacts to\b'),
    ('ANNOTATE',    r'\bdescribed as\b'),
    ('MEASURED',    r'\bmeasured in\b'),
    ('OWNED',       r'\bowned by\b'),
    ('MEASURE',     r'\bmeasure time\b'),
    ('ELAPSED',     r'\belapsed time\b'),
    ('STATE',       r'\bcan be\b'),
    ('STARTS_AS',   r'\bstarts as\b'),
    ('CAN_GO',      r'\bcan go\b'),
    ('WITH_CTX',    r'\bwith context\b'),
    ('RANDOM_NUM',  r'\brandom number between\b'),
    ('RANDOM_ITEM', r'\brandom item from\b'),
    ('RANDOM_BOOL', r'\brandom true or false\b'),
    ('VALID_EMAIL', r'\bvalid email\b'),
    ('VALID_URL',   r'\bvalid url\b'),
    ('VALID_NUM',   r'\bvalid number\b'),
    ('VALIDATE',    r'\bvalidate\b'),
    ('LINES_OF',    r'\blines of\b'),
    ('SAVE_LOGS',   r'\bsave logs to\b'),
    ('STOP_TIMER',  r'\bstop timer\b'),
    ('START_TIMER', r'\bstart timer\b'),
    ('BAR_CHART',   r'\bas bar chart\b'),
    ('AS_LIST',     r'\bas list\b'),
    ('AS_PERCENTAGE', r'\bas percentage\b'),
    ('IN_BINARY',   r'\bin binary\b'),
    ('IN_HEX',      r'\bin hexadecimal\b'),
    ('ROUNDED_TO',  r'\brounded to\b'),
    ('DECIMALS',    r'\bdecimals\b'),
    ('SORT_BY',     r'\bsorted by\b'),

    # File ops
    ('READ',        r'\bread\b'),
    ('WRITE',       r'\bwrite\b'),
    ('APPEND',      r'\bappend\b'),

    # Table
    ('TABLE',       r'\btable\b'),
    ('ROW',         r'\brow\b'),
    ('COLUMN',      r'\bcolumn\b'),
    ('PIPE_SEP',    r'\|'),

    # Random
    ('SHUFFLED',    r'\bshuffled\b'),

    # Convert
    ('CELSIUS',     r'\bcelsius\b'),
    ('FAHRENHEIT',  r'\bfahrenheit\b'),
    ('KILOMETERS',  r'\bkilometers\b'),
    ('MILES',       r'\bmiles\b'),
    ('BYTES',       r'\bbytes\b'),
    ('KILOBYTES',   r'\bkilobytes\b'),
    ('MEGABYTES',   r'\bmegabytes\b'),
    ('SECONDS_U',   r'\bseconds\b'),
    ('MINUTES',     r'\bminutes\b'),
    ('HOURS',       r'\bhours\b'),
    ('DEGREES',     r'\bdegrees\b'),
    ('RADIANS',     r'\bradians\b'),

    # Format
    ('FORMATTED',   r'\bformatted\b'),
    ('SHOW',        r'\bshow\b'),

    # Log
    ('LOG',         r'\blog\b'),
    ('LEVEL',       r'\blevel\b'),
    ('WARNING',     r'\bwarning\b'),
    ('ERROR_LVL',   r'\berror\b'),
    ('INFO',        r'\binfo\b'),

    # Schedule
    ('AFTER',       r'\bafter\b'),
    ('TIMER',       r'\btimer\b'),

    # Compare
    ('COMPARE',     r'\bcompare\b'),

    # Alias
    ('ALIAS',       r'\balias\b'),
    ('MEANS',       r'\bmeans\b'),

    # Chain
    ('THEN_CHAIN',  r'\bthen\b'),
    ('CLEAN',       r'\bclean\b'),
    ('CAPITALIZE',  r'\bcapitalize\b'),
    ('CLAMP',       r'\bclamp\b'),

    # Keywords singole
    ('GIVEN',       r'\bgiven\b'),
    ('REMEMBER',    r'\bremember\b'),
    ('RECALL',      r'\brecall\b'),
    ('FORGET',      r'\bforget\b'),
    ('EXPLAIN',     r'\bexplain\b'),
    ('WATCH',       r'\bwatch\b'),
    ('UNWATCH',     r'\bunwatch\b'),
    ('DEBUG',       r'\bdebug\b'),
    ('USE',         r'\buse\b'),
    ('WAIT',        r'\bwait\b'),
    ('CURRENT',     r'\bcurrent\b'),
    ('UNTIL',       r'\buntil\b'),
    ('EVERY',       r'\bevery\b'),
    ('WHENEVER',    r'\bwhenever\b'),
    ('OTHERWISE',   r'\botherwise\b'),
    ('ASSUME',      r'\bassume\b'),
    ('REQUIRE',     r'\brequire\b'),
    ('UNLESS',      r'\bunless\b'),
    ('DEFINED',     r'\bdefined\b'),
    ('NEVER',       r'\bnever\b'),
    ('BECOMES',     r'\bbecomes\b'),
    ('ABOVE',       r'\babove\b'),
    ('BELOW',       r'\bbelow\b'),
    ('BETWEEN',     r'\bbetween\b'),
    ('REPEAT',      r'\brepeat\b'),
    ('TIMES',       r'\btimes\b'),
    ('COUNT',       r'\bcount\b'),
    ('FROM',        r'\bfrom\b'),
    ('START',       r'\bstart\b'),
    ('WITH',        r'\bwith\b'),
    ('KEEP',        r'\bkeep\b'),
    ('EACH',        r'\beach\b'),
    ('ONLY',        r'\bonly\b'),
    ('ONES',        r'\bones\b'),
    ('THE',         r'\bthe\b'),
    ('DOUBLE',      r'\bdouble\b'),
    ('HALF',        r'\bhalf\b'),
    ('SQUARE',      r'\bsquare\b'),
    ('ROUND',       r'\bround\b'),
    ('PERCENT',     r'\bpercent\b'),
    ('REMAINDER',   r'\bremainder\b'),
    ('DIVIDED',     r'\bdivided\b'),
    ('AVERAGE',     r'\baverage\b'),
    ('TOTAL',       r'\btotal\b'),
    ('SORTED',      r'\bsorted\b'),
    ('REVERSED',    r'\breversed\b'),
    ('BEST',        r'\bbest\b'),
    ('WORST',       r'\bworst\b'),
    ('HITS',        r'\bhits\b'),
    ('GOES',        r'\bgoes\b'),
    ('GOING',       r'\bgoing\b'),
    ('KEEPS',       r'\bkeeps\b'),
    ('FALLS',       r'\bfalls\b'),
    ('CHANGES',     r'\bchanges\b'),
    ('LINKED',      r'\blinked\b'),
    ('WHEN',        r'\bwhen\b'),
    ('FASTER',      r'\bfaster\b'),
    ('SLOWER',      r'\bslower\b'),
    ('MUCH',        r'\bmuch\b'),
    ('ROLE',        r'\brole\b'),
    ('ROLES',       r'\broles\b'),
    ('ZONE',        r'\bzone\b'),
    ('CALLED',      r'\bcalled\b'),
    ('UPPERCASE',   r'\buppercase\b'),
    ('LOWERCASE',   r'\blowercase\b'),
    ('CAPITALIZED', r'\bcapitalized\b'),
    ('LENGTH',      r'\blength\b'),
    ('CONTAINS',    r'\bcontains\b'),
    ('STARTS',      r'\bstarts\b'),
    ('ENDS',        r'\bends\b'),
    ('WITHOUT',     r'\bwithout\b'),
    ('REPEATED',    r'\brepeated\b'),
    ('FIRST',       r'\bfirst\b'),
    ('LAST',        r'\blast\b'),
    ('LETTERS',     r'\bletters\b'),
    ('EMPTY',       r'\bempty\b'),
    ('PREVIOUS',    r'\bprevious\b'),
    ('VALUE',       r'\bvalue\b'),
    ('HISTORY',     r'\bhistory\b'),
    ('HIGHEST',     r'\bhighest\b'),
    ('LOWEST',      r'\blowest\b'),
    ('DEFINITELY',  r'\bdefinitely\b'),
    ('PROBABLY',    r'\bprobably\b'),
    ('MAYBE',       r'\bmaybe\b'),
    ('DO',          r'\bdo\b'),
    ('TRY',         r'\btry\b'),
    ('TO',          r'\bto\b'),
    ('BUT',         r'\bbut\b'),
    ('IF',          r'\bif\b'),
    ('AND',         r'\band\b'),
    ('OR',          r'\bor\b'),
    ('NOT',         r'\bnot\b'),
    ('IS',          r'\bis\b'),
    ('AT',          r'\bat\b'),
    ('LEAST',       r'\bleast\b'),
    ('MOST',        r'\bmost\b'),
    ('SAY',         r'\bsay\b'),
    ('ASK',         r'\bask\b'),
    ('HAS',         r'\bhas\b'),
    ('HAVE',        r'\bhave\b'),
    ('CAN',         r'\bcan\b'),
    ('BY',          r'\bby\b'),
    ('UP',          r'\bup\b'),
    ('DOWN',        r'\bdown\b'),
    ('FOR',         r'\bfor\b'),
    ('IN',          r'\bin\b'),
    ('OF',          r'\bof\b'),
    ('FAILS',       r'\bfails\b'),
    ('TRUE',        r'\btrue\b'),
    ('FALSE',       r'\bfalse\b'),
    ('AN',          r'\ban\b'),
    ('A',           r'\ba\b'),
    ('GIVE',        r'\bgive\b'),
    ('BACK',        r'\bback\b'),
    ('AGAIN',       r'\bagain\b'),
    ('YES',         r'\byes\b'),
    ('NO',          r'\bno\b'),
    ('NUMBER_KW',   r'\bnumber\b'),
    ('SECOND',      r'\bsecond\b'),
    ('TIME',        r'\btime\b'),
    ('DATE',        r'\bdate\b'),
    ('DAY',         r'\bday\b'),
    ('WEEK',        r'\bweek\b'),
    ('ON',          r'\bon\b'),
    ('OFF',         r'\boff\b'),
    ('AS',          r'\bas\b'),
    ('CONTEXT',     r'\bcontext\b'),
    ('ADD',         r'\badd\b'),
    ('REMOVE',      r'\bremove\b'),
    ('WHERE',       r'\bwhere\b'),
    ('POSITIVE',    r'\bpositive\b'),
    ('NEGATIVE',    r'\bnegative\b'),
    ('ONE',         r'\bone\b'),
    ('ARE',         r'\bare\b'),

    # Simboli
    ('COMMA',       r','),
    ('COLON',       r':'),
    ('LBRACKET',    r'\['),
    ('RBRACKET',    r'\]'),
    ('LPAREN',      r'\('),
    ('RPAREN',      r'\)'),

    # Operatori
    ('PLUS',        r'\+'),
    ('MINUS',       r'-'),
    ('TIMES_OP',    r'\*'),
    ('DIVIDE_OP',   r'/'),
    ('GTE',         r'>='),
    ('LTE',         r'<='),
    ('GT',          r'>'),
    ('LT',          r'<'),
    ('EQ',          r'=='),

    # Identificatori
    ('IDENT',       r'[a-zA-Z_][a-zA-Z0-9_]*'),
]

def tokenize(source):
    tokens = []
    pos = 0
    line = 1

    while pos < len(source):
        match = None

        for token_type, pattern in TOKENS:
            regex = re.compile(pattern)
            match = regex.match(source, pos)

            if match:
                value = match.group(0)

                if token_type == 'NEWLINE':
                    line += 1
                    tokens.append(('NEWLINE', '\n', line))
                elif token_type == 'COMMENT':
                    pass
                elif token_type == 'SKIP':
                    pass
                elif token_type == 'NUMBER':
                    tokens.append((token_type,
                        float(value) if '.' in value else int(value), line))
                elif token_type == 'STRING':
                    tokens.append((token_type, value[1:-1], line))
                else:
                    tokens.append((token_type, value, line))

                pos = match.end()
                break

        if not match:
            raise SyntaxError(
                f"FigLang: unexpected character '{source[pos]}' on line {line}"
            )

    tokens.append(('EOF', None, line))
    return tokens
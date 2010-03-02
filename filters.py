# Keyword Filter Parser

EXCLUDE = 0
INCLUDE = 1

ALL = 0xf
TITLE = 1
LINK = 2
AUTHOR = 4
CONTENT = 8

TYPES = {
    None: INCLUDE,
    '+': INCLUDE,
    '-': EXCLUDE,
}

QUALIFIERS = {
    None: ALL,
    'title:': TITLE,
    'link:': LINK,
    'author:': AUTHOR,
    'content:': CONTENT,
}

TYPE_STR = {
    EXCLUDE: '-',
    INCLUDE: '+',
}

QUALIFIER_STR = {
    ALL: 'all',
    TITLE: 'title',
    LINK: 'link',
    AUTHOR: 'author',
    CONTENT: 'content',
}

class Rule(object):
    def __init__(self, type, qualifier, word):
        self.type = TYPES.get(type, type)
        self.qualifier = QUALIFIERS.get(qualifier, qualifier)
        self.word = word
    def evaluate(self, item, ignore_case=True, whole_word=True):
        strings = []
        if self.qualifier & TITLE:
            strings.append(item.title)
        if self.qualifier & LINK:
            strings.append(item.link)
        if self.qualifier & AUTHOR:
            strings.append(item.author)
        if self.qualifier & CONTENT:
            strings.append(item.description)
        text = '\n'.join(strings)
        word = self.word
        if ignore_case:
            text = text.lower()
            word = word.lower()
        if whole_word:
            text = set(text.split())
        if word in text:
            return self.type == INCLUDE
        else:
            return self.type == EXLCUDE
    def __str__(self):
        type = TYPE_STR[self.type]
        qualifier = QUALIFIER_STR[self.qualifier]
        return '(%s, %s, "%s")' % (type, qualifier, self.word)
        
class AndRule(object):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def evaluate(self, item, ignore_case=True, whole_word=True):
        a = self.left.evaluate(item, ignore_case, whole_word) 
        b = self.right.evaluate(item, ignore_case, whole_word)
        return a and b
    def __str__(self):
        return '(%s and %s)' % (self.left, self.right)
        
class OrRule(object):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def evaluate(self, item, ignore_case=True, whole_word=True):
        a = self.left.evaluate(item, ignore_case, whole_word) 
        b = self.right.evaluate(item, ignore_case, whole_word)
        return a or b
    def __str__(self):
        return '(%s or %s)' % (self.left, self.right)
        
class NotRule(object):
    def __init__(self, rule):
        self.rule = rule
    def evaluate(self, item, ignore_case=True, whole_word=True):
        return not self.rule.evaluate(item, ignore_case, whole_word)
    def __str__(self):
        return '(not %s)' % (self.rule)
        
# Lexer Rules
reserved = {
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
}

tokens = [
    'PLUS',
    'MINUS',
    'LPAREN',
    'RPAREN',
    'TITLE',
    'LINK',
    'AUTHOR',
    'CONTENT',
    'WORD',
] + reserved.values()

t_PLUS = r'\+'
t_MINUS = r'\-'
t_LPAREN = r'\('
t_RPAREN = r'\)'

def t_TITLE(t):
    r'title:'
    return t
    
def t_LINK(t):
    r'link:'
    return t
    
def t_AUTHOR(t):
    r'author:'
    return t
    
def t_CONTENT(t):
    r'content:'
    return t
    
def t_WORD(t):
    r'(\'[^\']+\') | (\"[^\"]+\") | ([^ \n\t\r+\-()\'"]+)'
    t.type = reserved.get(t.value, 'WORD')
    if t.value[0] == '"' and t.value[-1] == '"':
        t.value = t.value[1:-1]
    if t.value[0] == "'" and t.value[-1] == "'":
        t.value = t.value[1:-1]
    return t
    
t_ignore = ' \n\t\r'

def t_error(t):
    raise Exception
    
# Parser Rules
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT')
)

def p_filter(t):
    'filter : expression'
    t[0] = t[1]
    
def p_expression_rule(t):
    'expression : rule'
    t[0] = t[1]
    
def p_expression_and(t):
    'expression : expression AND expression'
    t[0] = AndRule(t[1], t[3])
    
def p_expression_or(t):
    'expression : expression OR expression'
    t[0] = OrRule(t[1], t[3])
    
def p_expression_not(t):
    'expression : NOT expression'
    t[0] = NotRule(t[2])
    
def p_expression_group(t):
    'expression : LPAREN expression RPAREN'
    t[0] = t[2]
    
def p_rule(t):
    'rule : type qualifier WORD'
    t[0] = Rule(t[1], t[2], t[3])
    
def p_type(t):
    '''type : PLUS
            | MINUS
            | empty'''
    t[0] = t[1]
    
def p_qualifier(t):
    '''qualifier : TITLE 
                 | LINK 
                 | AUTHOR 
                 | CONTENT
                 | empty'''
    t[0] = t[1]
    
def p_empty(t):
    'empty :'
    pass
    
def p_error(t):
    raise Exception
    
import ply.lex as lex
import ply.yacc as yacc

lexer = lex.lex()
parser = yacc.yacc()

def parse(text):
    return parser.parse(text, lexer=lexer)
    
if __name__ == '__main__':
    while True:
        text = raw_input('> ')
        print parse(text)
        
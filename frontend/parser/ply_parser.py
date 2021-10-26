"""
Module that defines a parser using `ply.yacc`.
Add your own parser rules on demand, which can be accomplished by:

1. Define a global function whose name starts with "p_".
2. Write the corresponding grammar rule(s) in its docstring.
3. Complete the function body, which is actually a syntax base translation process.
    We're using this technique to build up the AST.

Refer to https://www.dabeaz.com/ply/ply.html for more details.
"""


import ply.yacc as yacc

from frontend.ast.tree import *
from frontend.lexer import lex
from frontend.type.array import ArrayType
from utils.error import DecafSyntaxError

tokens = lex.tokens
error_stack = list[DecafSyntaxError]()


def unary(p):
    p[0] = Unary(UnaryOp.backward_search(p[1]), p[2])


def binary(p):
    if p[2] == BinaryOp.Assign.value:
        p[0] = Assignment(p[1], p[3])
    else:
        p[0] = Binary(BinaryOp.backward_search(p[2]), p[1], p[3])


def p_empty(p: yacc.YaccProduction):
    """
    empty :
    """
    pass

def p_program(p):
    """
    program : program element
    """
    if p[2] is not NULL:
        p[1].children.append(p[2])
    p[0] = p[1]

def p_element(p):
    """
    element : declaration Semi
            | function
    """
    p[0] = p[1]

def p_program_empty(p):
    """
    program : empty
    """
    p[0] = Program()

def p_type(p):
    """
    type : Int
    """
    p[0] = TInt()

def p_function_def(p):
    """
    function : type Identifier LParen RParen LBrace block RBrace
    """
    p[0] = Function(p[1], p[2], p[6])

def p_function_para_def(p):
    """
    function : type Identifier LParen parameter RParen LBrace block RBrace
    """
    p[0] = Function(p[1], p[2], p[7], p[4])

def p_parameter(p):
    """
    parameter : parameter parameter_item
    """
    if p[2] is not NULL:
        p[1].children.append(p[2])
    p[0] = p[1]

def p_parameter_empty(p):
    """
    parameter : empty
    """
    p[0] = Parameter()

def p_parameter_item1(p):
    """
    parameter_item : Comma declaration
    """
    p[0] = p[2]

def p_parameter_item2(p):
    """
    parameter_item : declaration
    """
    p[0] = p[1]

def p_block(p):
    """
    block : block block_item
    """
    if p[2] is not NULL:
        p[1].children.append(p[2])
    p[0] = p[1]


def p_block_empty(p):
    """
    block : empty
    """
    p[0] = Block()


def p_block_item(p):
    """
    block_item : statement
        | declaration Semi
    """
    p[0] = p[1]


def p_statement(p):
    """
    statement : statement_matched
        | statement_unmatched
    """
    p[0] = p[1]


def p_if_else(p):
    """
    statement_matched : If LParen expression RParen statement_matched Else statement_matched
    statement_unmatched : If LParen expression RParen statement_matched Else statement_unmatched
    """
    p[0] = If(p[3], p[5], p[7])


def p_if(p):
    """
    statement_unmatched : If LParen expression RParen statement
    """
    p[0] = If(p[3], p[5])


def p_while(p):
    """
    statement_matched : While LParen expression RParen statement_matched
    statement_unmatched : While LParen expression RParen statement_unmatched
    """
    p[0] = While(p[3], p[5])

def p_do_while(p):
    """
    statement_matched : Do statement_matched While expression Semi
    statement_unmatched : Do statement_unmatched While expression Semi
    """
    p[0] = DoWhile(p[2], p[4])


def p_for_3(p):
    """
    statement_matched : For LParen expression Semi expression Semi expression RParen statement_matched
                    | For LParen declaration Semi expression Semi expression RParen statement_matched
    statement_unmatched : For LParen expression Semi expression Semi expression RParen statement_unmatched
                    | For LParen declaration Semi expression Semi expression RParen statement_unmatched
    """
    p[0] = For(p[3], p[5], p[7], p[9])

def p_for_2_1(p):
    """
    statement_matched : For LParen Semi expression Semi expression RParen statement_matched
    statement_unmatched : For LParen Semi expression Semi expression RParen statement_unmatched
    """
    p[0] = For(None, p[4], p[6], p[8])

def p_for_2_2(p):
    """
    statement_matched : For LParen expression Semi Semi expression RParen statement_matched
                    | For LParen declaration Semi Semi expression RParen statement_matched
    statement_unmatched : For LParen expression Semi Semi expression RParen statement_unmatched
                    | For LParen declaration Semi Semi expression RParen statement_unmatched
    """
    p[0] = For(p[3], None, p[6], p[8])

def p_for_2_3(p):
    """
    statement_matched : For LParen expression Semi expression Semi RParen statement_matched
                    | For LParen declaration Semi expression Semi RParen statement_matched
    statement_unmatched : For LParen expression Semi expression Semi RParen statement_unmatched
                    | For LParen declaration Semi expression Semi RParen statement_unmatched
    """
    p[0] = For(p[3], p[5], None, p[8])

def p_for_1_1(p):
    """
    statement_matched : For LParen expression Semi Semi RParen statement_matched
                    | For LParen declaration Semi Semi RParen statement_matched
    statement_unmatched : For LParen expression Semi Semi RParen statement_unmatched
                    | For LParen declaration Semi Semi RParen statement_unmatched
    """
    p[0] = For(p[3], None, None, p[7])

def p_for_1_2(p):
    """
    statement_matched : For LParen Semi expression Semi RParen statement_matched
    statement_unmatched : For LParen Semi expression Semi RParen statement_unmatched
    """
    p[0] = For(None, p[4], None, p[7])

def p_for_1_3(p):
    """
    statement_matched : For LParen Semi Semi expression RParen statement_matched
    statement_unmatched : For LParen Semi Semi expression RParen statement_unmatched
    """
    p[0] = For(None, None, p[5], p[7])

def p_for_0(p):
    """
    statement_matched : For LParen Semi Semi RParen statement_matched
    statement_unmatched : For LParen Semi Semi RParen statement_unmatched
    """
    p[0] = For(None, None, None, p[6])

def p_return(p):
    """
    statement_matched : Return expression Semi
    """
    p[0] = Return(p[2])


def p_expression_statement(p):
    """
    statement_matched : opt_expression Semi
    """
    p[0] = p[1]


def p_block_statement(p):
    """
    statement_matched : LBrace block RBrace
    """
    p[0] = p[2]


def p_break(p):
    """
    statement_matched : Break Semi
    """
    p[0] = Break()

def p_continue(p):
    """
    statement_matched : Continue Semi
    """
    p[0] = Continue()


def p_opt_expression(p):
    """
    opt_expression : expression
    """
    p[0] = p[1]


def p_opt_expression_empty(p):
    """
    opt_expression : empty
    """
    p[0] = NULL


def p_declaration(p):
    """
    declaration : type Identifier
    """
    p[0] = Declaration(p[1], p[2])

def p_declaration_array(p):
    """
    declaration : type Identifier dimension
    """
    if(len(p[3].dims) == 0):
        p[0] = Declaration(p[1], p[2])
    else:
        dim_list = []
        for i in p[3].dims:
            dim_list.append(i.value)
        dim_list.reverse()
        if(len(dim_list) == 1):
            p[0] = Declaration(TArray(ArrayType(INT, dim_list[0])), p[2])
        else:
            length = 1
            for d in dim_list:
                length *= d
            T = ArrayType(INT, dim_list[0])
            for i in range(1, len(dim_list)):
                T = ArrayType(T, dim_list[i])
            p[0] = Declaration(TArray(T), p[2])
    
def p_dimension(p):
    """
    dimension : dimension LSB Integer RSB
    """
    if p[3] is not NULL:
        p[1].dims.append(p[3])
    p[0] = p[1]

def p_dimension_empty(p):
    """
    dimension : empty
    """
    p[0] = Dimension()

def p_declaration_init(p):
    """
    declaration : type Identifier Assign expression
    """
    p[0] = Declaration(p[1], p[2], p[4])


def p_expression_precedence(p):
    """
    expression : assignment
    assignment : conditional
    conditional : logical_or
    logical_or : logical_and
    logical_and : bit_or
    bit_or : xor
    xor : bit_and
    bit_and : equality
    equality : relational
    relational : additive
    additive : multiplicative
    multiplicative : unary
    unary : postfix
    unary : indexexpr
    postfix : primary
    """
    p[0] = p[1]

def p_postfix(p):
    """
    postfix : Identifier LParen expression_list RParen
    """
    p[0] = Postfix(p[1], p[3])

# def p_postfix_array(p):
#     """
#     postfix : indexexpr LSB expression RSB
#     """
#     if(p[3] is not NULL):
#         p[1].index.append(p[3])
#     p[0] = p[1]
    

def p_indexexpr(p):
    """
    indexexpr : indexexpr LSB expression RSB
    """
    if(p[3] is not NULL):
        p[1].index.append(p[3])
    p[0] = p[1]

def p_indexexpr_empty(p):
    """
    indexexpr : Identifier
    """
    p[0] = IndexExpr(p[1])

def p_expression_list(p):
    """
    expression_list : expression_list expression_item
    """
    if p[2] is not NULL:
        p[1].children.append(p[2])
    p[0] = p[1]

def p_expression_list_empty(p):
    """
    expression_list : empty
    """
    p[0] = ExpressionList()

def p_expression_item1(p):
    """
    expression_item : Comma expression
    """
    p[0] = p[2]

def p_expression_item2(p):
    """
    expression_item : expression
    """
    p[0] = p[1]

def p_unary_expression(p):
    """
    unary : Minus unary
        | BitNot unary
        | Not unary
    """
    unary(p)


def p_binary_expression(p):
    """
    assignment : Identifier Assign expression
    assignment : indexexpr Assign expression
    logical_or : logical_or Or logical_and
    logical_and : logical_and And bit_or
    bit_or : bit_or BitOr xor
    xor : xor Xor bit_and
    bit_and : bit_and BitAnd equality
    equality : equality NotEqual relational
        | equality Equal relational
    relational : relational Less additive
        | relational Greater additive
        | relational LessEqual additive
        | relational GreaterEqual additive
    additive : additive Plus multiplicative
        | additive Minus multiplicative
    multiplicative : multiplicative Mul unary
        | multiplicative Div unary
        | multiplicative Mod unary
    """
    binary(p)


def p_conditional_expression(p):
    """
    conditional : logical_or Question expression Colon conditional
    """
    p[0] = ConditionExpression(p[1], p[3], p[5])


def p_int_literal_expression(p):
    """
    primary : Integer
    """
    p[0] = p[1]


def p_identifier_expression(p):
    """
    primary : Identifier
    """
    p[0] = p[1]


def p_brace_expression(p):
    """
    primary : LParen expression RParen
    """
    p[0] = p[2]


def p_error(t):
    """
    A naive (and possibly erroneous) implementation of error recovering.
    """
    if not t:
        error_stack.append(DecafSyntaxError(t, "EOF"))
        return

    inp = t.lexer.lexdata
    error_stack.append(DecafSyntaxError(t, f"\n{inp.splitlines()[t.lineno - 1]}"))

    parser.errok()
    return parser.token()


parser = yacc.yacc(start="program")
parser.error_stack = error_stack  # type: ignore

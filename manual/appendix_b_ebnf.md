# Appendix B: LL(1) EBNF Grammar

SINC was deliberately designed with an LL(1) grammar. This choice enables compiling SINC programs in a single pass directly from the token stream to intermediate representation without building a memory-heavy Abstract Syntax Tree (AST).

Here is the formal Extended Backus-Naur Form (EBNF) specification of the language.

---

## Lexical Grammar

Identifiers in SINC contain both their name and their type/usage flags. The lexer recognises the following token patterns:

```ebnf
Digit          ::= [0-9]
Letter         ::= [a-zA-Z] | "_"
IdentStart     ::= Letter
IdentChar      ::= Letter | Digit
BoundSuffix    ::= ":" Digit+
EffectOrBorrow ::= "~" | "!"

IntLiteral     ::= Digit+

(* Identifiers include optional refinement bounds followed by trailing effect/borrow markers *)
Identifier     ::= IdentStart IdentChar* BoundSuffix? EffectOrBorrow?
```

---

## Syntactic Grammar

### Top-Level Declarations

A SINC source file consists of constant declarations, function definitions, and external declarations:

```ebnf
Program        ::= (Function | Extern | Const)*
Const          ::= "const" Identifier "=" "-"? IntLiteral ";"
Function       ::= "fn" Identifier "(" ParamList ")" Block
Extern         ::= "extern" "fn" Identifier "(" ")" ";"
ParamList      ::= (Param ("," Param)*)?
Param          ::= Identifier
```

### Statements

Statements in SINC control execution flow or assign values. All simple statements end with a semicolon `;`.

```ebnf
Block          ::= "[" Stmt* "]"
Stmt           ::= ReturnStmt | IfStmt | LoopStmt | AssignOrExprStmt

ReturnStmt     ::= "ret" Expr ";"
IfStmt         ::= "if" Expr Block ("else" (IfStmt | Block))?
LoopStmt       ::= "loop" ("(" LoopHeader ")")? Block
LoopHeader     ::= Identifier "=" Expr ".." Expr
AssignOrExprStmt ::= Expr ("=" Expr)? ";"
```

*Note: SINC allows the loop header parenthesis to be completely optional. Both `loop (i = 0 .. 10)` and `loop i = 0 .. 10` are valid syntax.*

### Expressions

Expressions are parsed using operator-precedence parsing:

```ebnf
Expr           ::= PrimaryExpr (BinaryOp Expr | PostfixOp | LensOrUFCS)*

PrimaryExpr    ::= IntLiteral
                 | Identifier (* variables and function calls *)
                 | "-" Expr
                 | "!" Expr
                 | "(" Expr ")"

BinaryOp       ::= "==" | "!=" | "<" | ">" | "|" | "&" | "^" | "<<" | ">>" | "+" | "-" | "*" | "/"
PostfixOp      ::= "@" ("[" Expr ("*" IntLiteral)? "]")?
LensOrUFCS     ::= "." Identifier
```

---

## Operator Precedence

Operators are evaluated according to their binding power (lowest to highest), as defined in `sinc/pure/parser_pratt.sinc`:

| Precedence | Operator | Description | Binding Power (Left / Right) |
| :---: | :--- | :--- | :---: |
| **1** | `==`, `!=`, `<`, `>` | Comparisons | 5 / 6 (Lowest) |
| **2** | `\|` | Bitwise OR | 7 / 8 |
| **3** | `&`, `^` | Bitwise AND, XOR | 9 / 10 |
| **4** | `<<`, `>>` | Bitwise Shifts | 11 / 12 |
| **5** | `+`, `-` | Addition / Subtraction | 13 / 14 |
| **6** | `*`, `/` | Multiplication / Division | 15 / 16 (Highest) |
| **7** | `@` | Postfix Dereference / Subscript | (Unary Postfix) |
| **8** | `.` | Constant Lens / Field Access | (Unary Postfix) |

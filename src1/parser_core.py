from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional

from constants import TYPES, EOF

EPS = "epsilon"
# 用于输出的中文别名
ALIAS = {
    "S": "程序",
    "Decl": "声明",
    "TypedefDecl": "类型别名声明",
    "TypedefRhs": "typedef右部",
    "TypedefStruct": "typedef结构体",
    "TypedefStructHead": "typedef结构体头",
    "TypedefStructTail": "typedef结构体尾",
    "TypeAlias": "类型别名",
    "StructDecl": "结构体声明",
    "StructHead": "结构体头",
    "StructAfterTag": "结构体标签后缀",
    "AfterStructBody": "结构体体后缀",
    "Type": "类型",
    "BaseType": "基础类型",
    "Ptr": "指针",
    "DeclSuf": "声明后缀",
    "VarTail": "变量尾部",
    "VarSuf": "变量后缀",
    "InitOpt": "可选初始化",
    "NextDecl": "后续声明",
    "Init": "初始化",
    "InitList": "初始化列表",
    "NextInit": "后续初始化",
    "MemberList": "成员列表",
    "Member": "成员",
    "MemberType": "成员类型",
    "Block": "语句块",
    "StmtList": "语句序列",
    "Stmt": "语句",
    "DeclStmt": "声明语句",
    "RetStmt": "返回语句",
    "RetVal": "返回值",
    "IfStmt": "条件语句",
    "ElsePart": "else分支",
    "ForStmt": "循环语句",
    "ForInit": "循环初始化",
    "ExprOpt": "可选表达式",
    "ForStep": "循环步进",
    "SimpleStmt": "简单语句",
    "AssignOrCall": "赋值或调用",
    "AssignOp": "赋值运算符",
    "Expr": "表达式",
    "E_": "表达式续",
    "Term": "项",
    "Unary": "一元运算",
    "TermSuf": "项后缀",
    "Params": "形参列表",
    "Args": "实参列表",
    "NextArg": "后续实参",
}


@dataclass(frozen=True)
class Grammar:
    start: str
    prods: Dict[str, List[List[str]]]

    @property
    def nonterminals(self) -> Set[str]:
        return set(self.prods.keys())

    @property
    def terminals(self) -> Set[str]:
        nts = self.nonterminals
        ts: Set[str] = set()
        for alts in self.prods.values():
            for rhs in alts:
                for s in rhs:
                    if s != EPS and s not in nts:
                        ts.add(s)
        ts.add("EOF")
        return ts


def c_grammar() -> Grammar:
    g: Dict[str, List[List[str]]] = {
        "S": [
            ["Type", "Declarator", "DeclSuf", "S"], # 关键：引入 Declarator 处理指针+id
            ["TypedefDecl", "S"],
            ["StructDecl", "S"],
            [EPS]
        ],
        
        "Declarator": [
            ["Pointer", "id"] # 支持 *tree_setup 或直接 tree_setup
        ],

        "Decl": [["TypedefDecl"], ["StructDecl"], ["NonStructDecl"]],
        "NonStructDecl": [["Type", "id", "DeclSuf"]],

        "TypedefDecl": [["typedef", "TypedefRhs", "id", ";"]],
        "TypedefRhs": [["Type"], ["TypedefStruct"]],
        "TypedefStruct": [["struct", "TypedefStructBody"]],
        "TypedefStructBody": [
            ["id", "TypedefStructAfterId"], # 情况：struct id { ... } 或 struct id
            ["{", "MemberList", "}", "Ptr"] # 情况：struct { ... }
        ],
        "TypedefStructAfterId": [
            ["{", "MemberList", "}", "Ptr"], # 明确匹配带标签的定义
            ["Ptr"]                          # 明确匹配仅声明（如 struct _node *p;）
        ],
        "TypedefStructOptBody": [
            ["{", "MemberList", "}", "Ptr"], # 匹配 struct _node { ... }
            ["Ptr"]                         # 匹配 struct _node (仅引用)
        ],
        "TypedefStructHead": [["{", "MemberList", "}", "Ptr"], ["id", "TypedefStructTail"]],
        "TypedefStructTail": [["{", "MemberList", "}", "Ptr"], ["Ptr"]],
        "TypeAlias": [["id"]],

        "StructDecl": [["struct", "StructHead"]],
        "StructHead": [["id", "StructAfterTag"], ["{", "MemberList", "}", "AfterStructBody"]],
        "StructAfterTag": [["{", "MemberList", "}", "AfterStructBody"], ["Ptr", "id", "DeclSuf"]],
        "AfterStructBody": [[";"], ["Pointer", "id", "VarSuf", "NextDecl"]],

        "Type": [
            ["BaseType"], 
            ["id"],      # Node
            ["type_id"]  # 别名
        ],
        "TypeName": [
            ["BaseType"], 
            ["id"],      # 处理尚未注册的 Node
            ["type_id"]  # 处理已注册的 Node
        ],
        "BaseType": [
            ["int"], ["char"], ["float"], ["double"], ["void"], 
            ["long"], ["short"], ["signed"], ["unsigned"]
        ],
        "Ptr": [
            ["*", "Ptr"], 
            [EPS]
        ],

        "DeclSuf": [
            ["(", "Params", ")", "FuncSuf"], 
            ["VarTail"]
        ],
        "FuncSuf": [
            ["Block"], # 对应函数定义 { ... }
            [";"]      # 对应函数声明 ;
        ],

        "VarTail": [["VarSuf", "InitPart", "NextDecl"]],
        "VarSuf": [["[", "int_lit", "]", "VarSuf"], [EPS]],
        "InitPart": [
            ["=", "Init"], # 支持 char* p = s;
            [EPS]
        ],
        "ArrayLen": [
            ["int_lit"],
            ["id"]
        ],
        "InitOpt": [["=", "Init"], [EPS]],
        "NextDecl": [[",", "Declarator", "VarSuf", "InitPart", "NextDecl"], [";"]],
        
        "VarDefine": [
            ["Pointer", "id", "VarSuf"] 
        ],
        
        "Pointer": [
            ["*", "Pointer"], 
            [EPS]
        ],

        "Init": [
            ["{", "InitList", "}"], 
            ["Expr"]
        ],
        "InitList": [["Init", "NextInit"]],
        "NextInit": [[",", "Init" ,"NextInit"], [EPS]],

        "MemberList": [["Member", "MemberList"], [EPS]],
        "Member": [["MemberType", "id", "VarSuf", ";"]],
        "MemberType": [["Type"], ["struct", "id", "Ptr"]],

        "Block": [["{", "InnerContent", "}"]],
        "InnerContent": [
            ["BaseType", "Declarator", "VarSuf", "InitPart", "NextDecl", "InnerContent"], # 处理 int a;
            ["id", "IdStartAfter", "InnerContent"], # 处理 bt = ... 或 Node *p;
            ["Stmt", "InnerContent"],               # 处理 if, while, return 等关键字语句
            [EPS]
        ],
        "IdStartAfter": [
            ["Pointer", "id", "VarSuf", "InitPart", "NextDecl"], # 路径 A: 变量定义 (如 Node *p;)
            ["StmtIdTail"]                       # 路径 B: 赋值或调用 (如 bt = ... 或 bt++;)
        ],
        "LocalDecl": [
            ["Type", "Declarator", "VarSuf", "NextDecl"]
        ],
        "StmtList": [["Stmt", "StmtList"], [EPS]],

        "Stmt": [
            ["id", "StmtIdTail"],  # 修改这一行，处理以 id 开头的各种情况
            ["if", "(", "Expr", ")", "Stmt", "ElseStat"],
            ["while", "(", "Expr", ")", "Stmt"],
            ["return", "ReturnTail"],
            ["goto", "id", ";"],
            ["break", ";"],      # <--- 新增：支持 break;
            ["continue", ";"],   # <--- 新增：支持 continue;
            ["Block"],
            [";"]
        ],
        
        "ReturnTail": [
            ["Expr", ";"], # 支持 return 0; 或 return x+1;
            [";"]          # 支持 return;
        ],
        
        "StmtIdTail": [
            [":", "Stmt"],          # 标签逻辑: there:
            ["++", ";"],            # 匹配 p++;
            ["--", ";"],            # 匹配 p--;
            ["=", "Expr", ";"],     # 匹配赋值: p = s;
            ["(", "Args", ")", ";"] # 匹配调用: gets(s);
        ],

        "DeclStmt": [["Decl"]],
        # --- 4. 基础因子层：处理变量、常量、指针取值、函数调用 ---
        "Primary": [
            ["(", "Expr", ")"],
            ["*", "Primary"],      # 支持 *p
            ["&", "Primary"],      # 支持 &q
            ["id", "PrimaryTail"], # 处理变量名或函数名
            ["int_lit"],
            ["float_lit"],
            ["string_lit"],
            ["char_lit"]
        ],
        # --- 5. 因子后缀：处理函数调用 gets(s) 或自增 p++ ---
        "PrimaryTail": [
            ["(", "Args", ")", "PrimaryTail"], # 函数调用
            ["[", "Expr", "]", "PrimaryTail"], # 数组访问
            [".", "id", "PrimaryTail"],       # 核心修复：支持 book.price
            ["++"],                            # 自增
            ["--"],                            # 自减
            [EPS]
        ],
        "PostOp": [
            ["++"], 
            ["--"], 
            [EPS]
        ],

        "RetStmt": [["return", "RetVal", ";"]],
        "RetVal": [["Expr"], [EPS]],

        "IfStmt": [["if", "(", "Expr", ")", "Stmt", "ElsePart"]],
        "ElsePart": [["else", "Stmt"]],

        "ForStmt": [["for", "(", "ForInit", ";", "ExprOpt", ";", "ForStep", ")", "Stmt"]],
        "ForInit": [["DeclStmt"], ["SimpleStmt"], [EPS]],
        "ExprOpt": [["Expr"], [EPS]],
        "ForStep": [["SimpleStmt"], [EPS]],

        "SimpleStmt": [["id", "AssignOrCall"]],
        "AssignOrCall": [["AssignOp", "Expr"], ["(", "Args", ")"], [".", "id", "AssignOrCall"], ["[", "Expr", "]", "AssignOrCall"]],
        "AssignOp": [["="]],
        "ElseStat": [
            ["else", "Stmt"],  # 匹配 else { ... } 或 else if ...
            [EPS]              # 匹配没有 else 的情况
        ],

        "Expr": [["RelExpr", "ExprTail"]],
        "ExprTail": [
            ["LogOp", "RelExpr", "ExprTail"],
            [EPS]
        ],
        "LogOp": [["&&"], ["||"], ["&"], ["|"], ["~"], ["-"], ["!"]],
        
        "RelExpr": [["ArithExpr", "RelTail"]],
        "RelTail": [
            ["RelOp", "ArithExpr", "RelTail"],
            [EPS]
        ],
        
        "ArithExpr": [["Primary", "ArithTail"]],
        "ArithTail": [
            ["OP", "Primary", "ArithTail"], # 这里的 OP 对应 +, -
            ["*", "Primary", "ArithTail"],
            [EPS]
        ],
        
        "E_": [
            ["RelOp", "Term", "E_"], # 支持 pos != NULL
            ["OP", "Term", "E_"],    # 支持 pos - s
            [EPS]
        ],
        "RelOp": [
            ["!="], ["=="], [">"], ["<"], [">="], ["<="]
        ],

        "Term": [["id", "TermSuf"], ["int_lit"], ["float_lit"], ["string_lit"], ["char_lit"], ["(", "Expr", ")"], ["Unary", "Term"]],
        "TermTail": [
            ["OP", "Primary", "TermTail"], # 这里的 OP 对应 +, -
            [EPS]
        ],
        "Unary": [["*"], ["OP"]],

        # Term 后缀支持数组、成员访问以及函数调用
        "TermSuf": [["[", "Expr", "]", "TermSuf"], [".", "id", "TermSuf"], ["(", "Args", ")", "TermSuf"], [EPS]],

        "Params": [
            ["Type", "id", "NextParam"], # 这里的 Type 已经能处理 Node*
            ["void", "NextParam"], 
            [EPS]
        ],
        "ParamList": [["Param", "NextParam"]],
        # 2. 修改 NextParam，处理逗号
        "NextParam": [
            [",", "Param", "NextParam"],
            [EPS]
        ],
        
        # 3. 确保 Param 始终使用最通用的 Type
        "Param": [["Type", "Declarator"]],
        "Args": [["Expr", "NextArg"], [EPS]],
        "NextArg": [[",", "Expr", "NextArg"], [EPS]],
    }
    return Grammar("S", g)


def first_sets(g: Grammar) -> Dict[str, Set[str]]:
    nts = g.nonterminals
    ts = g.terminals
    first: Dict[str, Set[str]] = {A: set() for A in nts}

    def f_sym(x: str) -> Set[str]:
        if x == EPS:
            return {EPS}
        if x in ts and x not in nts:
            return {x}
        if x not in nts:
            return {x}
        return first[x]

    changed = True
    while changed:
        changed = False
        for A, alts in g.prods.items():
            for rhs in alts:
                acc: Set[str] = set()
                nullable = True
                for s in rhs:
                    fs = f_sym(s)
                    acc |= {t for t in fs if t != EPS}
                    if EPS not in fs:
                        nullable = False
                        break
                if nullable:
                    acc.add(EPS)
                if not acc.issubset(first[A]):
                    first[A] |= acc
                    changed = True
    return first


def first_seq(seq: List[str], g: Grammar, first: Dict[str, Set[str]]) -> Set[str]:
    ts = g.terminals
    nts = g.nonterminals

    def f_sym(x: str) -> Set[str]:
        if x == EPS:
            return {EPS}
        if x in ts and x not in nts:
            return {x}
        if x not in nts:
            return {x}
        return first[x]

    if not seq:
        return {EPS}
    out: Set[str] = set()
    for s in seq:
        fs = f_sym(s)
        out |= {t for t in fs if t != EPS}
        if EPS not in fs:
            return out
    out.add(EPS)
    return out


def follow_sets(g: Grammar, first: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    nts = g.nonterminals
    follow: Dict[str, Set[str]] = {A: set() for A in nts}
    follow[g.start].add("EOF")

    changed = True
    while changed:
        changed = False
        for A, alts in g.prods.items():
            for rhs in alts:
                for i, B in enumerate(rhs):
                    if B not in nts:
                        continue
                    beta = rhs[i + 1:]
                    fb = first_seq(beta, g, first)
                    add1 = {t for t in fb if t != EPS}
                    if not add1.issubset(follow[B]):
                        follow[B] |= add1
                        changed = True
                    if EPS in fb:
                        if not follow[A].issubset(follow[B]):
                            follow[B] |= follow[A]
                            changed = True
    return follow


def select_sets(g: Grammar, first: Dict[str, Set[str]], follow: Dict[str, Set[str]]):
    sel: Dict[Tuple[str, Tuple[str, ...]], Set[str]] = {}
    for A, alts in g.prods.items():
        for rhs in alts:
            frhs = first_seq(rhs, g, first)
            s = {t for t in frhs if t != EPS}
            if EPS in frhs:
                s |= follow.get(A, set())
            sel[(A, tuple(rhs))] = s
    return sel


def build_parse_table(select: Dict[Tuple[str, Tuple[str, ...]], Set[str]]):
    table: Dict[Tuple[str, str], List[str]] = {}
    conflicts: List[Tuple[str, str, List[str], List[str]]] = []
    for (A, rhs), terms in select.items():
        rhs_list = list(rhs)
        for a in terms:
            key = (A, a)
            if key in table and table[key] != rhs_list:
                conflicts.append((A, a, table[key], rhs_list))
            else:
                table[key] = rhs_list
    return table, conflicts


class LL1Parser:
    def __init__(self, grammar: Optional[Grammar] = None):
        self.grammar = grammar or c_grammar()

        self.first = first_sets(self.grammar)
        self.follow = follow_sets(self.grammar, self.first)
        self.select = select_sets(self.grammar, self.first, self.follow)

        self.table, self.conflicts = build_parse_table(self.select)
        self.terminals = self.grammar.terminals

        self.typedef_names: Set[str] = set()
        self._capture_typedef_alias = False

    def display(self, sym: str) -> str:
        return ALIAS.get(sym, sym)

    def symbolize(self, tok) -> str:
        tname = TYPES.get(tok.type, "UNKNOWN")
        attr = tok.attribute

        if tname == "PREPROCESSOR":
            return ""
        if tok.type == EOF or tname == "EOF":
            return "EOF"

        if tname == "KEYWORD":
            return attr
        if tname == "DELIMITER":
            if attr in ["if", "else", "while", "return", "goto", "break", "continue", "int", "char", "float", "double", "void", "struct", "typedef"]:
                return attr
            if attr in ["{", "}", "(", ")", ";", "[", "]", ","]:
                return attr
            return attr
        if tname == "OPERATOR":
            if attr == "*": 
                return "*"
            if attr in ["=", "."]:
                return attr
            if attr == ":":
                return ":"
            if attr in ["++", "--", "!=", "==", ">", "<", ">=", "<=", "&&", "||", "&", "|", "~", "-", "!"]:
                return attr  # 直接返回符号本身作为文法终结符
            return "OP"
        if tname == "IDENTIFIER":
            if attr in self.typedef_names:
                return "type_id"
            return "id"
        if tname in ["CONST_DECIMAL", "CONST_OCTAL", "CONST_HEX"]:
            return "int_lit"
        if tname == "CONST_FLOAT":
            return "float_lit"
        if tname == "CONST_CHAR":
            return "char_lit"
        if tname == "STRING_LITERAL":
            return "string_lit"

        return tname

    def analyze(self, tokens):
        filtered = [t for t in tokens if TYPES.get(t.type) != "PREPROCESSOR"]

        stack: List[str] = ["EOF", self.grammar.start]
        ptr = 0
        records = []
        step = 0

        def rest_input_str(i: int) -> str:
            if i >= len(filtered):
                return "#"
            attrs = [t.attribute for t in filtered[i:]]
            return " ".join(attrs) + " #"

        while stack:
            top = stack[-1]
            stack_str = " ".join(self.display(s) for s in stack).replace("EOF", "#")
            input_str = rest_input_str(ptr)

            if ptr < len(filtered):
                curr = filtered[ptr]
                lookahead = self.symbolize(curr)
                attr = curr.attribute
                line = curr.line
            else:
                lookahead = "EOF"
                attr = "EOF"
                line = -1

            if top in self.terminals or top == "EOF":

                if top == lookahead:
                    if top == "id" and self._capture_typedef_alias:
                        self.typedef_names.add(attr)
                        self._capture_typedef_alias = False
                    
                    # --- 核心修改点 ---
                    # 以前这里是 ""，现在我们填入 "匹配成功" 确保占位，使每一行都有 5 个元素
                    match_disp = f"匹配 {self.display(top)}"
                    records.append((step, stack_str, input_str, match_disp, f"“{attr}” 从栈顶弹出"))
                    # -----------------
                    
                    stack.pop()
                    ptr += 1
                    if top == "EOF":
                        break
                else:
                    # 报错时也建议补齐 5 列，防止 main.py 导出报错的数据记录
                    return records, False, f"匹配失败：期望 {self.display(top)} 但看到 {attr} (行 {line})"
            else:
                key = (top, lookahead)
                # “*” 既可能是指针/解引用（文法里用"*"），也可能是乘法（文法用 OP）。
                # 如果按字面"*"查不到表项，尝试把它视作 OP 再查一次。
                if key not in self.table:
                    return records, False, f"文法错误：无法用 {self.display(top)} 匹配 {attr} (行 {line})"

                prod = self.table[key]
                if top == "TypeAlias" and prod == ["id"]:
                    self._capture_typedef_alias = True

                prod_disp = " ".join(self.display(s) for s in prod)
                top_disp = self.display(top)
                prod_str = f"{top_disp} -> {prod_disp}" if prod != [EPS] else f"{top_disp} -> ε"
                action_str = f"{top_disp} 弹栈, {prod_disp} 逆序压栈" if prod != [EPS] else f"{top_disp} 弹栈 (空推导)"
                records.append((step, stack_str, input_str, prod_str, action_str))

                stack.pop()
                if prod != [EPS]:
                    for s in reversed(prod):
                        stack.append(s)

            step += 1

        return records, True, "语法分析成功！"

    def calc_sets(self):
        return {"first": self.first, "follow": self.follow, "select": self.select}

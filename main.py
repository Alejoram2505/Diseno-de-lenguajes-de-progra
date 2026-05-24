# ============================================================
# Laboratorio 01
# Conversión directa de una expresión regular a un AFD
# y simulación del AFD
#
# Soporta operadores:
#   |   unión
#   .   concatenación explícita
#   *   cerradura de Kleene
#   +   cerradura positiva
#   ?   opcional
#
# NO usa librerías de expresiones regulares.
# ============================================================

from dataclasses import dataclass, field
from collections import deque
from typing import Optional, Dict, Set, List, Tuple, FrozenSet


EPSILON = "ε"       # representa cadena vacía dentro de la expresión regular
ENDMARKER = "#"     # marcador final agregado automáticamente
CONCAT = "·"        # operador interno de concatenación explícita

# Token = (tipo, valor)
# Tipos principales:
# SYM     símbolo literal del alfabeto
# EPS     epsilon, cadena vacía
# OP      operador: |, *, +, ?, ·
# LPAREN  (
# RPAREN  )
Token = Tuple[str, str]


@dataclass
class Node:
    kind: str
    value: str = ""
    left: Optional["Node"] = None
    right: Optional["Node"] = None
    child: Optional["Node"] = None
    pos: Optional[int] = None
    nullable: bool = False
    firstpos: Set[int] = field(default_factory=set)
    lastpos: Set[int] = field(default_factory=set)


# ------------------------------------------------------------
# 1. Tokenización
# ------------------------------------------------------------

def tokenize(expr: str) -> List[Token]:
    """
    Convierte la expresión en tokens sin usar regex.

    Reglas:
    - |, *, +, ?, (, ) son operadores o paréntesis.
    - ε sin escapar representa la cadena vacía.
    - \\x representa el símbolo literal x, aunque x sea operador o ε.
      Ejemplo: \\| es el símbolo literal '|'.
               \\ε es el símbolo literal 'ε', no cadena vacía.
    - . no es operador de concatenación; se trata como símbolo literal.
    """
    tokens: List[Token] = []
    operators = {"|", "*", "+", "?", "(", ")"}
    i = 0

    while i < len(expr):
        c = expr[i]

        if c in {" ", "\t", "\n", "\r"}:
            i += 1
            continue

        if c == "\\":
            if i + 1 >= len(expr):
                raise ValueError("La expresión termina con una barra invertida '\\'.")
            escaped = expr[i + 1]
            if escaped == ENDMARKER:
                raise ValueError("No uses '#', ni siquiera escapado: el programa lo reserva como marcador final.")
            if escaped == CONCAT:
                raise ValueError(f"No uses '{CONCAT}': se usa internamente para concatenación.")
            tokens.append(("SYM", escaped))
            i += 2
            continue

        if c == EPSILON:
            tokens.append(("EPS", c))
        elif c in operators:
            if c == "(":
                tokens.append(("LPAREN", c))
            elif c == ")":
                tokens.append(("RPAREN", c))
            else:
                tokens.append(("OP", c))
        else:
            if c == ENDMARKER:
                raise ValueError("No uses '#': el programa lo agrega automáticamente.")
            if c == CONCAT:
                raise ValueError(f"No uses '{CONCAT}': se usa internamente para concatenación.")
            tokens.append(("SYM", c))

        i += 1

    if not tokens:
        raise ValueError("La expresión regular no puede estar vacía. Usa ε si quieres el lenguaje {ε}.")

    return tokens


def can_end_expression(tok: Token) -> bool:
    typ, val = tok
    return typ in {"SYM", "EPS", "RPAREN"} or (typ == "OP" and val in {"*", "+", "?"})


def can_start_expression(tok: Token) -> bool:
    typ, _ = tok
    return typ in {"SYM", "EPS", "LPAREN"}


def insert_concat(tokens: List[Token]) -> List[Token]:
    """Inserta el operador interno de concatenación donde corresponde."""
    result: List[Token] = []

    for i, tok in enumerate(tokens):
        if i > 0:
            prev = tokens[i - 1]
            if can_end_expression(prev) and can_start_expression(tok):
                result.append(("OP", CONCAT))
        result.append(tok)

    return result


# ------------------------------------------------------------
# 2. Validación y conversión a postfija
# ------------------------------------------------------------

def validate_tokens(tokens: List[Token]) -> None:
    """Valida errores básicos de sintaxis."""
    expecting_operand = True
    balance = 0

    for typ, val in tokens:
        if typ in {"SYM", "EPS"}:
            expecting_operand = False

        elif typ == "LPAREN":
            balance += 1
            expecting_operand = True

        elif typ == "RPAREN":
            balance -= 1
            if balance < 0:
                raise ValueError("Hay un paréntesis de cierre ')' sin apertura.")
            if expecting_operand:
                raise ValueError("Hay paréntesis vacíos o un operador antes de ')'.")
            expecting_operand = False

        elif typ == "OP":
            if val in {"*", "+", "?"}:
                if expecting_operand:
                    raise ValueError(f"El operador '{val}' no tiene operando a la izquierda.")
                expecting_operand = False

            elif val in {"|", CONCAT}:
                if expecting_operand:
                    raise ValueError(f"El operador '{val}' no tiene operando a la izquierda.")
                expecting_operand = True

            else:
                raise ValueError(f"Operador desconocido: {val}")

    if balance != 0:
        raise ValueError("Hay paréntesis sin cerrar.")

    if expecting_operand:
        raise ValueError("La expresión termina con un operador binario.")


def to_postfix(tokens: List[Token]) -> List[Token]:
    """Convierte de infija a postfija con Shunting Yard, sin usar regex."""
    validate_tokens(tokens)

    precedence = {"|": 1, CONCAT: 2}
    output: List[Token] = []
    stack: List[Token] = []

    for typ, val in tokens:
        if typ in {"SYM", "EPS"}:
            output.append((typ, val))

        elif typ == "LPAREN":
            stack.append((typ, val))

        elif typ == "RPAREN":
            while stack and stack[-1][0] != "LPAREN":
                output.append(stack.pop())
            if not stack:
                raise ValueError("Paréntesis desbalanceados.")
            stack.pop()

        elif typ == "OP":
            # *, + y ? son operadores postfijos de mayor precedencia.
            if val in {"*", "+", "?"}:
                output.append((typ, val))
            else:
                while (
                    stack
                    and stack[-1][0] == "OP"
                    and stack[-1][1] in precedence
                    and precedence[stack[-1][1]] >= precedence[val]
                ):
                    output.append(stack.pop())
                stack.append((typ, val))

    while stack:
        if stack[-1][0] == "LPAREN":
            raise ValueError("Paréntesis desbalanceados.")
        output.append(stack.pop())

    return output


# ------------------------------------------------------------
# 3. Construcción del árbol sintáctico
# ------------------------------------------------------------

def build_ast(postfix: List[Token]) -> Node:
    """Construye el árbol sintáctico desde la expresión postfija."""
    stack: List[Node] = []

    for typ, val in postfix:
        if typ == "SYM":
            stack.append(Node("leaf", val))

        elif typ == "EPS":
            stack.append(Node("epsilon", EPSILON))

        elif typ == "OP":
            if val in {"*", "+", "?"}:
                if not stack:
                    raise ValueError(f"Falta operando para '{val}'.")
                child = stack.pop()
                kind = {"*": "star", "+": "plus", "?": "optional"}[val]
                stack.append(Node(kind, val, child=child))

            elif val in {"|", CONCAT}:
                if len(stack) < 2:
                    raise ValueError(f"Faltan operandos para '{val}'.")
                right = stack.pop()
                left = stack.pop()
                kind = "union" if val == "|" else "concat"
                stack.append(Node(kind, val, left=left, right=right))

    if len(stack) != 1:
        raise ValueError("La expresión regular no es válida.")

    return stack[0]


# ------------------------------------------------------------
# 4. Posiciones, nullable, firstpos, lastpos, followpos
# ------------------------------------------------------------

def assign_positions(root: Node) -> Dict[int, str]:
    """Etiqueta las hojas con posiciones. Epsilon no recibe posición."""
    pos_to_symbol: Dict[int, str] = {}
    counter = 1

    def walk(n: Optional[Node]) -> None:
        nonlocal counter
        if n is None:
            return

        if n.kind == "leaf":
            n.pos = counter
            pos_to_symbol[counter] = n.value
            counter += 1
            return

        if n.kind == "epsilon":
            return

        if n.kind in {"union", "concat"}:
            walk(n.left)
            walk(n.right)
        else:
            walk(n.child)

    walk(root)
    return pos_to_symbol


def compute_functions(root: Node, pos_to_symbol: Dict[int, str]) -> Dict[int, Set[int]]:
    """Calcula nullable, firstpos, lastpos y followpos."""
    followpos: Dict[int, Set[int]] = {pos: set() for pos in pos_to_symbol}

    def post(n: Node) -> None:
        if n.kind == "leaf":
            n.nullable = False
            n.firstpos = {n.pos} if n.pos is not None else set()
            n.lastpos = {n.pos} if n.pos is not None else set()

        elif n.kind == "epsilon":
            n.nullable = True
            n.firstpos = set()
            n.lastpos = set()

        elif n.kind == "union":
            post(n.left)   
            post(n.right)  
            n.nullable = n.left.nullable or n.right.nullable  
            n.firstpos = n.left.firstpos | n.right.firstpos  
            n.lastpos = n.left.lastpos | n.right.lastpos      

        elif n.kind == "concat":
            post(n.left)  
            post(n.right)  

            n.nullable = n.left.nullable and n.right.nullable  

            if n.left.nullable: 
                n.firstpos = n.left.firstpos | n.right.firstpos  
            else:
                n.firstpos = set(n.left.firstpos) 

            if n.right.nullable:  
                n.lastpos = n.left.lastpos | n.right.lastpos 
            else:
                n.lastpos = set(n.right.lastpos)  

            for p in n.left.lastpos:  
                followpos[p].update(n.right.firstpos) 

        elif n.kind == "star":
            post(n.child)  
            n.nullable = True
            n.firstpos = set(n.child.firstpos)  
            n.lastpos = set(n.child.lastpos)   
          
            for p in n.child.lastpos:  
                followpos[p].update(n.child.firstpos)  

        elif n.kind == "plus":
            post(n.child)  
            n.nullable = n.child.nullable  
            n.firstpos = set(n.child.firstpos) 
            n.lastpos = set(n.child.lastpos)   
            for p in n.child.lastpos:  
                followpos[p].update(n.child.firstpos)  

        elif n.kind == "optional":
            post(n.child) 
            n.nullable = True
            n.firstpos = set(n.child.firstpos)  
            n.lastpos = set(n.child.lastpos)    

        else:
            raise ValueError(f"Nodo desconocido: {n.kind}")

    post(root)
    return followpos


# ------------------------------------------------------------
# 5. Construcción directa del AFD
# ------------------------------------------------------------

def build_direct_dfa(expr: str) -> dict:
    """Construye el AFD directo para una expresión regular."""
    tokens = tokenize(expr)
    tokens_with_concat = insert_concat(tokens)
    postfix = to_postfix(tokens_with_concat)
    user_root = build_ast(postfix)

    # Expresión aumentada: r#
    augmented_root = Node("concat", CONCAT, left=user_root, right=Node("leaf", ENDMARKER))

    pos_to_symbol = assign_positions(augmented_root)
    followpos = compute_functions(augmented_root, pos_to_symbol)

    hash_pos = None
    for pos, symbol in pos_to_symbol.items():
        if symbol == ENDMARKER:
            hash_pos = pos
            break

    if hash_pos is None:
        raise ValueError("No se encontró la posición de aceptación '#'.")

    alphabet = sorted({s for s in pos_to_symbol.values() if s != ENDMARKER})

    state_map: Dict[FrozenSet[int], str] = {}
    states: List[FrozenSet[int]] = []
    transitions: Dict[FrozenSet[int], Dict[str, FrozenSet[int]]] = {}

    def add_state(pos_set: Set[int]) -> FrozenSet[int]:
        frozen = frozenset(pos_set)
        if frozen not in state_map:
            state_map[frozen] = f"S{len(states)}"
            states.append(frozen)
        return frozen

    start = add_state(augmented_root.firstpos)
    queue = deque([start])
    visited = {start}

    while queue:
        state = queue.popleft()
        transitions[state] = {}

        for symbol in alphabet:
            dest: Set[int] = set()

            for p in state:
                if pos_to_symbol[p] == symbol:
                    dest.update(followpos[p])

            dest_frozen = frozenset(dest)
            transitions[state][symbol] = dest_frozen

            if dest_frozen and dest_frozen not in state_map:
                add_state(dest)

            if dest_frozen and dest_frozen not in visited:
                visited.add(dest_frozen)
                queue.append(dest_frozen)

    accept_states = {state for state in states if hash_pos in state}

    return {
        "expr": expr,
        "tokens": tokens,
        "tokens_with_concat": tokens_with_concat,
        "postfix": postfix,
        "root": augmented_root,
        "pos_to_symbol": pos_to_symbol,
        "followpos": followpos,
        "alphabet": alphabet,
        "states": states,
        "state_map": state_map,
        "transitions": transitions,
        "start": start,
        "accept_states": accept_states,
        "hash_pos": hash_pos,
    }


# ------------------------------------------------------------
# 6. Impresión de tablas
# ------------------------------------------------------------

def set_to_str(values) -> str:
    if not values:
        return "∅"
    return "{" + ",".join(str(x) for x in sorted(values)) + "}"


def print_tokens(dfa: dict) -> None:
    print("\nTokens reconocidos")
    print(dfa["tokens"])
    print("\nTokens con concatenación explícita interna")
    print(dfa["tokens_with_concat"])
    print("\nExpresión postfija interna")
    print(dfa["postfix"])


def print_positions(dfa: dict) -> None:
    print("\nHojas etiquetadas con posiciones")
    print("Pos | Símbolo")
    print("----+--------")
    for pos in sorted(dfa["pos_to_symbol"]):
        print(f"{pos:>3} | {dfa['pos_to_symbol'][pos]}")


def print_followpos(dfa: dict) -> None:
    print("\nTabla de siguientePosicion / followpos")
    print("Pos | Símbolo | followpos")
    print("----+---------+----------------")

    for pos in sorted(dfa["pos_to_symbol"]):
        symbol = dfa["pos_to_symbol"][pos]
        follow = set_to_str(dfa["followpos"][pos])
        print(f"{pos:>3} | {symbol:^7} | {follow}")


def print_transition_table(dfa: dict) -> None:
    alphabet = dfa["alphabet"]
    headers = ["Estado", "Posiciones"] + alphabet
    rows: List[List[str]] = []

    for state in dfa["states"]:
        name = dfa["state_map"][state]

        if state == dfa["start"]:
            name = "->" + name
        if state in dfa["accept_states"]:
            name = "*" + name

        row = [name, set_to_str(state)]

        for symbol in alphabet:
            dest = dfa["transitions"].get(state, {}).get(symbol, frozenset())
            row.append(dfa["state_map"].get(dest, "∅") if dest else "∅")

        rows.append(row)

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def format_line(values: List[str]) -> str:
        return " | ".join(values[i].ljust(widths[i]) for i in range(len(values)))

    print("\nTabla de transiciones del AFD")
    print(format_line(headers))
    print("-+-".join("-" * w for w in widths))

    for row in rows:
        print(format_line(row))

    print("\n-> estado inicial")
    print("*  estado de aceptación")


# ------------------------------------------------------------
# 7. Simulación del AFD
# ------------------------------------------------------------

def accepts(dfa: dict, text: str) -> bool:
    """Evalúa una cadena usando el AFD construido."""
    current = dfa["start"]

    for ch in text:
        if ch not in dfa["alphabet"]:
            return False

        current = dfa["transitions"].get(current, {}).get(ch, frozenset())

        if not current:
            return False

    return current in dfa["accept_states"]


# ------------------------------------------------------------
# 8. Programa principal
# ------------------------------------------------------------

def main() -> None:
    print("Conversión directa de una expresión regular a un AFD")
    print("Operadores permitidos:")
    print("  |  unión")
    print("  concatenación implícita, ejemplo: ab")
    print("  *  cerradura de Kleene")
    print("  +  cerradura positiva")
    print("  ?  opcional")
    print("  ε  cadena vacía")
    print("Usa \\ antes de un operador para tomarlo como símbolo literal. Ejemplo: a\\|b")
    print("El punto . se toma como símbolo literal, no como concatenación.")
    print("No uses # porque el programa lo agrega automáticamente.\n")

    expr = input("Ingresa la expresión regular: ")

    try:
        dfa = build_direct_dfa(expr)
    except ValueError as error:
        print(f"\nError: {error}")
        return

    print(f"\nExpresión aumentada: ({expr})#")
    print_tokens(dfa)
    print_positions(dfa)
    print_followpos(dfa)
    print_transition_table(dfa)

    print("\n(Para probar la cadena vacía ε, presiona Enter sin escribir nada.)")
    print("(Escribe 'salir' para terminar.)")

    while True:
        text = input("\nIngresa una cadena para evaluar: ")
        if text.strip().lower() == "salir":
            break
        if accepts(dfa, text):
            print("Resultado: la cadena PERTENECE al lenguaje.")
        else:
            print("Resultado: la cadena NO pertenece al lenguaje.")


if __name__ == "__main__":
    main()

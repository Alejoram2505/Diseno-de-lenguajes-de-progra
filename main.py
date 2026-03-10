# ============================================================
# Laboratorio 01
# Conversión directa de una expresión regular a un AFD
# y simulación del AFD
#
# Soporta operadores:
#   |   unión
#   .   concatenación explícita (el programa la agrega)
#   *   cerradura de Kleene
#   +   cerradura positiva
#   ?   opcional
#
# NO usa librerías de expresiones regulares.
# ============================================================

from collections import deque

# ------------------------------------------------------------
# Nodo del árbol sintáctico
# ------------------------------------------------------------
class Node:
    def __init__(self, value, left=None, right=None, position=None):
        self.value = value
        self.left = left
        self.right = right
        self.position = position

        self.nullable = False
        self.firstpos = set()
        self.lastpos = set()

    def __repr__(self):
        return f"Node({self.value})"


# ------------------------------------------------------------
# Utilidades para regex
# ------------------------------------------------------------
OPERATORS = {'|', '.', '*', '+', '?', '(', ')'}
UNARY_OPERATORS = {'*', '+', '?'}


def is_symbol(c):
    return c not in OPERATORS


def insert_concat(regex):
    """
    Inserta concatenación explícita '.' donde corresponde.
    Ejemplo:
        a(b|c)*   -> a.(b|c)*
        ab+c      -> a.b+.c
    """
    result = []
    for i in range(len(regex)):
        c1 = regex[i]
        result.append(c1)

        if i + 1 < len(regex):
            c2 = regex[i + 1]

            # Casos donde debe ir concatenación:
            # símbolo, ')', '*', '+', '?' seguido de símbolo o '('
            if ((is_symbol(c1) or c1 in {')', '*', '+', '?'}) and
                (is_symbol(c2) or c2 == '(')):
                result.append('.')

    return ''.join(result)


def to_postfix(regex):
    """
    Convierte de infix a postfix con Shunting Yard.
    Precedencia:
        *, +, ?  (más alta)
        .
        |
    """
    precedence = {
        '|': 1,
        '.': 2,
        '*': 3,
        '+': 3,
        '?': 3
    }

    output = []
    stack = []

    for c in regex:
        if is_symbol(c):
            output.append(c)
        elif c == '(':
            stack.append(c)
        elif c == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            if not stack:
                raise ValueError("Paréntesis desbalanceados.")
            stack.pop()  # quitar '('
        else:
            # operador
            while (stack and stack[-1] != '(' and
                   precedence.get(stack[-1], 0) >= precedence.get(c, 0)):
                output.append(stack.pop())
            stack.append(c)

    while stack:
        if stack[-1] in {'(', ')'}:
            raise ValueError("Paréntesis desbalanceados.")
        output.append(stack.pop())

    return ''.join(output)


# ------------------------------------------------------------
# Construcción del árbol sintáctico y followpos
# ------------------------------------------------------------
def build_syntax_tree(postfix):
    """
    Construye el árbol sintáctico a partir del postfix.
    También asigna posiciones a las hojas.
    """
    stack = []
    pos_counter = 1
    pos_to_symbol = {}

    for token in postfix:
        if is_symbol(token):
            node = Node(token, position=pos_counter)
            pos_to_symbol[pos_counter] = token
            pos_counter += 1
            stack.append(node)

        elif token in UNARY_OPERATORS:
            if not stack:
                raise ValueError(f"Operador unary '{token}' inválido.")
            child = stack.pop()
            node = Node(token, left=child)
            stack.append(node)

        elif token in {'|', '.'}:
            if len(stack) < 2:
                raise ValueError(f"Operador binary '{token}' inválido.")
            right = stack.pop()
            left = stack.pop()
            node = Node(token, left=left, right=right)
            stack.append(node)

        else:
            raise ValueError(f"Token desconocido: {token}")

    if len(stack) != 1:
        raise ValueError("La expresión regular es inválida.")

    root = stack[0]
    return root, pos_to_symbol


def compute_functions(node, followpos):
    """
    Calcula nullable, firstpos, lastpos y llena followpos.
    """
    if node is None:
        return

    # Hoja
    if node.left is None and node.right is None:
        node.nullable = False
        node.firstpos = {node.position}
        node.lastpos = {node.position}
        if node.position not in followpos:
            followpos[node.position] = set()
        return

    # Unario
    if node.value in UNARY_OPERATORS:
        compute_functions(node.left, followpos)
        child = node.left

        if node.value == '*':
            node.nullable = True
            node.firstpos = set(child.firstpos)
            node.lastpos = set(child.lastpos)

            for i in child.lastpos:
                followpos[i].update(child.firstpos)

        elif node.value == '+':
            # A+ = una o más repeticiones
            node.nullable = child.nullable
            node.firstpos = set(child.firstpos)
            node.lastpos = set(child.lastpos)

            for i in child.lastpos:
                followpos[i].update(child.firstpos)

        elif node.value == '?':
            # A? = epsilon o A
            node.nullable = True
            node.firstpos = set(child.firstpos)
            node.lastpos = set(child.lastpos)

        return

    # Binario
    compute_functions(node.left, followpos)
    compute_functions(node.right, followpos)

    if node.value == '|':
        node.nullable = node.left.nullable or node.right.nullable
        node.firstpos = node.left.firstpos | node.right.firstpos
        node.lastpos = node.left.lastpos | node.right.lastpos

    elif node.value == '.':
        node.nullable = node.left.nullable and node.right.nullable

        if node.left.nullable:
            node.firstpos = node.left.firstpos | node.right.firstpos
        else:
            node.firstpos = set(node.left.firstpos)

        if node.right.nullable:
            node.lastpos = node.left.lastpos | node.right.lastpos
        else:
            node.lastpos = set(node.right.lastpos)

        for i in node.left.lastpos:
            followpos[i].update(node.right.firstpos)


# ------------------------------------------------------------
# Construcción del AFD directo
# ------------------------------------------------------------
def build_dfa(root, followpos, pos_to_symbol):
    """
    Construye el AFD usando firstpos, followpos y el símbolo final '#'.
    """
    alphabet = sorted(set(sym for sym in pos_to_symbol.values() if sym != '#'))

    # Encontrar la posición del símbolo final '#'
    hash_pos = None
    for pos, sym in pos_to_symbol.items():
        if sym == '#':
            hash_pos = pos
            break

    if hash_pos is None:
        raise ValueError("No se encontró el símbolo final '#'.")

    start_state = frozenset(root.firstpos)

    states = []
    state_ids = {}
    transitions = {}
    accepting_states = set()

    queue = deque([start_state])
    state_ids[start_state] = "S0"
    states.append(start_state)

    while queue:
        current = queue.popleft()
        current_name = state_ids[current]
        transitions[current_name] = {}

        if hash_pos in current:
            accepting_states.add(current_name)

        for a in alphabet:
            u = set()

            for p in current:
                if pos_to_symbol[p] == a:
                    u.update(followpos[p])

            if u:
                u = frozenset(u)
                if u not in state_ids:
                    state_ids[u] = f"S{len(state_ids)}"
                    states.append(u)
                    queue.append(u)
                transitions[current_name][a] = state_ids[u]

    return {
        "alphabet": alphabet,
        "states": states,
        "state_ids": state_ids,
        "transitions": transitions,
        "start_state": "S0",
        "accepting_states": accepting_states,
        "hash_pos": hash_pos
    }


# ------------------------------------------------------------
# Simulación del AFD
# ------------------------------------------------------------
def simulate_dfa(dfa, string):
    current = dfa["start_state"]

    for ch in string:
        if ch not in dfa["alphabet"]:
            return False
        if ch not in dfa["transitions"].get(current, {}):
            return False
        current = dfa["transitions"][current][ch]

    return current in dfa["accepting_states"]


# ------------------------------------------------------------
# Impresión de resultados
# ------------------------------------------------------------
def print_followpos(followpos, pos_to_symbol):
    print("\nTabla followpos:")
    print("Posición | Símbolo | followpos")
    print("--------------------------------")
    for pos in sorted(pos_to_symbol.keys()):
        if pos_to_symbol[pos] == '#':
            continue
        fp = sorted(followpos[pos])
        print(f"{pos:^8} | {pos_to_symbol[pos]:^7} | {fp}")


def print_positions(pos_to_symbol):
    print("\nPosiciones de hojas:")
    print("Posición | Símbolo")
    print("------------------")
    for pos in sorted(pos_to_symbol.keys()):
        print(f"{pos:^8} | {pos_to_symbol[pos]:^7}")


def print_syntax_info(root):
    print("\nFunciones de la raíz:")
    print(f"nullable : {root.nullable}")
    print(f"firstpos : {sorted(root.firstpos)}")
    print(f"lastpos  : {sorted(root.lastpos)}")


def print_dfa_table(dfa):
    alphabet = dfa["alphabet"]
    transitions = dfa["transitions"]
    accepting = dfa["accepting_states"]

    print("\nTabla de transición del AFD:")
    header = ["Estado"] + alphabet
    print(" | ".join(f"{h:^10}" for h in header))
    print("-" * (13 * len(header)))

    # Ordenar estados por número
    ordered_states = sorted(
        transitions.keys(),
        key=lambda s: int(s[1:])
    )

    for state in ordered_states:
        label = state
        if state == dfa["start_state"]:
            label += "(I)"
        if state in accepting:
            label += "(F)"

        row = [f"{label:^10}"]
        for sym in alphabet:
            row.append(f"{transitions[state].get(sym, '-'):^10}")
        print(" | ".join(row))

    print("\nConjuntos que representa cada estado:")
    inv = {v: k for k, v in dfa["state_ids"].items()}
    for state_name in sorted(inv.keys(), key=lambda s: int(s[1:])):
        print(f"{state_name} = {sorted(inv[state_name])}")


# ------------------------------------------------------------
# Función principal de construcción
# ------------------------------------------------------------
def regex_to_dfa(regex):
    """
    Construye el AFD directo a partir de la regex.
    Internamente agrega:
        (regex).#
    """
    if not regex:
        raise ValueError("La expresión regular no puede estar vacía.")

    # Agregamos concatenación explícita primero
    regex = insert_concat(regex)

    # Agregamos símbolo terminal #
    augmented = f"({regex}).#"

    postfix = to_postfix(augmented)
    root, pos_to_symbol = build_syntax_tree(postfix)

    followpos = {pos: set() for pos in pos_to_symbol}
    compute_functions(root, followpos)

    dfa = build_dfa(root, followpos, pos_to_symbol)

    return {
        "original_regex": regex,
        "augmented_regex": augmented,
        "postfix": postfix,
        "root": root,
        "pos_to_symbol": pos_to_symbol,
        "followpos": followpos,
        "dfa": dfa
    }


# ------------------------------------------------------------
# Interfaz de consola
# ------------------------------------------------------------
def main():
    print("==============================================")
    print(" Conversión directa de ER a AFD y simulación ")
    print("==============================================")
    print("Operadores soportados: |  *  +  ?  y concatenación implícita")
    print("Ejemplos válidos:")
    print("  a(b|c)*")
    print("  (ab)+c")
    print("  a?bc")
    print()

    while True:
        try:
            regex = input("Ingrese una expresión regular (o 'salir'): ").strip()
            if regex.lower() == "salir":
                print("Programa finalizado.")
                break

            result = regex_to_dfa(regex)

            print("\nExpresión con concatenación explícita:")
            print(result["original_regex"])

            print("\nExpresión aumentada:")
            print(result["augmented_regex"])

            print("\nPostfix:")
            print(result["postfix"])

            print_positions(result["pos_to_symbol"])
            print_syntax_info(result["root"])
            print_followpos(result["followpos"], result["pos_to_symbol"])
            print_dfa_table(result["dfa"])

            while True:
                cadena = input("\nIngrese una cadena para validar (o 'nueva' para otra regex): ").strip()
                if cadena.lower() == "nueva":
                    print()
                    break

                accepted = simulate_dfa(result["dfa"], cadena)
                if accepted:
                    print("Resultado: CADENA ACEPTADA")
                else:
                    print("Resultado: CADENA RECHAZADA")

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
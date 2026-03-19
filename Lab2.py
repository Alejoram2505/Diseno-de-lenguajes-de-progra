# ============================================================
# Laboratorio 01 / Extensión
# Conversión directa de una expresión regular a un AFD,
# minimización del AFD y simulación del autómata minimizado.
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
            stack.pop()
        else:
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
                raise ValueError(f"Operador unario '{token}' inválido.")
            child = stack.pop()
            node = Node(token, left=child)
            stack.append(node)

        elif token in {'|', '.'}:
            if len(stack) < 2:
                raise ValueError(f"Operador binario '{token}' inválido.")
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
# Minimización del AFD
# ------------------------------------------------------------
def count_transitions(dfa):
    return sum(len(trans) for trans in dfa["transitions"].values())



def complete_dfa(dfa):
    """
    Completa el AFD agregando un estado pozo si hace falta.
    Esto simplifica la minimización por particiones.
    """
    alphabet = list(dfa["alphabet"])
    transitions = {state: dict(trans) for state, trans in dfa["transitions"].items()}
    accepting = set(dfa["accepting_states"])

    all_states = set(transitions.keys()) | {dfa["start_state"]}
    for trans in dfa["transitions"].values():
        all_states.update(trans.values())

    sink_needed = False
    for state in list(all_states):
        transitions.setdefault(state, {})
        for symbol in alphabet:
            if symbol not in transitions[state]:
                sink_needed = True

    sink_name = None
    if sink_needed:
        base = "POZO"
        sink_name = base
        counter = 0
        while sink_name in all_states:
            counter += 1
            sink_name = f"{base}_{counter}"

        transitions[sink_name] = {symbol: sink_name for symbol in alphabet}
        all_states.add(sink_name)

        for state in list(all_states):
            transitions.setdefault(state, {})
            for symbol in alphabet:
                if symbol not in transitions[state]:
                    transitions[state][symbol] = sink_name

    return {
        "alphabet": alphabet,
        "states": sorted(all_states),
        "transitions": transitions,
        "start_state": dfa["start_state"],
        "accepting_states": accepting,
        "sink_state": sink_name
    }



def reachable_states(dfa):
    visited = set()
    queue = deque([dfa["start_state"]])

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        for nxt in dfa["transitions"].get(current, {}).values():
            if nxt not in visited:
                queue.append(nxt)

    return visited



def minimize_dfa(dfa):
    """
    Minimiza un AFD mediante refinamiento de particiones.
    1. Completa el AFD con estado pozo si es necesario.
    2. Elimina estados inaccesibles.
    3. Refina particiones entre finales/no finales.
    4. Construye el AFD minimizado.
    """
    completed = complete_dfa(dfa)
    reachable = reachable_states(completed)

    alphabet = completed["alphabet"]
    transitions = {
        state: {sym: dst for sym, dst in completed["transitions"][state].items()}
        for state in reachable
    }
    accepting = completed["accepting_states"] & reachable
    start_state = completed["start_state"]

    non_accepting = reachable - accepting
    partitions = []
    if accepting:
        partitions.append(set(accepting))
    if non_accepting:
        partitions.append(set(non_accepting))

    if not partitions:
        raise ValueError("No se pudo construir la partición inicial.")

    changed = True
    while changed:
        changed = False
        new_partitions = []

        for group in partitions:
            signatures = {}
            for state in group:
                signature = []
                for symbol in alphabet:
                    dest = transitions[state][symbol]
                    dest_group_index = next(
                        i for i, part in enumerate(partitions) if dest in part
                    )
                    signature.append(dest_group_index)
                signature = tuple(signature)
                signatures.setdefault(signature, set()).add(state)

            if len(signatures) == 1:
                new_partitions.append(group)
            else:
                changed = True
                new_partitions.extend(signatures.values())

        partitions = new_partitions

    original_reachable = reachable_states({
        "alphabet": dfa["alphabet"],
        "transitions": dfa["transitions"],
        "start_state": dfa["start_state"]
    })

    sink_state = completed.get("sink_state")

    ordered_partitions = []
    start_partition = next(part for part in partitions if start_state in part)
    ordered_partitions.append(start_partition)
    for part in partitions:
        if part is not start_partition:
            ordered_partitions.append(part)

    visible_partitions = []
    hidden_sink_partition = None
    for part in ordered_partitions:
        if part & original_reachable:
            visible_partitions.append(part)
        elif sink_state is not None and sink_state in part:
            hidden_sink_partition = part

    state_name_of_partition = {}
    for index, part in enumerate(visible_partitions):
        state_name_of_partition[frozenset(part)] = f"M{index}"

    state_to_min = {}
    for part in visible_partitions:
        min_name = state_name_of_partition[frozenset(part)]
        for state in part:
            state_to_min[state] = min_name

    if hidden_sink_partition is not None:
        for state in hidden_sink_partition:
            state_to_min[state] = None

    min_transitions = {}
    min_accepting = set()
    min_states = []

    for part in visible_partitions:
        rep = next(iter(part))
        min_name = state_to_min[rep]
        min_states.append(min_name)
        min_transitions[min_name] = {}

        if part & accepting:
            min_accepting.add(min_name)

        for symbol in alphabet:
            dest = transitions[rep][symbol]
            dest_min = state_to_min[dest]
            if dest_min is not None:
                min_transitions[min_name][symbol] = dest_min

    return {
        "alphabet": alphabet,
        "states": min_states,
        "transitions": min_transitions,
        "start_state": state_to_min[start_state],
        "accepting_states": min_accepting,
        "partitions": [sorted(part) for part in visible_partitions],
        "state_map": state_to_min,
        "original_completed": completed
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



def print_dfa_table(dfa, title="Tabla de transición del AFD"):
    alphabet = dfa["alphabet"]
    transitions = dfa["transitions"]
    accepting = dfa["accepting_states"]

    print(f"\n{title}:")
    header = ["Estado"] + alphabet
    print(" | ".join(f"{h:^12}" for h in header))
    print("-" * (15 * len(header)))

    ordered_states = sorted(transitions.keys(), key=lambda s: (s[0], int(''.join(filter(str.isdigit, s)) or 0), s))

    for state in ordered_states:
        label = state
        if state == dfa["start_state"]:
            label += "(I)"
        if state in accepting:
            label += "(F)"

        row = [f"{label:^12}"]
        for sym in alphabet:
            row.append(f"{transitions[state].get(sym, '-'):^12}")
        print(" | ".join(row))



def print_direct_state_sets(dfa):
    print("\nConjuntos que representa cada estado del AFD directo:")
    inv = {v: k for k, v in dfa["state_ids"].items()}
    for state_name in sorted(inv.keys(), key=lambda s: int(s[1:])):
        print(f"{state_name} = {sorted(inv[state_name])}")



def print_minimized_partitions(min_dfa):
    print("\nParticiones / equivalencias del AFD minimizado:")
    for index, part in enumerate(min_dfa["partitions"]):
        print(f"M{index} = {part}")



def print_comparison(dfa_directo, dfa_minimizado):
    estados_directo = len(dfa_directo["transitions"])
    trans_directo = count_transitions(dfa_directo)

    estados_min = len(dfa_minimizado["transitions"])
    trans_min = count_transitions(dfa_minimizado)

    print("\nComparación de autómatas:")
    print("--------------------------------------------------")
    print(f"AFD directo     -> estados: {estados_directo}, transiciones: {trans_directo}")
    print(f"AFD minimizado  -> estados: {estados_min}, transiciones: {trans_min}")
    print("--------------------------------------------------")

    if estados_directo == estados_min and trans_directo == trans_min:
        print("Resultado: el AFD obtenido por método directo ya era mínimo.")
    else:
        print("Resultado: la minimización redujo el autómata.")


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

    regex = insert_concat(regex)
    augmented = f"({regex}).#"

    postfix = to_postfix(augmented)
    root, pos_to_symbol = build_syntax_tree(postfix)

    followpos = {pos: set() for pos in pos_to_symbol}
    compute_functions(root, followpos)

    dfa = build_dfa(root, followpos, pos_to_symbol)
    minimized_dfa = minimize_dfa(dfa)

    return {
        "original_regex": regex,
        "augmented_regex": augmented,
        "postfix": postfix,
        "root": root,
        "pos_to_symbol": pos_to_symbol,
        "followpos": followpos,
        "dfa": dfa,
        "minimized_dfa": minimized_dfa
    }


# ------------------------------------------------------------
# Interfaz de consola
# ------------------------------------------------------------
def main():
    print("============================================================")
    print(" Conversión directa de ER a AFD, minimización y simulación ")
    print("============================================================")
    print("Operadores soportados: |  *  +  ?  y concatenación implícita")
    print("Ejemplos válidos:")
    print("  a(b|c)*")
    print("  (ab)+c")
    print("  a?bc")
    print()
    print("Sugerencias para la demostración:")
    print("  - Una ER que ya produzca un AFD mínimo")
    print("  - Otra ER donde la minimización sí reduzca estados")
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
            print_dfa_table(result["dfa"], "Tabla de transición del AFD directo")
            print_direct_state_sets(result["dfa"])

            print_dfa_table(result["minimized_dfa"], "Tabla de transición del AFD minimizado")
            print_minimized_partitions(result["minimized_dfa"])
            print_comparison(result["dfa"], result["minimized_dfa"])

            while True:
                cadena = input("\nIngrese una cadena para validar con el AFD minimizado (o 'nueva' para otra regex): ").strip()
                if cadena.lower() == "nueva":
                    print()
                    break

                accepted = simulate_dfa(result["minimized_dfa"], cadena)
                if accepted:
                    print("Resultado: CADENA ACEPTADA por el AFD minimizado")
                else:
                    print("Resultado: CADENA RECHAZADA por el AFD minimizado")

        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()

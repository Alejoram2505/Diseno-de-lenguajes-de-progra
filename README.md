# Conversión Directa de una Expresión Regular a un AFD y Simulación del AFD

**Laboratorio 01**
**Integrantes:** Diego Ramírez, Nina Nájera, Eliazar Canastuj   

---

## Descripción

Este proyecto implementa el **método directo para convertir una expresión regular en un Autómata Finito Determinista (AFD)** y permite simular el funcionamiento del autómata para determinar si una cadena pertenece o no al lenguaje definido por la expresión regular.

El programa:

- Recibe una **expresión regular**
- Construye el **árbol sintáctico**
- Calcula:
  - `nullable`
  - `firstpos`
  - `lastpos`
  - `followpos`
- Genera la **tabla de transición del AFD**
- Permite **validar cadenas de entrada**

---

## Características

El programa soporta los siguientes operadores de expresiones regulares:

| Operador | Significado |
|--------|--------|
| `|` | Unión |
| `*` | Cerradura de Kleene |
| `+` | Cerradura positiva |
| `?` | Operador opcional |
| concatenación | Implícita |

Ejemplo de expresión válida: a(b|c)*

Cadena: abcb
Resultado: CADENA ACEPTADA

Cadena: ba
Resultado: CADENA RECHAZADA
# Conversión Directa de una Expresión Regular a un AFD, Simulación del AFD y Minimización de un AFD.

**Laboratorio 01**
**Integrantes:** Diego Ramírez, Nina Nájera, Eliazar Canastuj   

---

## Descripción

Este programa implementa el **método directo** para convertir una
expresión regular en un **Autómata Finito Determinista (AFD)**, y
posteriormente aplica un **algoritmo de minimización** para obtener un
AFD equivalente con el menor número de estados posible.

También permite simular cadenas para verificar si pertenecen al lenguaje
definido por la expresión regular.

------------------------------------------------------------------------

## Características

-   Construcción de AFD mediante el método directo (followpos)
-   Soporte de operadores:
    -   Unión `|`
    -   Concatenación implícita
    -   Cerradura de Kleene `*`
    -   Cerradura positiva `+`
    -   Opcional `?`
-   Generación de:
    -   Expresión con concatenación explícita
    -   Expresión postfix
    -   Tabla followpos
    -   Tabla de transición del AFD directo
-   Minimización del AFD
-   Generación de la tabla del AFD minimizado
-   Comparación entre:
    -   Número de estados
    -   Número de transiciones
-   Simulación de cadenas

------------------------------------------------------------------------

## Uso del programa

1.  Ejecutar el archivo:

``` bash
python Lab2.py
```

2.  Ingresar una expresión regular válida.

3.  El programa mostrará:

    -   Conversión a postfix
    -   Tabla followpos
    -   AFD directo
    -   AFD minimizado
    -   Comparación

4.  Ingresar cadenas para probar si son aceptadas o rechazadas.

------------------------------------------------------------------------

## Ejemplos recomendados

### Caso mínimo (no cambia al minimizar)

    (a|b)*abb

### Caso no mínimo (sí se reduce)

    (ab)?(a|b)*

------------------------------------------------------------------------

## Salida esperada

-   Tabla de transición del AFD directo
-   Tabla de transición del AFD minimizado
-   Número de estados antes y después
-   Resultado de aceptación de cadenas

------------------------------------------------------------------------

## Estructura general del algoritmo

1.  Convertir la expresión a postfix
2.  Construir el árbol sintáctico
3.  Calcular:
    -   nullable
    -   firstpos
    -   lastpos
    -   followpos
4.  Construir el AFD directo
5.  Minimizar el AFD (refinamiento de particiones)
6.  Simular cadenas


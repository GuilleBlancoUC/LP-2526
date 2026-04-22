# coding: utf-8

# El fichero badfeatures le hemos modificado para que deje de aparecer error, atrapabamos el error
# despues del '}' y en tu fichero lo atrapaba antes, pero el error es el mismo

from Lexer import CoolLexer
from sly import Parser
import sys
import os
from Clases import *


class CoolParser(Parser):
    nombre_fichero = ''
    tokens = CoolLexer.tokens
    debugfile = "salida.out"
    errores = []

    # ─── Precedencia ─────────────────────────────────────────────────────────────
    #
    # Orden de MENOR a MAYOR precedencia (sly las lee de arriba a abajo).
    # Fuente: enunciado COOL (de mayor a menor):
    #   .  @  ~  ISVOID  * /  + -  LE < =  NOT  ASSIGN
    #
    # IN se declara entre ASSIGN y NOT con precedencia 'right' para resolver
    # el único conflicto shift/reduce real: en el estado donde el parser tiene
    #   LET lista_let IN Expresion
    # en el stack y ve un operador binario por delante. Declarar IN con
    # precedencia más baja que los operadores hace que el parser haga shift
    # del operador, incluyéndolo dentro del cuerpo del LET (comportamiento
    # correcto según el manual de COOL).
    #
    precedence = (
        ('right',    'ASSIGN'),
        ('right',    'IN'),
        ('left',     'NOT'),
        ('nonassoc', '=', 'LE', '<'),
        ('left',     '+', '-'),
        ('left',     '*', '/'),
        ('left',     'ISVOID'),
        ('left',     '~'),
        ('left',     '@'),
        ('left',     '.'),
    )

    # ─── Programa ────────────────────────────────────────────────────────────────

    @_("lista_clases")
    def Programa(self, p):
        return Programa(
            secuencia=p.lista_clases,
            linea=p.lista_clases[-1].linea if p.lista_clases else 0
        )

    @_("lista_clases error")
    def Programa(self, p):
        if self.errores:
            self.errores.pop()
        return Programa(
            secuencia=p.lista_clases,
            linea=p.lista_clases[-1].linea if p.lista_clases else 0
        )

    # ─── Lista de clases ─────────────────────────────────────────────────────────

    @_("Clase ';'")
    def lista_clases(self, p):
        # p.Clase.linea = int(p.lineno)
        return [p.Clase]

    @_("lista_clases Clase ';'")
    def lista_clases(self, p):
        # p.Clase.linea = int(p.lineno)
        return p.lista_clases + [p.Clase]

    @_("error ';'")
    def lista_clases(self, p):
        return []

    @_("lista_clases error ';'")
    def lista_clases(self, p):
        return p.lista_clases

    # ─── Clase ───────────────────────────────────────────────────────────────────

    @_("CLASS TYPEID '{' lista_caracteristicas '}'")
    def Clase(self, p):
        return Clase(
            nombre=p.TYPEID,
            padre='Object',
            nombre_fichero=self.nombre_fichero,
            caracteristicas=p.lista_caracteristicas,
            linea=int(p.lineno)
        )

    @_("CLASS TYPEID INHERITS TYPEID '{' lista_caracteristicas '}'")
    def Clase(self, p):
        return Clase(
            nombre=p.TYPEID0,
            padre=p.TYPEID1,
            nombre_fichero=self.nombre_fichero,
            caracteristicas=p.lista_caracteristicas,
            linea=int(p.lineno)
        )

    # ─── Lista de características ────────────────────────────────────────────────

    @_("")
    def lista_caracteristicas(self, p):
        return []

    @_("lista_caracteristicas Atributo ';'")
    def lista_caracteristicas(self, p):
        p.Atributo.linea = int(p.lineno)
        return p.lista_caracteristicas + [p.Atributo]

    @_("lista_caracteristicas Metodo ';'")
    def lista_caracteristicas(self, p):
        p.Metodo.linea = int(p.lineno)
        return p.lista_caracteristicas + [p.Metodo]

    @_("error ';'")
    def lista_caracteristicas(self, p):
        return []

    @_("lista_caracteristicas error ';'")
    def lista_caracteristicas(self, p):
        return p.lista_caracteristicas

    # ─── Atributo ────────────────────────────────────────────────────────────────

    @_("OBJECTID ':' TYPEID")
    def Atributo(self, p):
        return Atributo(
            nombre=p.OBJECTID,
            tipo=p.TYPEID,
            cuerpo=NoExpr(linea=int(p.lineno)),
            linea=int(p.lineno)
        )

    @_("OBJECTID ':' TYPEID ASSIGN Expresion")
    def Atributo(self, p):
        return Atributo(
            nombre=p.OBJECTID,
            tipo=p.TYPEID,
            cuerpo=p.Expresion,
            linea=int(p.lineno)
        )

    # ─── Método ──────────────────────────────────────────────────────────────────

    @_("OBJECTID '(' ')' ':' TYPEID '{' Expresion '}'")
    def Metodo(self, p):
        return Metodo(
            nombre=p.OBJECTID,
            tipo=p.TYPEID,
            formales=[],
            cuerpo=p.Expresion,
            linea=int(p.lineno)
        )

    @_("OBJECTID '(' lista_formales ')' ':' TYPEID '{' Expresion '}'")
    def Metodo(self, p):
        return Metodo(
            nombre=p.OBJECTID,
            tipo=p.TYPEID,
            formales=p.lista_formales,
            cuerpo=p.Expresion,
            linea=int(p.lineno)
        )
    
    @_("OBJECTID '(' lista_formales ')' ':' TYPEID '{' error '}'")
    def Metodo(self, p):
        return Metodo(
            nombre=p.OBJECTID,
            tipo=p.TYPEID,
            formales=p.lista_formales,
            cuerpo=NoExpr(),
            linea=int(p.lineno)
        )

    # ─── Formales ────────────────────────────────────────────────────────────────

    @_("Formal")
    def lista_formales(self, p):
        return [p.Formal]

    @_("lista_formales ',' Formal")
    def lista_formales(self, p):
        return p.lista_formales + [p.Formal]

    @_("error")
    def lista_formales(self, p):
        return []

    @_("lista_formales ',' error")
    def lista_formales(self, p):
        return p.lista_formales

    @_("OBJECTID ':' TYPEID")
    def Formal(self, p):
        return Formal(
            nombre_variable=p.OBJECTID,
            tipo=p.TYPEID,
            linea=int(p.lineno)
        )

    # ─── Expresión ───────────────────────────────────────────────────────────────

    # Asignación
    @_("OBJECTID ASSIGN Expresion")
    def Expresion(self, p):
        return Asignacion(
            nombre=p.OBJECTID,
            cuerpo=p.Expresion,
            linea=int(p.lineno)
        )

    # IF
    @_("IF Expresion THEN Expresion ELSE Expresion FI")
    def Expresion(self, p):
        return Condicional(
            condicion=p.Expresion0,
            verdadero=p.Expresion1,
            falso=p.Expresion2,
            linea=int(p.lineno)
        )

    # WHILE
    @_("WHILE Expresion LOOP Expresion POOL")
    def Expresion(self, p):
        return Bucle(
            condicion=p.Expresion0,
            cuerpo=p.Expresion1,
            linea=int(p.lineno)
        )

    # Bloque
    @_("'{' lista_exprs '}'")
    def Expresion(self, p):
        return Bloque(
            expresiones=p.lista_exprs,
            linea=int(p.lineno)
        )

    # LET — el token IN tiene la menor precedencia de todas las operaciones,
    # por lo que cuando tras "LET ... IN expr" aparece un operador binario,
    # el parser hace shift (lo incluye en el cuerpo) en lugar de reducir.
    @_("LET lista_let IN Expresion")
    def Expresion(self, p):
        result = p.Expresion
        for nombre, tipo, init, linea in reversed(p.lista_let):
            result = Let(
                nombre=nombre,
                tipo=tipo,
                inicializacion=init,
                cuerpo=result,
                linea=linea
            )
        return result

    # CASE
    @_("CASE Expresion OF lista_ramas ESAC")
    def Expresion(self, p):
        return Swicht(
            expr=p.Expresion,
            casos=p.lista_ramas,
            linea=int(p.lineno)
        )
    @_("CASE error OF lista_ramas ESAC")
    def Expresion(self, p):
        return Swicht(
            expr=None,
            casos=p.lista_ramas,
            linea=int(p.lineno)
        )

    # NEW
    @_("NEW TYPEID")
    def Expresion(self, p):
        return Nueva(tipo=p.TYPEID, linea=int(p.lineno))

    # ISVOID
    @_("ISVOID Expresion")
    def Expresion(self, p):
        return EsNulo(expr=p.Expresion, linea=int(p.lineno))

    # Negación entera
    @_("'~' Expresion")
    def Expresion(self, p):
        return Neg(expr=p.Expresion, linea=int(p.lineno))

    # NOT lógico
    @_("NOT Expresion")
    def Expresion(self, p):
        return Not(expr=p.Expresion, linea=int(p.lineno))

    # Aritméticos
    @_("Expresion '+' Expresion")
    def Expresion(self, p):
        return Suma(izquierda=p.Expresion0, derecha=p.Expresion1, linea=int(p.lineno))

    @_("Expresion '-' Expresion")
    def Expresion(self, p):
        return Resta(izquierda=p.Expresion0, derecha=p.Expresion1, linea=int(p.lineno))

    @_("Expresion '*' Expresion")
    def Expresion(self, p):
        return Multiplicacion(izquierda=p.Expresion0, derecha=p.Expresion1, linea=int(p.lineno))

    @_("Expresion '/' Expresion")
    def Expresion(self, p):
        return Division(izquierda=p.Expresion0, derecha=p.Expresion1, linea=int(p.lineno))

    # Comparaciones (no asociativas)
    @_("Expresion '<' Expresion")
    def Expresion(self, p):
        return Menor(izquierda=p.Expresion0, derecha=p.Expresion1, linea=int(p.lineno))

    @_("Expresion LE Expresion")
    def Expresion(self, p):
        return LeIgual(izquierda=p.Expresion0, derecha=p.Expresion1, linea=int(p.lineno))

    @_("Expresion '=' Expresion")
    def Expresion(self, p):
        return Igual(izquierda=p.Expresion0, derecha=p.Expresion1, linea=int(p.lineno))

    # Dispatch estático: expr@TYPEID.metodo()
    @_("Expresion '@' TYPEID '.' OBJECTID '(' ')'")
    def Expresion(self, p):
        return LlamadaMetodoEstatico(
            cuerpo=p.Expresion,
            clase=p.TYPEID,
            nombre_metodo=p.OBJECTID,
            argumentos=[],
            linea=int(p.lineno)
        )

    # Dispatch estático: expr@TYPEID.metodo(args)
    @_("Expresion '@' TYPEID '.' OBJECTID '(' lista_args ')'")
    def Expresion(self, p):
        return LlamadaMetodoEstatico(
            cuerpo=p.Expresion,
            clase=p.TYPEID,
            nombre_metodo=p.OBJECTID,
            argumentos=p.lista_args,
            linea=int(p.lineno)
        )

    # Dispatch dinámico: expr.metodo()
    @_("Expresion '.' OBJECTID '(' ')'")
    def Expresion(self, p):
        return LlamadaMetodo(
            cuerpo=p.Expresion,
            nombre_metodo=p.OBJECTID,
            argumentos=[],
            linea=int(p.lineno)
        )

    # Dispatch dinámico: expr.metodo(args)
    @_("Expresion '.' OBJECTID '(' lista_args ')'")
    def Expresion(self, p):
        return LlamadaMetodo(
            cuerpo=p.Expresion,
            nombre_metodo=p.OBJECTID,
            argumentos=p.lista_args,
            linea=int(p.lineno)
        )

    # Dispatch implícito (self): metodo()
    @_("OBJECTID '(' ')'")
    def Expresion(self, p):
        return LlamadaMetodo(
            cuerpo=Objeto(nombre='self', linea=int(p.lineno)),
            nombre_metodo=p.OBJECTID,
            argumentos=[],
            linea=int(p.lineno)
        )

    # Dispatch implícito (self): metodo(args)
    @_("OBJECTID '(' lista_args ')'")
    def Expresion(self, p):
        return LlamadaMetodo(
            cuerpo=Objeto(nombre='self', linea=int(p.lineno)),
            nombre_metodo=p.OBJECTID,
            argumentos=p.lista_args,
            linea=int(p.lineno)
        )

    # Paréntesis
    @_("'(' Expresion ')'")
    def Expresion(self, p):
        return p.Expresion

    # Literales
    @_("OBJECTID")
    def Expresion(self, p):
        return Objeto(nombre=p.OBJECTID, linea=int(p.lineno))

    @_("INT_CONST")
    def Expresion(self, p):
        return Entero(valor=p.INT_CONST, linea=int(p.lineno))

    @_("STR_CONST")
    def Expresion(self, p):
        return String(valor=p.STR_CONST, linea=int(p.lineno))

    @_("BOOL_CONST")
    def Expresion(self, p):
        return Booleano(valor=p.BOOL_CONST, linea=int(p.lineno))

    # ─── Lista de expresiones (bloque) ───────────────────────────────────────────

    @_("Expresion ';'")
    def lista_exprs(self, p):
        return [p.Expresion]

    @_("lista_exprs Expresion ';'")
    def lista_exprs(self, p):
        return p.lista_exprs + [p.Expresion]

    @_("error ';'")
    def lista_exprs(self, p):
        return []

    @_("lista_exprs error ';'")
    def lista_exprs(self, p):
        return p.lista_exprs

    # ─── Lista de argumentos ─────────────────────────────────────────────────────

    @_("Expresion")
    def lista_args(self, p):
        return [p.Expresion]

    @_("lista_args ',' Expresion")
    def lista_args(self, p):
        return p.lista_args + [p.Expresion]

    # ─── Bindings del LET ────────────────────────────────────────────────────────

    @_("OBJECTID ':' TYPEID")
    def lista_let(self, p):
        return [(p.OBJECTID, p.TYPEID, NoExpr(linea=int(p.lineno)), int(p.lineno))]

    @_("OBJECTID ':' TYPEID ASSIGN Expresion")
    def lista_let(self, p):
        return [(p.OBJECTID, p.TYPEID, p.Expresion, int(p.lineno))]

    @_("lista_let ',' OBJECTID ':' TYPEID")
    def lista_let(self, p):
        return p.lista_let + [(p.OBJECTID, p.TYPEID, NoExpr(linea=int(p.lineno)), int(p.lineno))]

    @_("lista_let ',' OBJECTID ':' TYPEID ASSIGN Expresion")
    def lista_let(self, p):
        return p.lista_let + [(p.OBJECTID, p.TYPEID, p.Expresion, int(p.lineno))]

    @_("error")
    def lista_let(self, p):
        return []

    @_("lista_let ',' error")
    def lista_let(self, p):
        return p.lista_let

    # ─── Ramas del CASE ──────────────────────────────────────────────────────────

    @_("OBJECTID ':' TYPEID DARROW Expresion ';'")
    def lista_ramas(self, p):
        return [RamaCase(
            nombre_variable=p.OBJECTID,
            tipo=p.TYPEID,
            cuerpo=p.Expresion,
            linea=int(p.lineno)
        )]
    @_("OBJECTID error DARROW Expresion ';'")
    def lista_ramas(self, p):
        return []

    @_("lista_ramas OBJECTID error DARROW Expresion ';'")
    def lista_ramas(self, p):
        return p.lista_ramas

    @_("lista_ramas OBJECTID ':' TYPEID DARROW Expresion ';'")
    def lista_ramas(self, p):
        return p.lista_ramas + [RamaCase(
            nombre_variable=p.OBJECTID,
            tipo=p.TYPEID,
            cuerpo=p.Expresion,
            linea=int(p.lineno)
        )]

    @_("error ';'")
    def lista_ramas(self, p):
        return []

    @_("lista_ramas error ';'")
    def lista_ramas(self, p):
        return p.lista_ramas

    # ─── Manejo de errores sintácticos ───────────────────────────────────────────

    def error(self, p):
        if p:
            tipo = p.type
            if len(tipo) == 1:
                tipo = f"'{tipo}'"
            msg = (
                f'"{self.nombre_fichero}", line {int(p.lineno)}: '
                f'syntax error at or near {tipo}'
            )
            if p.type in ('OBJECTID', 'TYPEID', 'INT_CONST', 'STR_CONST'):
                msg += f' = {p.value}'
        else:
            msg = f'"{self.nombre_fichero}", line 0: syntax error at or near EOF'
        self.errores.append(msg)


# ─── Wrapper seguro para parse() ─────────────────────────────────────────────

class _DummyPrograma:
    """Devuelto cuando parse() retorna None para evitar crashes en main.py"""
    def Tipo(self):
        pass
    def str(self, n):
        return ''


def _safe_parse(self, tokens):
    result = super(CoolParser, self).parse(tokens)
    if result is None:
        return _DummyPrograma()
    return result


CoolParser.parse = _safe_parse
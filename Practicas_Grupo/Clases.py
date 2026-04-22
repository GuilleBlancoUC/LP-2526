# coding: utf-8
from dataclasses import dataclass, field
from typing import List

errores_semanticos = []

class Ambito:
    def __init__(self):
        self.variables = {}
        self.metodos = {}
        self.arbol_clases = {}
        self.nombre_clase = 'Object'  # clase actual en contexto
        self.padre = None             # ámbito padre (para scopes anidados)
        self.atributos_clase = {}     # {clase: set(nombres_atributos)}
        self.formales_metodos = {}    # {(metodo, clase): [nombres_formales]}

        # Clases y métodos built-in
        self.arbol_clases['Object'] = None
        self.metodos[('abort', 'Object')] = ([], 'Object')
        self.metodos[('copy', 'Object')] = ([], 'SELF_TYPE')
        self.metodos[('type_name', 'Object')] = ([], 'String')
        self.arbol_clases['IO'] = 'Object'
        self.metodos[('out_string', 'IO')] = (['String'], 'SELF_TYPE')
        self.metodos[('out_int', 'IO')] = (['Int'], 'SELF_TYPE')
        self.metodos[('in_string', 'IO')] = ([], 'String')
        self.metodos[('in_int', 'IO')] = ([], 'Int')
        self.arbol_clases['Int'] = 'Object'
        self.arbol_clases['String'] = 'Object'
        self.arbol_clases['Bool'] = 'Object'
        self.metodos[('length', 'String')] = ([], 'Int')
        self.metodos[('concat', 'String')] = (['String'], 'String')
        self.metodos[('substr', 'String')] = (['Int', 'Int'], 'String')

    def nuevo_variable(self, nombre, tipo):
        self.variables[nombre] = tipo

    def dame_tipo_variable(self, nombre):
        if nombre == 'self':
            return self.nombre_clase
        if nombre in self.variables:
            return self.variables[nombre]
        if self.padre:
            return self.padre.dame_tipo_variable(nombre)
        return '_no_type'

    # Alias usado en Asignacion.Tipo() del código original
    def get_tipo_variable(self, nombre):
        return self.dame_tipo_variable(nombre)

    def nueva_clase(self, nombre, padre):
        self.arbol_clases[nombre] = padre

    def dame_clase(self, nombre):
        return nombre if nombre in self.arbol_clases else None

    def nuevo_metodo(self, nombre, tipo, args, retorno, nombres_formales=None):
        self.metodos[(nombre, tipo)] = (args, retorno)
        if nombres_formales is not None:
            self.formales_metodos[(nombre, tipo)] = nombres_formales

    def dame_metodo_clase(self, nombre_metodo, tipo):
        """Busca el método nombre_metodo en tipo y sus ancestros."""
        if tipo is None:
            return None
        # Resolver SELF_TYPE
        if tipo == 'SELF_TYPE':
            tipo = self.nombre_clase
        if (nombre_metodo, tipo) in self.metodos:
            return self.metodos[(nombre_metodo, tipo)]
        padre = self.arbol_clases.get(tipo)
        if padre is not None:
            return self.dame_metodo_clase(nombre_metodo, padre)
        return None

    def es_subtipo(self, tipo1, tipo2):
        """¿Es tipo1 subtipo o igual a tipo2?"""
        if tipo1 == tipo2:
            return True
        # Resolver SELF_TYPE al tipo de la clase actual
        if tipo1 == 'SELF_TYPE':
            tipo1 = self.nombre_clase
        if tipo2 == 'SELF_TYPE':
            tipo2 = self.nombre_clase
        if tipo1 is None or tipo1 == '_no_type':
            return False
        if tipo2 == 'Object':
            return True
        actual = self.arbol_clases.get(tipo1)
        visitados = set()
        while actual is not None and actual not in visitados:
            if actual == tipo2:
                return True
            visitados.add(actual)
            actual = self.arbol_clases.get(actual)
        return False

    def tipo_comun_ancestro(self, tipos):
        """Devuelve el ancestro común más específico de una lista de tipos."""
        if not tipos:
            return 'Object'
        # Resolver SELF_TYPE
        tipos = [self.nombre_clase if t == 'SELF_TYPE' else t for t in tipos]
        # Construir cadena de ancestros para el primer tipo
        def cadena(tipo):
            resultado = []
            actual = tipo
            visitados = set()
            while actual is not None and actual not in visitados:
                resultado.append(actual)
                visitados.add(actual)
                actual = self.arbol_clases.get(actual)
            return resultado
        # Buscar el ancestro común más cercano
        ancestros_primero = cadena(tipos[0])
        for ancestro in ancestros_primero:
            if all(self.es_subtipo(t, ancestro) for t in tipos):
                return ancestro
        return 'Object'


@dataclass
class Nodo:
    linea: int = 0

    def str(self, n):
        return f'{n*" "}#{self.linea}\n'

    def Tipo(self, ambito):
        pass


@dataclass
class Formal(Nodo):
    nombre_variable: str = '_no_set'
    tipo: str = '_no_type'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_formal\n'
        resultado += f'{(n+2)*" "}{self.nombre_variable}\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        return resultado

    def Tipo(self, ambito):
        pass


class Expresion(Nodo):
    cast: str = '_no_type'

    def Tipo(self, ambito):
        pass


@dataclass
class Asignacion(Expresion):
    nombre: str = '_no_set'
    cuerpo: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_assign\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.cuerpo.Tipo(ambito)
        tipo_variable = ambito.get_tipo_variable(self.nombre)
        tipo_cuerpo = self.cuerpo.cast
        self.cast = tipo_cuerpo
        if not ambito.es_subtipo(tipo_cuerpo, tipo_variable):
            errores_semanticos.append(
                f"{self.linea}: Type {tipo_cuerpo} of assigned expression does not conform to declared type {tipo_variable} of identifier {self.nombre}."
            )


@dataclass
class LlamadaMetodoEstatico(Expresion):
    cuerpo: Expresion = None
    clase: str = '_no_type'
    nombre_metodo: str = '_no_set'
    argumentos: List[Expresion] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_static_dispatch\n'
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n+2)*" "}{self.clase}\n'
        resultado += f'{(n+2)*" "}{self.nombre_metodo}\n'
        resultado += f'{(n+2)*" "}(\n'
        resultado += ''.join([c.str(n+2) for c in self.argumentos])
        resultado += f'{(n+2)*" "})\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.cuerpo.Tipo(ambito)
        for a in self.argumentos:
            a.Tipo(ambito)
        metodo = ambito.dame_metodo_clase(self.nombre_metodo, self.clase)
        if metodo:
            _, retorno = metodo
            # SELF_TYPE en retorno significa el tipo del receptor
            self.cast = self.cuerpo.cast if retorno == 'SELF_TYPE' else retorno
        else:
            self.cast = '_no_type'


@dataclass
class LlamadaMetodo(Expresion):
    cuerpo: Expresion = None
    nombre_metodo: str = '_no_set'
    argumentos: List[Expresion] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_dispatch\n'
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n+2)*" "}{self.nombre_metodo}\n'
        resultado += f'{(n+2)*" "}(\n'
        resultado += ''.join([c.str(n+2) for c in self.argumentos])
        resultado += f'{(n+2)*" "})\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def valor(self, ambito):
        cuerpo_ret = self.cuerpo.valor(ambito)
        if self.nombre_metodo == 'copy':
            return cuerpo_ret
        elif self.nombre_metodo == 'abort':
            exit()

    def Tipo(self, ambito):
        self.cuerpo.Tipo(ambito)
        tipo_cuerpo = self.cuerpo.cast
        # Resolver SELF_TYPE al tipo real de la clase actual
        if tipo_cuerpo == 'SELF_TYPE':
            tipo_cuerpo = ambito.nombre_clase
        for a in self.argumentos:
            a.Tipo(ambito)
        metodo = ambito.dame_metodo_clase(self.nombre_metodo, tipo_cuerpo)
        if metodo:
            params, retorno = metodo
            # Comprobar conformidad de argumentos con parámetros formales
            for i, (arg, param_tipo) in enumerate(zip(self.argumentos, params)):
                tipo_arg = arg.cast
                if not ambito.es_subtipo(tipo_arg, param_tipo):
                    # Obtener nombre del parámetro formal si está disponible
                    errores_semanticos.append(
                        f"{self.linea}: In call of method {self.nombre_metodo}, type {tipo_arg} of parameter "
                        f"{self._nombre_formal(i, tipo_cuerpo, ambito)} does not conform to declared type {param_tipo}."
                    )
            # SELF_TYPE en retorno significa el tipo del receptor, no la clase actual
            self.cast = tipo_cuerpo if retorno == 'SELF_TYPE' else retorno
        else:
            errores_semanticos.append(
                f"{self.linea}: Dispatch to undefined method {self.nombre_metodo}."
            )
            self.cast = '_no_type'

    def _nombre_formal(self, i, tipo_clase, ambito):
        """Devuelve el nombre del parámetro formal i-ésimo del método en tipo_clase."""
        # Buscar en el árbol de clases el método con sus formales
        tipo = tipo_clase
        while tipo:
            if (self.nombre_metodo, tipo) in ambito.metodos:
                break
            tipo = ambito.arbol_clases.get(tipo)
        if tipo and hasattr(ambito, 'formales_metodos'):
            formales = ambito.formales_metodos.get((self.nombre_metodo, tipo), [])
            if i < len(formales):
                return formales[i]
        # Fallback: usar letra genérica
        return chr(ord('a') + i)


@dataclass
class Condicional(Expresion):
    condicion: Expresion = None
    verdadero: Expresion = None
    falso: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_cond\n'
        resultado += self.condicion.str(n+2)
        resultado += self.verdadero.str(n+2)
        resultado += self.falso.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.condicion.Tipo(ambito)
        self.verdadero.Tipo(ambito)
        self.falso.Tipo(ambito)
        self.cast = ambito.tipo_comun_ancestro([self.verdadero.cast, self.falso.cast])


@dataclass
class Bucle(Expresion):
    condicion: Expresion = None
    cuerpo: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_loop\n'
        resultado += self.condicion.str(n+2)
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.condicion.Tipo(ambito)
        self.cuerpo.Tipo(ambito)
        self.cast = 'Object'


@dataclass
class Let(Expresion):
    nombre: str = '_no_set'
    tipo: str = '_no_set'
    inicializacion: Expresion = None
    cuerpo: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_let\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        resultado += self.inicializacion.str(n+2)
        resultado += self.cuerpo.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        if self.inicializacion:
            self.inicializacion.Tipo(ambito)
        ambito.nuevo_variable(self.nombre, self.tipo)
        if self.cuerpo:
            self.cuerpo.Tipo(ambito)
            self.cast = self.cuerpo.cast
        else:
            self.cast = 'Object'


@dataclass
class Bloque(Expresion):
    expresiones: List[Expresion] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado = f'{n*" "}_block\n'
        resultado += ''.join([e.str(n+2) for e in self.expresiones])
        resultado += f'{(n)*" "}: {self.cast}\n'
        resultado += '\n'
        return resultado

    def Tipo(self, ambito):
        for e in self.expresiones:
            e.Tipo(ambito)
        if self.expresiones:
            self.cast = self.expresiones[-1].cast
        else:
            self.cast = 'Object'


@dataclass
class RamaCase(Nodo):
    cast: str = '_no_type'
    nombre_variable: str = '_no_set'
    tipo: str = '_no_set'
    cuerpo: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_branch\n'
        resultado += f'{(n+2)*" "}{self.nombre_variable}\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        resultado += self.cuerpo.str(n+2)
        return resultado

    def Tipo(self, ambito):
        ambito.nuevo_variable(self.nombre_variable, self.tipo)
        if self.cuerpo:
            self.cuerpo.Tipo(ambito)
            self.cast = self.cuerpo.cast
        else:
            self.cast = 'Object'


@dataclass
class Swicht(Nodo):
    cast: str = '_no_type'
    expr: Expresion = None
    casos: List[RamaCase] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_typcase\n'
        resultado += self.expr.str(n+2)
        resultado += ''.join([c.str(n+2) for c in self.casos])
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.expr.Tipo(ambito)
        tipos_casos = []
        for c in self.casos:
            c.Tipo(ambito)
            tipos_casos.append(c.cast)
        if tipos_casos:
            self.cast = ambito.tipo_comun_ancestro(tipos_casos)
        else:
            self.cast = 'Object'


@dataclass
class Nueva(Nodo):
    cast: str = '_no_type'
    tipo: str = '_no_set'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_new\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        # SELF_TYPE se resuelve al tipo de la clase actual
        if self.tipo == 'SELF_TYPE':
            self.cast = ambito.nombre_clase
        else:
            self.cast = self.tipo

@dataclass
class OperacionBinaria(Expresion):
    izquierda: Expresion = None
    derecha: Expresion = None

    def Tipo(self, ambito):
        pass


@dataclass
class Suma(OperacionBinaria):
    operando: str = '+'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_plus\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        if self.izquierda.cast != 'Int' or self.derecha.cast != 'Int':
            errores_semanticos.append(
                f"{self.linea}: non-Int arguments: {self.izquierda.cast} + {self.derecha.cast}"
            )
        self.cast = 'Int'


@dataclass
class Resta(OperacionBinaria):
    operando: str = '-'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_sub\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        if self.izquierda.cast != 'Int' or self.derecha.cast != 'Int':
            errores_semanticos.append(
                f"{self.linea}: non-Int arguments: {self.izquierda.cast} - {self.derecha.cast}"
            )
        self.cast = 'Int'


@dataclass
class Multiplicacion(OperacionBinaria):
    operando: str = '*'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_mul\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        if self.izquierda.cast != 'Int' or self.derecha.cast != 'Int':
            errores_semanticos.append(
                f"{self.linea}: non-Int arguments: {self.izquierda.cast} * {self.derecha.cast}"
            )
        self.cast = 'Int'


@dataclass
class Division(OperacionBinaria):
    operando: str = '/'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_divide\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        if self.izquierda.cast != 'Int' or self.derecha.cast != 'Int':
            errores_semanticos.append(
                f"{self.linea}: non-Int arguments: {self.izquierda.cast} / {self.derecha.cast}"
            )
        self.cast = 'Int'


@dataclass
class Menor(OperacionBinaria):
    operando: str = '<'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_lt\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        self.cast = 'Bool'


@dataclass
class LeIgual(OperacionBinaria):
    operando: str = '<='

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_leq\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        self.cast = 'Bool'


@dataclass
class Igual(OperacionBinaria):
    operando: str = '='

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_eq\n'
        resultado += self.izquierda.str(n+2)
        resultado += self.derecha.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def valor(self, ambito):
        izq = self.izquierda.valor(ambito)
        dcha = self.derecha.valor(ambito)
        if izq == dcha:
            return True
        else:
            return False

    def Tipo(self, ambito):
        self.izquierda.Tipo(ambito)
        self.derecha.Tipo(ambito)
        self.cast = 'Bool'


@dataclass
class Neg(Expresion):
    expr: Expresion = None
    operador: str = '~'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_neg\n'
        resultado += self.expr.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.expr.Tipo(ambito)
        self.cast = 'Int'


@dataclass
class Not(Expresion):
    expr: Expresion = None
    operador: str = 'NOT'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_comp\n'
        resultado += self.expr.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.expr.Tipo(ambito)
        self.cast = 'Bool'


@dataclass
class EsNulo(Expresion):
    expr: Expresion = None

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_isvoid\n'
        resultado += self.expr.str(n+2)
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.expr.Tipo(ambito)
        self.cast = 'Bool'


@dataclass
class Objeto(Expresion):
    nombre: str = '_no_set'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_object\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        if self.nombre == 'self':
            self.cast = 'SELF_TYPE'
        else:
            self.cast = ambito.dame_tipo_variable(self.nombre)
            if self.cast == '_no_type':
                errores_semanticos.append(
                    f"{self.linea}: Undeclared identifier {self.nombre}."
                )


@dataclass
class NoExpr(Expresion):
    nombre: str = ''

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_no_expr\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.cast = '_no_type'


@dataclass
class Entero(Expresion):
    valor: int = 0

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_int\n'
        resultado += f'{(n+2)*" "}{self.valor}\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.cast = 'Int'


@dataclass
class String(Expresion):
    valor: str = '_no_set'

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_string\n'
        escaped = (self.valor
                   .replace('\\', '\\\\')
                   .replace('\n', '\\n')
                   .replace('\t', '\\t')
                   .replace('\b', '\\b')
                   .replace('\f', '\\f')
                   .replace('\0', '\\0'))
        resultado += f'{(n+2)*" "}"{escaped}"\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def Tipo(self, ambito):
        self.cast = 'String'


@dataclass
class Booleano(Expresion):
    valor: bool = False

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_bool\n'
        resultado += f'{(n+2)*" "}{1 if self.valor else 0}\n'
        resultado += f'{(n)*" "}: {self.cast}\n'
        return resultado

    def valor(self, ambito):
        return self.valor

    def Tipo(self, ambito):
        self.cast = 'Bool'


@dataclass
class IterableNodo(Nodo):
    secuencia: List = field(default_factory=List)

    def Tipo(self, ambito):
        for c in self.secuencia:
            c.Tipo(ambito)


@dataclass
class Programa(IterableNodo):
    def str(self, n):
        resultado = super().str(n)
        resultado += f'{" "*n}_program\n'
        resultado += ''.join([c.str(n+2) for c in self.secuencia])
        return resultado

    def Tipo(self):
        ambito = Ambito()
        errores_semanticos.clear()
        # Primer paso: registrar todas las clases para que es_subtipo funcione
        for c in self.secuencia:
            if isinstance(c, Clase):
                ambito.nueva_clase(c.nombre, c.padre)
        # Segundo paso: registrar todos los métodos de todas las clases
        for c in self.secuencia:
            if isinstance(c, Clase):
                for caract in c.caracteristicas:
                    if isinstance(caract, Metodo):
                        args = [f.tipo for f in caract.formales]
                        nombres = [f.nombre_variable for f in caract.formales]
                        ambito.nuevo_metodo(caract.nombre, c.nombre, args, caract.tipo, nombres)
        # Tercer paso: chequear tipos
        for c in self.secuencia:
            c.Tipo(ambito)


@dataclass
class Caracteristica(Nodo):
    nombre: str = '_no_set'
    tipo: str = '_no_set'
    cuerpo: Expresion = None

    def Tipo(self, ambito):
        pass


@dataclass
class Clase(Nodo):
    nombre: str = '_no_set'
    padre: str = '_no_set'
    nombre_fichero: str = '_no_set'
    caracteristicas: List[Caracteristica] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_class\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += f'{(n+2)*" "}{self.padre}\n'
        resultado += f'{(n+2)*" "}"{self.nombre_fichero}"\n'
        resultado += f'{(n+2)*" "}(\n'
        resultado += ''.join([c.str(n+2) for c in self.caracteristicas])
        resultado += '\n'
        resultado += f'{(n+2)*" "})\n'
        return resultado

    def Tipo(self, ambito):
        # Crear un ámbito local para esta clase, con el global como padre,
        # para que los atributos de una clase no contaminen las demás
        ambito_clase = Ambito()
        ambito_clase.arbol_clases = ambito.arbol_clases
        ambito_clase.metodos = ambito.metodos
        ambito_clase.nombre_clase = self.nombre
        # Primer paso: registrar métodos
        for c in self.caracteristicas:
            if isinstance(c, Metodo):
                args = [f.tipo for f in c.formales]
                nombres = [f.nombre_variable for f in c.formales]
                ambito_clase.nuevo_metodo(c.nombre, self.nombre, args, c.tipo, nombres)
        # Segundo paso: registrar atributos propios en el ámbito local
        ambito.atributos_clase[self.nombre] = {c.nombre for c in self.caracteristicas if isinstance(c, Atributo)}
        for c in self.caracteristicas:
            if isinstance(c, Atributo):
                ambito_clase.nuevo_variable(c.nombre, c.tipo)
        ambito_clase.atributos_clase = ambito.atributos_clase
        ambito_clase.formales_metodos = ambito.formales_metodos
        # Tercer paso: chequear tipos de métodos y atributos
        for c in self.caracteristicas:
            if isinstance(c, Metodo):
                c.Tipo(ambito_clase)
        for c in self.caracteristicas:
            if isinstance(c, Atributo):
                c.Tipo(ambito_clase)


@dataclass
class Metodo(Caracteristica):
    formales: List[Formal] = field(default_factory=list)

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_method\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += ''.join([c.str(n+2) for c in self.formales])
        resultado += f'{(n + 2) * " "}{self.tipo}\n'
        resultado += self.cuerpo.str(n+2)
        return resultado

    def Tipo(self, ambito):
        # Registrar los parámetros formales como variables del scope
        for f in self.formales:
            ambito.nuevo_variable(f.nombre_variable, f.tipo)
        self.cuerpo.Tipo(ambito)
        self.cast = self.tipo


class Atributo(Caracteristica):

    def str(self, n):
        resultado = super().str(n)
        resultado += f'{(n)*" "}_attr\n'
        resultado += f'{(n+2)*" "}{self.nombre}\n'
        resultado += f'{(n+2)*" "}{self.tipo}\n'
        resultado += self.cuerpo.str(n+2)
        return resultado

    def Tipo(self, ambito):
        ambito.nuevo_variable(self.nombre, self.tipo)
        if self.nombre == 'self':
            errores_semanticos.append(f"{self.linea}: 'self' cannot be the name of an attribute.")
        # Comprobar si el atributo está definido en alguna clase ancestro
        padre = ambito.arbol_clases.get(ambito.nombre_clase)
        while padre is not None:
            if self.nombre in ambito.atributos_clase.get(padre, set()):
                errores_semanticos.append(f"{self.linea}: Attribute {self.nombre} is an attribute of an inherited class.")
                break
            padre = ambito.arbol_clases.get(padre)   
        if self.cuerpo:
            self.cuerpo.Tipo(ambito)
            self.cast = self.tipo
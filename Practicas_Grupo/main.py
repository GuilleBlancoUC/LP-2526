import os
import re
import sys

# from coloredama import init  ## Para coloredear la salida en la terminal
from termcolor import colored ## Para coloredear la salida en la terminal
#init()


DIRECTORIO = os.path.dirname(os.path.abspath(__file__))
sys.path.append(DIRECTORIO)

from Lexer import *
from Parser import CoolParser
from Clases import *

PRACTICA = "01" # Practica que hay que evaluar
DEBUG = True   # Decir si se lanzan mensajes de debug
NUMLINEAS = 3   # Numero de lineas que se muestran antes y después de la no coincidencia
sys.path.append(DIRECTORIO)
DIR = os.path.join(DIRECTORIO, PRACTICA, 'grading')
FICHEROS = os.listdir(DIR)
TESTS = [fich for fich in FICHEROS
         if os.path.isfile(os.path.join(DIR, fich)) and
         re.search(r"^[a-zA-Z].*\.(cool|test|cl)$",fich)]
TESTS.sort()
# TESTS = ["anattributenamedself.test"]

if True:
    for fich in TESTS:
        lexer = CoolLexer()
        f = open(os.path.join(DIR, fich), 'r', newline='')
        g = open(os.path.join(DIR, fich + '.out'), 'r', newline='')
        if os.path.isfile(os.path.join(DIR, fich)+'.nuestro'):
            os.remove(os.path.join(DIR, fich)+'.nuestro')
        if os.path.isfile(os.path.join(DIR, fich)+'.bien'):
            os.remove(os.path.join(DIR, fich)+'.bien')            
        texto = ''
        entrada = f.read()
        f.close()
        if PRACTICA == '01':
            texto = '\n'.join(lexer.salida(entrada))
            texto = f'#name "{fich}"\n' + texto
            resultado = g.read()
            g.close()
            texto = re.sub(r'#\d+\b','',texto)
            resultado = re.sub(r'#\d+\b','',resultado)
            nuestro = [linea.strip() for linea in texto.split('\n') if linea.strip()]
            bien = [linea.strip() for linea in resultado.split('\n') if linea.strip()]
            texto = '\n'.join(nuestro)
            resultado = '\n'.join(bien)
            #print(texto)
            #print(resultado)
            if texto.strip().split() != resultado.strip().split():
                print(f"Revisa el fichero {fich}")
                if DEBUG:
                    f = open(os.path.join(DIR, fich)+'.nuestro', 'w')
                    g = open(os.path.join(DIR, fich)+'.bien', 'w')
                    f.write(texto.strip())
                    g.write(resultado.strip())
                    f.close()
                    g.close()
        elif PRACTICA in ('02', '03'):
            parser = CoolParser()
            parser.nombre_fichero = fich
            parser.errores = []
            bien = ''.join([c.replace('\n', '') for c in g.readlines() if c and '#' not in c])
            bien_total = bien
            g.close()
            j = parser.parse(lexer.tokenize(entrada))
            try:
                if PRACTICA == '03':
                    j.Tipo()
                if j and not parser.errores and not errores_semanticos:
                    resultado = '\n'.join([c for c in j.str(0).split('\n')
                                           if c and '#' not in c])
                else:
                    resultado = '\n'.join(parser.errores)
                    if PRACTICA == '03':
                        resultado += fich + ":"
                        resultado += '\n'.join(errores_semanticos)
                        resultado += '\n' + "Compilation halted due to static semantic errors."
                    else:
                        resultado += '\n' + "Compilation halted due to lex and parse errors"
                    

                if resultado.lower().strip().split() != bien.lower().strip().split():
                    print(f"Revisa el fichero {fich}")
                    if DEBUG:
                        nuestro = [linea for linea in resultado.split('\n') if linea]
                        bien = [linea for linea in bien.split('\n') if linea]
                        linea = 0
                        while nuestro[linea:linea+NUMLINEAS] == bien[linea:linea+NUMLINEAS]:
                            linea += 1
                        print(colored('\n'.join(nuestro[linea:linea+NUMLINEAS]), 'white', 'on_red'))
                        print(colored('\n'.join(bien[linea:linea+NUMLINEAS]), 'blue', 'on_green'))
                        f = open(os.path.join(DIR, fich)+'.nuestro', 'w')
                        g = open(os.path.join(DIR, fich)+'.bien', 'w')
                        f.write(resultado.strip())
                        g.write(bien_total.strip())
                        f.close()
                        g.close()
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Lanza excepción en {fich} con el texto {e}")

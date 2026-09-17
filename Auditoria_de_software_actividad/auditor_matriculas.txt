"""
auditor_matriculas.py
---------------------------------------------------------------
Herramienta de apoyo para la auditoria de software del archivo
sistema_matriculas.py.

Que hace:
  1. Lee el codigo fuente como texto plano (analisis estatico).
     NO ejecuta el sistema auditado ni abre la ventana de Tkinter.
  2. Aplica dos tipos de reglas:
       - Reglas de linea: buscan un patron en cada linea del archivo.
       - Reglas de archivo: verifican la AUSENCIA de un control en
         todo el documento (por ejemplo, que no exista try/except).
  3. Imprime una matriz de hallazgos en consola y la exporta a
     reporte_auditoria.csv y reporte_auditoria.txt.

Alcance: la herramienta apoya el analisis, no reemplaza el criterio
del auditor. Todo lo que reporta es un POSIBLE hallazgo que debe ser
confirmado leyendo el codigo.

Uso:  python auditor_matriculas.py [archivo_a_auditar]
---------------------------------------------------------------
"""

import csv
import os
import re
import sys
from datetime import datetime

# ----------------------------------------------------------------------
# CONFIGURACION GENERAL
# ----------------------------------------------------------------------

ARCHIVO_POR_DEFECTO = "sistema_matriculas.py"
REPORTE_CSV = "reporte_auditoria.csv"
REPORTE_TXT = "reporte_auditoria.txt"

ANCHO = 100  # ancho de la consola para los separadores


# ----------------------------------------------------------------------
# CATALOGO DE REGLAS
# ----------------------------------------------------------------------
# Cada regla es un diccionario con la informacion que exige el enunciado:
# categoria, patron (evidencia), descripcion del hallazgo, riesgo,
# severidad y recomendacion.

REGLAS_DE_LINEA = [
    {
        "codigo": "VAL",
        "categoria": "Validacion de datos",
        "patron": r"entrada_\w+\.get\(\)",
        "descripcion": "Se lee un campo del formulario y se usa sin verificar "
                       "si esta vacio o si tiene el tipo esperado.",
        "riesgo": "Se pueden almacenar registros incompletos o con datos sin sentido "
                  "(nombre vacio, edad en letras) y el sistema igual informa exito.",
        "severidad": "Alta",
        "recomendacion": "Aplicar .strip() y rechazar la operacion cuando el campo "
                         "quede vacio, mostrando un mensaje al usuario.",
    },
    {
        "codigo": "ERR",
        "categoria": "Manejo de errores",
        "patron": r"\bint\s*\(",
        "descripcion": "Conversion de texto a numero entero sin proteccion try/except.",
        "riesgo": "Si el texto no es numerico, Python lanza ValueError y la aplicacion "
                  "se detiene; los estudiantes que solo estaban en memoria se pierden.",
        "severidad": "Alta",
        "recomendacion": "Envolver la conversion en try/except ValueError y avisar "
                         "al usuario en lugar de dejar caer el programa.",
    },
    {
        "codigo": "ARC",
        "categoria": "Gestion de archivos",
        "patron": r"\bopen\s*\(",
        "descripcion": "Apertura de archivo sin bloque with y sin try/except. "
                       "Ademas el modo 'w' sobrescribe el contenido anterior.",
        "riesgo": "Si la ruta no existe o no hay permisos, el programa falla. "
                  "Si la escritura se interrumpe, se pierde el archivo anterior "
                  "y el nuevo queda incompleto.",
        "severidad": "Alta",
        "recomendacion": "Usar with open(...) dentro de try/except OSError y escribir "
                         "primero en un archivo temporal antes de reemplazar.",
    },
    {
        "codigo": "SEG",
        "categoria": "Seguridad de la informacion",
        "patron": r"write\s*\(\s*str\s*\(",
        "descripcion": "Los datos personales se escriben en texto plano usando str() "
                       "sobre el diccionario completo.",
        "riesgo": "Nombre, documento de identidad, edad y programa quedan legibles "
                  "para cualquier persona con acceso a la carpeta.",
        "severidad": "Alta",
        "recomendacion": "Guardar solo los datos necesarios, usar un formato controlado "
                         "(CSV o JSON) y restringir permisos o cifrar el archivo.",
    },
    {
        "codigo": "INT",
        "categoria": "Integridad de los datos",
        "patron": r"\.append\s*\(",
        "descripcion": "Se agrega el registro a la lista sin comprobar si el documento "
                       "ya fue registrado antes.",
        "riesgo": "Se generan registros duplicados con el mismo documento, lo que luego "
                  "vuelve ambigua la eliminacion y los reportes.",
        "severidad": "Media",
        "recomendacion": "Antes de agregar, recorrer la lista y rechazar el documento "
                         "si ya existe.",
    },
    {
        "codigo": "INT",
        "categoria": "Integridad de los datos",
        "patron": r"\.remove\s*\(",
        "descripcion": "Se elimina un elemento de la lista mientras se recorre esa "
                       "misma lista con un for.",
        "riesgo": "El recorrido puede saltarse elementos y no se garantiza que se "
                  "afecte unicamente el registro esperado.",
        "severidad": "Alta",
        "recomendacion": "Recorrer una copia de la lista, o construir una lista nueva "
                         "sin el registro, y pedir confirmacion antes de borrar.",
    },
    {
        "codigo": "INT",
        "categoria": "Integridad de los datos",
        "patron": r"text\s*=\s*[\"']Proceso terminado[\"']",
        "descripcion": "Mensaje de resultado fijo que se muestra sin importar si "
                       "realmente se elimino algun registro.",
        "riesgo": "El usuario no distingue entre 'se elimino' y 'no se encontro', "
                  "y puede creer que una operacion fallida fue exitosa.",
        "severidad": "Media",
        "recomendacion": "Contar las coincidencias y mostrar un mensaje diferente "
                         "para cada caso.",
    },
    {
        "codigo": "MAN",
        "categoria": "Mantenibilidad",
        "patron": r"mensaje\.config\s*\(",
        "descripcion": "La funcion de logica modifica directamente un widget global "
                       "de la interfaz grafica.",
        "riesgo": "La regla de negocio queda amarrada a Tkinter: no se puede probar "
                  "ni reutilizar sin abrir la ventana.",
        "severidad": "Media",
        "recomendacion": "Separar la logica (registrar, eliminar, calcular) de la capa "
                         "de presentacion; que las funciones retornen valores.",
    },
]

REGLAS_DE_ARCHIVO = [
    {
        "codigo": "ERR",
        "categoria": "Manejo de errores",
        "patron": r"\btry\s*:",
        "evidencia": "No aparece ningun bloque try: en el archivo",
        "descripcion": "El programa completo carece de manejo de excepciones.",
        "riesgo": "Cualquier situacion inesperada (conversion invalida, fallo de disco) "
                  "termina la aplicacion sin aviso ni registro.",
        "severidad": "Alta",
        "recomendacion": "Definir un manejo de errores minimo en las operaciones de "
                         "conversion y de archivo.",
    },
    {
        "codigo": "ARC",
        "categoria": "Gestion de archivos",
        "patron": r"with\s+open\s*\(",
        "evidencia": "No aparece 'with open(' ni 'close()' en el archivo",
        "descripcion": "El archivo abierto en guardar_datos nunca se cierra de forma "
                       "explicita ni con un administrador de contexto.",
        "riesgo": "El contenido puede quedar en el bufer sin escribirse y el archivo "
                  "bloqueado mientras la ventana siga abierta.",
        "severidad": "Media",
        "recomendacion": "Reemplazar open(...) por with open(...) para garantizar el "
                         "cierre en todos los casos.",
    },
    {
        "codigo": "VAL",
        "categoria": "Validacion de datos",
        "patron": r"\.strip\s*\(\)|if\s+not\s+\w+",
        "evidencia": "No aparecen .strip() ni comprobaciones del tipo 'if not campo'",
        "descripcion": "No existe ninguna validacion de campos obligatorios en todo "
                       "el programa.",
        "riesgo": "La ausencia de validacion no es un error aislado sino un control "
                  "que falta en el sistema completo.",
        "severidad": "Alta",
        "recomendacion": "Crear una funcion unica de validacion e invocarla desde "
                         "registrar, eliminar y calcular.",
    },
    {
        "codigo": "SEG",
        "categoria": "Seguridad de la informacion",
        "patron": r"hashlib|cryptography|getpass|permission|chmod",
        "evidencia": "No se importa ninguna libreria de proteccion de datos",
        "descripcion": "No hay cifrado, control de acceso ni autenticacion para los "
                       "datos personales que administra el sistema.",
        "riesgo": "Cualquier usuario del equipo puede abrir, copiar o modificar los "
                  "datos de los estudiantes.",
        "severidad": "Alta",
        "recomendacion": "Restringir el acceso al archivo y evaluar el cifrado de los "
                         "campos sensibles, empezando por el documento.",
    },
]


# ----------------------------------------------------------------------
# FUNCIONES DE APOYO
# ----------------------------------------------------------------------

def leer_codigo(ruta):
    """Lee el archivo a auditar y devuelve la lista de lineas."""
    if not os.path.exists(ruta):
        print("ERROR: no se encontro el archivo '" + ruta + "'.")
        print("Coloque auditor_matriculas.py en la misma carpeta del sistema auditado.")
        sys.exit(1)

    with open(ruta, "r", encoding="utf-8") as archivo:
        return archivo.read().split("\n")


def es_comentario(linea):
    """Evita reportar evidencia que este dentro de un comentario."""
    return linea.strip().startswith("#")


def crear_hallazgo(consecutivo, regla, linea, evidencia):
    """Arma el diccionario de un hallazgo con los 8 campos del enunciado."""
    return {
        "id": "A%02d" % consecutivo,
        "categoria": regla["categoria"],
        "linea": linea,
        "evidencia": evidencia,
        "hallazgo": regla["descripcion"],
        "riesgo": regla["riesgo"],
        "severidad": regla["severidad"],
        "recomendacion": regla["recomendacion"],
    }


# ----------------------------------------------------------------------
# MOTOR DE ANALISIS
# ----------------------------------------------------------------------

def analizar_por_linea(lineas, consecutivo):
    """Aplica las reglas que buscan un patron presente en una linea."""
    hallazgos = []

    for numero, linea in enumerate(lineas, start=1):
        if es_comentario(linea):
            continue

        for regla in REGLAS_DE_LINEA:
            if re.search(regla["patron"], linea):
                hallazgos.append(
                    crear_hallazgo(consecutivo, regla, str(numero), linea.strip())
                )
                consecutivo += 1

    return hallazgos, consecutivo


def analizar_archivo_completo(lineas, consecutivo):
    """Aplica las reglas que verifican la AUSENCIA de un control."""
    hallazgos = []
    codigo = "\n".join(lineas)

    for regla in REGLAS_DE_ARCHIVO:
        if not re.search(regla["patron"], codigo):
            hallazgos.append(
                crear_hallazgo(consecutivo, regla, "General", regla["evidencia"])
            )
            consecutivo += 1

    return hallazgos, consecutivo


def auditar(ruta):
    """Ejecuta la auditoria completa y devuelve la lista de hallazgos."""
    lineas = leer_codigo(ruta)

    hallazgos, consecutivo = analizar_por_linea(lineas, 1)
    hallazgos_generales, consecutivo = analizar_archivo_completo(lineas, consecutivo)
    hallazgos = hallazgos + hallazgos_generales

    return lineas, hallazgos


# ----------------------------------------------------------------------
# PRESENTACION DE RESULTADOS
# ----------------------------------------------------------------------

def imprimir_encabezado(ruta, total_lineas):
    print("=" * ANCHO)
    print("HERRAMIENTA AUTOMATIZADA DE AUDITORIA - SISTEMA DE MATRICULAS".center(ANCHO))
    print("=" * ANCHO)
    print("Archivo auditado : " + os.path.basename(ruta))
    print("Ruta             : " + os.path.abspath(ruta))
    print("Lineas analizadas: " + str(total_lineas))
    print("Fecha y hora     : " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print("Tipo de analisis : estatico (lectura de texto, sin ejecutar el sistema)")
    print("=" * ANCHO)


def imprimir_hallazgos(hallazgos):
    """Muestra los hallazgos agrupados por categoria."""
    categorias = []
    for hallazgo in hallazgos:
        if hallazgo["categoria"] not in categorias:
            categorias.append(hallazgo["categoria"])

    for categoria in categorias:
        print("")
        print("-" * ANCHO)
        print("CATEGORIA: " + categoria.upper())
        print("-" * ANCHO)

        for hallazgo in hallazgos:
            if hallazgo["categoria"] != categoria:
                continue
            print("")
            print("[" + hallazgo["id"] + "]  Linea " + hallazgo["linea"] +
                  "   |   Severidad: " + hallazgo["severidad"])
            print("   Evidencia      : " + hallazgo["evidencia"])
            print("   Hallazgo       : " + hallazgo["hallazgo"])
            print("   Riesgo         : " + hallazgo["riesgo"])
            print("   Recomendacion  : " + hallazgo["recomendacion"])


def imprimir_resumen(hallazgos):
    altas = 0
    medias = 0
    bajas = 0
    por_categoria = {}

    for hallazgo in hallazgos:
        if hallazgo["severidad"] == "Alta":
            altas += 1
        elif hallazgo["severidad"] == "Media":
            medias += 1
        else:
            bajas += 1

        categoria = hallazgo["categoria"]
        por_categoria[categoria] = por_categoria.get(categoria, 0) + 1

    print("")
    print("=" * ANCHO)
    print("RESUMEN DE LA AUDITORIA AUTOMATICA".center(ANCHO))
    print("=" * ANCHO)
    print("Total de posibles hallazgos: " + str(len(hallazgos)))
    print("Severidad Alta : " + str(altas))
    print("Severidad Media: " + str(medias))
    print("Severidad Baja : " + str(bajas))
    print("")
    print("Hallazgos por categoria:")
    for categoria in por_categoria:
        print("   - " + categoria + ": " + str(por_categoria[categoria]))
    print("")
    print("NOTA: cada linea reportada es un POSIBLE hallazgo. La herramienta apoya")
    print("el analisis y no reemplaza el criterio del auditor; la confirmacion del")
    print("riesgo requiere la lectura manual del codigo.")
    print("=" * ANCHO)


def exportar_csv(hallazgos, ruta_salida):
    with open(ruta_salida, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo, delimiter=";")
        escritor.writerow(["ID", "Categoria", "Linea", "Evidencia", "Hallazgo",
                           "Riesgo", "Severidad", "Recomendacion"])
        for h in hallazgos:
            escritor.writerow([h["id"], h["categoria"], h["linea"], h["evidencia"],
                               h["hallazgo"], h["riesgo"], h["severidad"],
                               h["recomendacion"]])
    print("Matriz exportada a: " + ruta_salida)


def exportar_txt(hallazgos, ruta_salida):
    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        archivo.write("REPORTE DE AUDITORIA AUTOMATICA\n")
        archivo.write("Generado: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + "\n\n")
        for h in hallazgos:
            archivo.write("[" + h["id"] + "] " + h["categoria"] +
                          " | Linea " + h["linea"] + " | " + h["severidad"] + "\n")
            archivo.write("  Evidencia    : " + h["evidencia"] + "\n")
            archivo.write("  Hallazgo     : " + h["hallazgo"] + "\n")
            archivo.write("  Riesgo       : " + h["riesgo"] + "\n")
            archivo.write("  Recomendacion: " + h["recomendacion"] + "\n\n")
    print("Reporte exportado a: " + ruta_salida)


# ----------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ----------------------------------------------------------------------

def main():
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        carpeta = os.path.dirname(os.path.abspath(__file__))
        ruta = os.path.join(carpeta, ARCHIVO_POR_DEFECTO)

    lineas, hallazgos = auditar(ruta)

    imprimir_encabezado(ruta, len(lineas))
    imprimir_hallazgos(hallazgos)
    imprimir_resumen(hallazgos)

    carpeta_salida = os.path.dirname(os.path.abspath(ruta))
    exportar_csv(hallazgos, os.path.join(carpeta_salida, REPORTE_CSV))
    exportar_txt(hallazgos, os.path.join(carpeta_salida, REPORTE_TXT))


if __name__ == "__main__":
    main()

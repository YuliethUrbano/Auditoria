import tkinter as tk

estudiantes = []

def registrar_estudiante():
    nombre = entrada_nombre.get()
    documento = entrada_documento.get()
    edad = entrada_edad.get()
    programa = entrada_programa.get()

    estudiante = {
        "nombre": nombre,
        "documento": documento,
        "edad": edad,
        "programa": programa
    }

    estudiantes.append(estudiante)

    mensaje.config(text="Estudiante registrado correctamente")

def mostrar_estudiantes():
    resultado = ""

    for estudiante in estudiantes:
        resultado = resultado + estudiante["nombre"] + " - " + estudiante["programa"] + "\n"

    mensaje.config(text=resultado)

def eliminar_estudiante():
    documento = entrada_documento.get()

    for estudiante in estudiantes:
        if estudiante["documento"] == documento:
            estudiantes.remove(estudiante)

    mensaje.config(text="Proceso terminado")

def calcular_edad_academica():
    edad = int(entrada_edad.get())

    if edad >= 18:
        mensaje.config(text="Estudiante mayor de edad")
    else:
        mensaje.config(text="Estudiante menor de edad")

def guardar_datos():
    archivo = open("estudiantes.txt", "w")

    for estudiante in estudiantes:
        archivo.write(str(estudiante) + "\n")

    mensaje.config(text="Información guardada")


ventana = tk.Tk()
ventana.title("Sistema de Matrículas")
ventana.geometry("500x400")

tk.Label(ventana, text="Nombre").pack()
entrada_nombre = tk.Entry(ventana)
entrada_nombre.pack()

tk.Label(ventana, text="Documento").pack()
entrada_documento = tk.Entry(ventana)
entrada_documento.pack()

tk.Label(ventana, text="Edad").pack()
entrada_edad = tk.Entry(ventana)
entrada_edad.pack()

tk.Label(ventana, text="Programa").pack()
entrada_programa = tk.Entry(ventana)
entrada_programa.pack()

tk.Button(ventana, text="Registrar", command=registrar_estudiante).pack()
tk.Button(ventana, text="Mostrar estudiantes", command=mostrar_estudiantes).pack()
tk.Button(ventana, text="Eliminar", command=eliminar_estudiante).pack()
tk.Button(ventana, text="Calcular edad", command=calcular_edad_academica).pack()
tk.Button(ventana, text="Guardar", command=guardar_datos).pack()

mensaje = tk.Label(ventana, text="")
mensaje.pack()

ventana.mainloop()
Sistema de Inventario UNISON — Flask + SQLite

Proyecto Final de la materia de Desarrollo de Sistemas IV
Universidad de Sonora — Departamento de Ingeniería Industrial
Autor: Caleb Romo

📝 Descripción del Proyecto

Este sistema web permite la gestión de inventarios de una organización educativa.
Soporta administración de Productos y Almacenes, con control de acceso por roles y registro de auditoría.

📍 Diseñado con la identidad visual de la UNISON
📍 CRUD completo con interfaz moderna usando Bootstrap y JS
📍 Seguridad mediante login + roles con sesiones
📍 Auditoría automática de cambios en la base de datos
📍 Filtros en tiempo real para búsqueda avanzada

🚀 Tecnologías utilizadas
Categoría	Tecnología
Backend	Python 3 + Flask
Base de datos	SQLite3
Frontend	HTML5, CSS3, Bootstrap 5, JavaScript Fetch API
Gestión de acceso	Flask Session + Roles
Hash de contraseñas	MD5 (proyecto escolar)
🔐 Control de acceso y roles
Usuario	Rol	Permisos
ADMIN	ADMIN	CRUD en Productos y Almacenes
PRODUCTOS	PRODUCTOS	CRUD solo Productos
ALMACENES	ALMACENES	CRUD solo Almacenes

Las credenciales iniciales se generan automáticamente al iniciar la app.

📊 Funcionalidades principales

Login con validación y auditoría de inicio de sesión

Panel principal con navegación simplificada

Tablas con filtro dinámico por columnas

CRUD mediante modales y AJAX

Toasts de confirmación en acciones exitosas

Protección a rutas según rol del usuario

Organización del código en estructura limpia de carpetas

Estructura del Proyecto
<img width="975" height="1016" alt="image" src="https://github.com/user-attachments/assets/b84a5adb-e659-497f-ac85-3da2965cae78" />

⚙️ Instalación y ejecución
Requisitos previos:

✔ Python 3.x
✔ pip

Pasos:
# Clonar el repositorio
git clone https://github.com/usuario/inventario-unison.git
cd inventario-unison

# Instalar dependencias
pip install flask

# Ejecutar aplicación
python app.py


La aplicación estará disponible en:
👉 http://127.0.0.1:5000

📌 Base de datos

La base InventarioBD_2.db se inicializa automáticamente.
Se agregan columnas de auditoría si no existen.

Puedes editarla usando DB Browser for SQLite.

📸 Capturas (agrega las tuyas)
Pantalla	Vista
Login	[Agregar imagen]
Productos	[Agregar imagen]
Almacenes	[Agregar imagen]
Modales CRUD + Toasts	[Agregar imagen]

⚠️ Recomendado: sube las imágenes al repo y reemplaza con URL de GitHub.

🔍 Auditoría automática de cambios

La BD registra:

✔ Fecha de creación
✔ Última modificación
✔ Usuario que realizó el cambio

Esto permite trazabilidad completa del inventario.

🧠 Aprendizajes del proyecto

Integración frontend–backend con Fetch API

Control de acceso profesional con roles de usuario

Mejores prácticas de organización en Flask

Experiencia construyendo UI accesible y responsiva

Trazabilidad y auditoría de datos en bases SQL

📜 Licencia

Este proyecto es educativo y sin fines de lucro.
Puedes reutilizarlo como ejemplo para aprendizaje personal.

📮 Contacto

🧑‍💻 Autor: Caleb Romo
✉️ Email: a222200419@unison.mx
🔗 GitHub: klep98


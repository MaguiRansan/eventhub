# Imagen base oficial con Python 3.11 slim para reducir tamaño
FROM python:3.11-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos solo los archivos necesarios para instalar dependencias primero
COPY requirements.txt .

# Instalamos dependencias del sistema necesarias (apt) y luego las de Python
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiamos el resto del proyecto
COPY . .

# Variables de entorno para evitar creación de archivos .pyc y activar modo no interactivo
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Ejecutamos las migraciones de la base de datos
# Es importante que esto se haga después de copiar el resto del proyecto,
# ya que las migraciones dependen del código de tu aplicación.
RUN python manage.py makemigrations
RUN python manage.py migrate

# Comando para ejecutar el servidor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
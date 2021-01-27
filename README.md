Basic

1. Crear entorno virtual en Python

2. activar entorno virtual

3. Intslar requerimiento

$ pip install -r requirements.txt

4. Instalar Docker

5. Ejecutar

$ docker run --name some-postgres -p 5432:5432 -e POSTGRES_USER=taxi -e POSTGRES_DB=taxi -e POSTGRES_PASSWORD=taxi -d postgres

$ docker run --name some-redis -p 6379:6379 -d redis

Comprobar la conexipon con Redis

$ docker exec -it some-redis redis-cli ping

Exportar variables de entorno

$ export PGDATABASE=taxi
$ export PGUSER=taxi
$ export PGPASSWORD=taxi

6. levantar proyecto

$ python manage.py runserver
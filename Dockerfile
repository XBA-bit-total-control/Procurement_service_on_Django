FROM python:3.13

WORKDIR /purchasing_service

COPY requirements-dev.txt .

RUN pip install -r requirements.txt

COPY . .

RUN chmod +x migrate.sh

WORKDIR /purchasing_service/purchasing_service

ENTRYPOINT ["../migrate.sh"]

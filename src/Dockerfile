FROM python:3.8-alpine
ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD bash -c "python manage.py makemigrations && python manage.py migrate && gunicorn --workers=3 AssetStorm.wsgi -b 0.0.0.0:8080"
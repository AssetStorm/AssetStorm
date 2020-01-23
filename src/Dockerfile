FROM python:3.8-alpine
ENV PYTHONUNBUFFERED 1
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev bash py-gunicorn
RUN pip install --upgrade pip && pip install psycopg2

RUN mkdir /code
WORKDIR /code

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8081

CMD bash -c "./startup.sh"
# syntax=docker/dockerfile:1

FROM python:3.11-slim

ARG APP_PORT

WORKDIR /bia-dashboard

RUN apt update

RUN apt install -y libexpat1

COPY . .

RUN pip install --upgrade pip

RUN ldconfig

RUN pip install -r requirements.txt

ENV FLASK_APP=/bia-dashboard/src/app.py

EXPOSE ${APP_PORT}

CMD ["python", "/bia-dashboard/src/app.py"]
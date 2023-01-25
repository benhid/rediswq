FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY ./worker.py worker.py

COPY ./rediswq.py rediswq.py

CMD [ "python3", "worker.py" ]

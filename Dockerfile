FROM python:3.11-bookworm

WORKDIR /usr/app/src

COPY ./requirements.txt /usr/app/src/requirements.txt

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
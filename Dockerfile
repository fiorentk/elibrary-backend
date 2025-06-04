FROM python:3.12.2

ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/.

CMD ["python3","main.py"]
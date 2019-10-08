FROM python:3

RUN pip3 --no-cache-dir install --upgrade \
    pip \
    pipenv

COPY Pipfile .
COPY Pipfile.lock .

RUN pipenv install --system --deploy

COPY handler.py .

CMD ["python", "handler.py"]

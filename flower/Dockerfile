FROM mher/flower

USER root

RUN mkdir /code
WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt 

COPY ./tasks.py /code/tasks.py

RUN chown flower:flower /code/tasks.py

CMD ["sh", "-c", "celery -A tasks flower --inspect_timeout=3000 --max_tasks=1000000 --max_workers=5000 --purge_offline_workers=86400"]

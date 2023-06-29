FROM python:3.9-alpine3.18

RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add --no-cache mariadb-dev git
RUN python -m pip install --upgrade pip wheel setuptools

WORKDIR /idkchat
COPY . .
RUN pip install -r requirements.txt

RUN apk del build-deps
RUN rm -r /root/.cache

EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=idkchat.settings

RUN ["chmod", "+x", "./entrypoint.sh"]

ENTRYPOINT ["./entrypoint.sh"]
CMD [""]
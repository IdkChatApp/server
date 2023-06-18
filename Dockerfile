FROM python:3.9-alpine3.18

RUN python -m pip install --upgrade pip wheel setuptools

WORKDIR /idkchat
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=idkchat.settings

ENTRYPOINT ["./entrypoint.sh"]
CMD [""]
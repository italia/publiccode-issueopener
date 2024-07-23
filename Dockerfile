FROM python:3.12-slim as build

WORKDIR /app

RUN addgroup --system app && adduser --system --home /home/app --group app

USER app

COPY requirements.txt .
COPY templates/ templates/
COPY main.py .

RUN pip install -r requirements.txt

CMD ["./main.py", "--dry-run"]

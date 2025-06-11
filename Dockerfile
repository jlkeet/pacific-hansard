FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pipelines.py .
COPY pipelines_enhanced.py .

CMD ["python", "pipelines_enhanced.py"]

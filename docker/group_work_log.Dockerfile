FROM python:3.12-alpine

WORKDIR /app

COPY ../group_work_log /app
COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN chmod +x run.py

EXPOSE 8000
ENTRYPOINT ["python", "run.py", "--port", "8000"]

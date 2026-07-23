FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
# functions-framework discovers the CloudEvent entry point below.
ENV FUNCTION_TARGET=handle_event
ENV FUNCTION_SIGNATURE_TYPE=cloudevent
CMD ["functions-framework", "--target=handle_event", "--signature-type=cloudevent", "--port=8080", "--source=src/main.py"]

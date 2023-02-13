FROM python:3.9-slim
WORKDIR /bot_57
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
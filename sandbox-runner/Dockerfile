FROM docker:27-cli

RUN apk add --no-cache python3 py3-pip git

WORKDIR /runner

COPY requirements.txt .

RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY runner.py .

EXPOSE 8000

CMD ["python3", "runner.py"]

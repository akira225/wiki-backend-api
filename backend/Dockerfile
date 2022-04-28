FROM python3:latest

WORKDIR /app

copy . .

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ['python', 'main.py']
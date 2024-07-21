FROM python:3.10
WORKDIR /soc_credit_tgbot
COPY . /soc_credit_tgbot
RUN pip install -r requirements.txt
CMD ["python", "./bot.py"]
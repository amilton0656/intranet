import smtplib
import email.message
from dotenv import load_dotenv
import os

load_dotenv()

def enviar_email():
    corpo_email = """
    <p>Parágrafo 00000 </p>

"""

    msg = email.message.Message()
    msg['Subject'] = "Assunto"
    msg['From'] = "amilton0656@gmail.com"
    msg['To'] = "amilton0656@gmail.com"
    password = os.getenv("EMAIL_HOST_PASSWORD")
    msg.add_header('Content-Type', 'text/html')
    msg.set_payload(corpo_email)

    s = smtplib.SMTP('smtp.gmail.com: 587')
    s.starttls()
    s.login(msg['From'], password)
    s.sendmail(msg['From'], [msg['To']], msg.as_string().encode('utf-8'))
    print('Email enviado')


enviar_email()
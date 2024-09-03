import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def _send_email(
    _subject: str,
    _body: str,
    _print_function,
    _contact: str,
    _sender_email: str,
    _sender_email_pwd: str):
  _sender_email_address = _sender_email
  _sender_pwd = _sender_email_pwd
  _receiver_email_address = _contact
  
  _msg = MIMEText(_body)
  _msg['Subject'] = _subject
  _msg['From'] = _sender_email_address
  _msg['To'] = _receiver_email_address
  with smtplib.SMTP_SSL('smtp.gmail.com', 465) as _smtp_server:
    _smtp_server.login(_sender_email_address, _sender_pwd)
    _smtp_server.sendmail(_sender_email_address, _receiver_email_address, _msg.as_string())
  _print_function(f'Email sent to {_receiver_email_address}')
  
def _timer_email(MINUTES, _email_address, _email_pwd):
  '''
  Sends an email to the user, from the user's own email address, on a timer.
  '''
  import time
  _sender_email_address = _email_address
  _sender_pwd = _email_pwd
  _receiver_email_address = _email_address
  
  _msg = MIMEText(f'Timer Done\n\n{time.asctime()}')
  _msg['Subject'] = f"Timer - ({MINUTES} minute(s))"
  _msg['From'] = _sender_email_address
  _msg['To'] = _receiver_email_address
  with smtplib.SMTP_SSL('smtp.gmail.com', 465) as _smtp_server:
    _smtp_server.login(_sender_email_address, _sender_pwd)
    _smtp_server.sendmail(_sender_email_address, _receiver_email_address, _msg.as_string())
"""Envio de notificação por e-mail.

A senha do servidor SMTP era `'senha123'`, literal num atributo de classe. Agora
as credenciais são INJETADAS: quem monta a aplicação decide de onde elas vêm, e a
classe passa a ser testável sem servidor de e-mail real.
"""
import smtplib

from utils.tempo import agora_utc


class NotificationService:
    def __init__(self, host, port, user, password, transporte=smtplib.SMTP):
        self.notifications = []
        self.email_host = host
        self.email_port = port
        self.email_user = user
        self._email_password = password
        self._transporte = transporte

    @property
    def configurado(self) -> bool:
        return bool(self.email_user and self._email_password)

    def send_email(self, to, subject, body) -> bool:
        if not self.configurado:
            print("Envio de e-mail desativado: EMAIL_USER/EMAIL_PASSWORD não definidos")
            return False
        try:
            server = self._transporte(self.email_host, self.email_port)
            server.starttls()
            server.login(self.email_user, self._email_password)
            server.sendmail(self.email_user, to, f"Subject: {subject}\n\n{body}")
            server.quit()
            return True
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
            return False

    def notify_task_assigned(self, user, task):
        self.send_email(
            user.email, f"Nova task atribuída: {task.title}",
            f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
            f"Prioridade: {task.priority}\nStatus: {task.status}")
        self.notifications.append({'type': 'task_assigned', 'user_id': user.id,
                                   'task_id': task.id, 'timestamp': agora_utc()})

    def notify_task_overdue(self, user, task):
        self.send_email(
            user.email, f"Task atrasada: {task.title}",
            f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\n"
            f"Data limite: {task.due_date}")

    def get_notifications(self, user_id):
        return [n for n in self.notifications if n['user_id'] == user_id]

from celery import shared_task
from users.models import UserAccount
from graphql_auth.settings import graphql_auth_settings as app_settings
from graphql_auth.models import UserStatus, TokenAction
from graphql_auth.utils import get_token
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


@shared_task(bind=True)
def graphql_auth_async_email(func, *args):
    """
    Task to send an e-mail for the graphql_auth package
    """

    return func(*args)


@shared_task
def send_activation_email(user_id, *args, **kwargs):
    """
    Task to send an activation email for the graphql_auth package

    :param user_id: The user id
    :param info: The graphql info
    :param args: The args
    :param kwargs: The kwargs
    """

    user = UserAccount.objects.get(pk=user_id)
    user_status = UserStatus.objects.get(user=user)

    token = get_token(user_status.user, TokenAction.ACTIVATION, **kwargs)

    site = kwargs.get("site", None)
    email_context = {
        "user": user_status.user,
        "token": token,
        "port": kwargs.get("port", None),
        "site_name": site.name,
        "domain": site.domain,
        "protocol": "https" if kwargs.get("is_secure", False) else "http",
        "path": app_settings.ACTIVATION_PATH_ON_EMAIL,
    }
    template = app_settings.EMAIL_TEMPLATE_ACTIVATION
    subject = app_settings.EMAIL_SUBJECT_ACTIVATION

    print("send_activation_email", subject, *args, **kwargs)
    _subject = "Activate your TrayFoods account"
    html_message = render_to_string(template, email_context)
    message = strip_tags(html_message)

    send_mail(
        subject=_subject,
        from_email=app_settings.EMAIL_FROM,
        message=message,
        html_message=html_message,
        recipient_list=([getattr(user_status.user, UserAccount.EMAIL_FIELD)]),
        fail_silently=False,
    )

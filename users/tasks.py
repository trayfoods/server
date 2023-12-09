from celery import shared_task


@shared_task(bind=True)
def graphql_auth_async_email(func, *args):
    """
    Task to send an e-mail for the graphql_auth package
    """

    return func(*args)


@shared_task
def send_activation_email(*args, **kwargs):
    """
    Task to send an e-mail for the graphql_auth package
    """
    from graphql_auth.models import UserStatus

    return UserStatus.send_activation_email(*args, **kwargs)

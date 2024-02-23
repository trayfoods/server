import threading
from typing import Optional
from firebase_admin import messaging


class FCMThread(threading.Thread):
    """
    :param title: Title of notification
    :param msg: Message or body of notification
    :param tokens: Tokens of the users who will receive this notification
    :param data: A dictionary of data fields (optional). All keys and values in the dictionary must be strings.
    :return -> None:
    """

    def __init__(
        self: threading.Thread,
        title: str,
        msg: str,
        tokens: list,
        image: str = None,
        data: Optional[list] = None,
    ) -> None:
        self.title = title
        self.msg = msg
        self.tokens = tokens
        self.image = image
        self.data = data
        threading.Thread.__init__(self)

    def _push_notification(self):
        """
        Push notification messages by chunks of 500.
        """
        chunks = [self.tokens[i : i + 500] for i in range(0, len(self.tokens), 500)]
        for chunk in chunks:
            messages = [
                messaging.Message(
                    notification=messaging.Notification(
                        self.title, self.msg, self.image
                    ),
                    token=token,
                    data=self.data,
                )
                for token in chunk
            ]
            response = messaging.send_all(messages)
            print(response)
            print(
                f"Number of successful notifications: {response._success_count}"
            )
            print(
                f"Number of failed notifications: {len(messages) - response._success_count}"
            )

    def run(self):
        self._push_notification()

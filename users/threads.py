import threading
from typing import Optional
from firebase_admin import messaging


class FCMThread(threading.Thread):
    """
    :param title: Title of notification
    :param message: Message or body of notification
    :param tokens: Tokens of the users who will receive this notification
    :param data: A dictionary of data fields (optional). All keys and values in the dictionary must be strings.
    :return -> None:
    """

    def __init__(
        self: threading.Thread,
        title: str,
        message: str,
        tokens: list,
        image: str = None,
        data: Optional[list] = None,
    ) -> None:
        self.title = title
        self.message = message
        self.tokens = tokens
        self.image = image
        self.sound = "defaultNotificationSound.wav"
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
                        self.title, self.message, self.image, self.sound
                    ),
                    token=token,
                    data=self.data,
                )
                for token in chunk
            ]
            messaging.send_all(messages)

    def run(self):
        self._push_notification()

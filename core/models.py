import uuid
from django.db import models


class UUIDModelMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = uuid.uuid4()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.id)

    def natural_key(self):
        return (self.id,)

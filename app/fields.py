from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


class EncryptedCharField(models.Field):
    def __init__(self, *args, **kwargs):
        self.max_length = kwargs.get('max_length', 255)
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'TextField'  

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return self.decrypt(value)
        except InvalidToken:
          
            return value

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            try:
                return self.decrypt(value)
            except InvalidToken:
                return value
        return value

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encrypt(value)

    def encrypt(self, value):
        f = Fernet(settings.ENCRYPTION_KEY)
        encrypted = f.encrypt(value.encode())
        return encrypted.decode()

    def decrypt(self, value):
        f = Fernet(settings.ENCRYPTION_KEY)
        decrypted = f.decrypt(value.encode())
        return decrypted.decode()

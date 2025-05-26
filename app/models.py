from django.db import models
from django.utils import timezone
import uuid
from typing import Dict
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError
from decimal import Decimal
import qrcode
import base64
from io import BytesIO
from .fields import EncryptedCharField
from django.contrib import messages
from django.shortcuts import redirect


class User(AbstractUser):
    is_organizer = models.BooleanField(default=False)

    @classmethod
    def validate_new_user(cls, email, username, password, password_confirm):
        errors = {}

        if email is None:
            errors["email"] = "El email es requerido"
        elif User.objects.filter(email=email).exists():
            errors["email"] = "Ya existe un usuario con este email"

        if username is None:
            errors["username"] = "El username es requerido"
        elif User.objects.filter(username=username).exists():
            errors["username"] = "Ya existe un usuario con este nombre de usuario"

        if password is None or password_confirm is None:
            errors["password"] = "Las contraseñas son requeridas"
        elif password != password_confirm:
            errors["password"] = "Las contraseñas no coinciden"

        return errors


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def clean(self):
        self.name = self.name.strip()
        self.description = self.description.strip()

class Venue(models.Model):
    name = models.CharField("Nombre", max_length=100)
    address = models.CharField("Dirección", max_length=200)
    city = models.CharField("Ciudad", max_length=100)
    capacity = models.PositiveIntegerField("Capacidad")
    contact = models.TextField("Información de contacto")
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_at = models.DateTimeField()
    organizer = models.ForeignKey('User', on_delete=models.CASCADE, related_name="organized_events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    categories = models.ManyToManyField(Category, blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)

    general_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    vip_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    general_tickets_total = models.PositiveIntegerField(default=0)
    general_tickets_available = models.PositiveIntegerField(default=0)
    vip_tickets_total = models.PositiveIntegerField(default=0)
    vip_tickets_available = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    @property
    def formatted_date(self):
        days = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        date = timezone.localtime(self.scheduled_at)
        return f"{days[date.weekday()]} {date.day} de {months[date.month - 1]} del {date.year} "

    @property
    def is_sold_out(self):
        return self.general_tickets_available == 0 and self.vip_tickets_available == 0

    def get_available_tickets(self, ticket_type):
        if ticket_type == Ticket.TicketType.GENERAL:
            return self.general_tickets_available
        elif ticket_type == Ticket.TicketType.VIP:
            return self.vip_tickets_available
        return 0

    @classmethod
    def validate(cls, title, description, scheduled_at, general_tickets=None, vip_tickets=None):
        errors = {}
        if not title:
            errors["title"] = "Por favor ingrese un titulo"
        if not description:
            errors["description"] = "Por favor ingrese una descripcion"
        if not scheduled_at or scheduled_at < timezone.now():
            errors["scheduled_at"] = "La fecha del evento debe ser en el futuro"
        if general_tickets is not None and general_tickets < 0:
            errors["general_tickets"] = "Ingrese una cantidad válida de tickets generales"
        if vip_tickets is not None and vip_tickets < 0:
            errors["vip_tickets"] = "Ingrese una cantidad válida de tickets VIP"
        return errors

    @classmethod
    def new(cls, title, description, scheduled_at, organizer, venue=None, categories=None,
            general_price=Decimal('0.00'), vip_price=Decimal('0.00'),
            general_tickets=0, vip_tickets=0):
        errors = cls.validate(title, description, scheduled_at, general_tickets, vip_tickets)
        if len(errors.keys()) > 0:
            return False, errors

        event = cls.objects.create(
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            organizer=organizer,
            venue=venue,
            general_price=general_price,
            vip_price=vip_price,
            general_tickets_total=general_tickets,
            general_tickets_available=general_tickets,
            vip_tickets_total=vip_tickets,
            vip_tickets_available=vip_tickets
        )
        if categories:
            event.categories.set(categories)
        return True, event

    def update(self, title=None, description=None, scheduled_at=None, organizer=None,
               general_price=None, vip_price=None, general_tickets=None, vip_tickets=None,
               venue=None, categories=None):
        self.title = title or self.title
        self.description = description or self.description
        self.scheduled_at = scheduled_at or self.scheduled_at
        self.organizer = organizer or self.organizer
        self.venue = venue or self.venue

        if general_price is not None:
            self.general_price = general_price
        if vip_price is not None:
            self.vip_price = vip_price
        if general_tickets is not None:
            diff = general_tickets - self.general_tickets_total
            self.general_tickets_total = general_tickets
            self.general_tickets_available += diff
        if vip_tickets is not None:
            diff = vip_tickets - self.vip_tickets_total
            self.vip_tickets_total = vip_tickets
            self.vip_tickets_available += diff

        self.save()

        if categories is not None:
            self.categories.set(categories)

        return self

class Rating(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    comment = models.TextField(blank=True, null=True)
    score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
    def __str__(self):
        return f"{self.user.username} - {self.score} estrellas"

class Ticket(models.Model):
    class TicketType(models.TextChoices):
        GENERAL = 'GENERAL', 'General'
        VIP = 'VIP', 'VIP'

    buy_date = models.DateTimeField(auto_now_add=True)
    ticket_code = models.CharField(max_length=100, unique=True)
    quantity = models.PositiveIntegerField(default=1)
    type = models.CharField(max_length=7, choices=TicketType.choices, default=TicketType.GENERAL)
    is_used = models.BooleanField(default=False)
    payment_confirmed = models.BooleanField(default=False)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    taxes = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name="tickets")
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name="tickets")

    def __str__(self):
        type_map = {'GENERAL': 'General', 'VIP': 'VIP'}
        return f"{type_map.get(self.type, self.type)} Ticket - {self.event.title} (x{self.quantity})"

    def qr_code_base64(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(self.ticket_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffered = BytesIO()
        img.save(buffered, "PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def clean(self):
        errors = {}
        if self.quantity <= 0:
            errors['quantity'] = 'La cantidad debe ser mayor a cero'
        if self.type == self.TicketType.VIP and self.quantity > 2:
            errors['type'] = 'Máximo 2 tickets VIP por compra'
        if self.pk and not self._is_within_edit_window():
            errors['buy_date'] = 'No se puede modificar después de 30 minutos de la compra'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.ticket_code:
            self.ticket_code = self._generate_ticket_code()
        self._calculate_pricing()
        if is_new:
            available = self.event.get_available_tickets(self.type)
            if available < self.quantity:
                raise ValidationError(f"No hay suficientes entradas {self.type.lower()} disponibles")
            if self.type == self.TicketType.GENERAL:
                self.event.general_tickets_available -= self.quantity
            else:
                self.event.vip_tickets_available -= self.quantity
            self.event.save()
        super().save(*args, **kwargs)

    def _generate_ticket_code(self):
        return f"{self.event.title[:4].upper()}-{uuid.uuid4().hex[:8]}"

    def _calculate_pricing(self):
        price = self.event.general_price if self.type == self.TicketType.GENERAL else self.event.vip_price
        self.subtotal = price * Decimal(self.quantity)
        self.taxes = self.subtotal * Decimal('0.10')
        self.total = self.subtotal + self.taxes
        return self.total

    def _is_within_edit_window(self):
        return (timezone.now() - self.buy_date).total_seconds() <= 1800

    @property
    def is_refundable(self):
        return (not self.is_used and
                self._is_within_edit_window() and
                (self.event.scheduled_at - timezone.now()).days > 0)

    def can_be_modified_by(self, user):
        if user.is_organizer and user == self.event.organizer:
            return True
        return user == self.user and self._is_within_edit_window()

    def can_be_deleted_by(self, user):
        return self.can_be_modified_by(user)

    @classmethod
    def create_ticket(cls, user, event, quantity=1, ticket_type='GENERAL'):
        total_existentes = cls.objects.filter(user=user, event=event).aggregate(
            total=models.Sum('quantity'))['total'] or 0
        if total_existentes + quantity > 4:
            raise ValidationError("No podés comprar más de 4 entradas para este evento.")

        ticket = cls(user=user, event=event, quantity=quantity, type=ticket_type)
        if not ticket.ticket_code:
            ticket.ticket_code = ticket._generate_ticket_code()
        ticket.full_clean()
        ticket.save()
        return ticket




class PaymentInfo(models.Model):
    CARD_TYPE_CHOICES = [
        ('VISA', 'Visa'),
        ('MC', 'MasterCard'),
        ('AMEX', 'American Express'),
    ]

    user = models.ForeignKey('User', on_delete=models.CASCADE)
    card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES, default='VISA')
    card_number = EncryptedCharField(max_length=19)
    expiry_month = models.PositiveIntegerField()
    expiry_year = models.PositiveIntegerField()
    card_holder = models.CharField(max_length=100)
    cvv = EncryptedCharField(max_length=4)
    save_card = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def ___str___ (self):
        return f"{self.card_type} **** {self.card_number[-4:]}"

    @property
    def expiry_date(self):
        return f"{self.expiry_month:02d}/{str(self.expiry_year)[-2:]}"

    def clean(self):
        super().clean()

        if self.expiry_month and (self.expiry_month < 1 or self.expiry_month > 12):
            raise ValidationError({'expiry_month': 'Mes de expiración inválido (1-12)'})

        current_year = timezone.now().year
        if self.expiry_year and (self.expiry_year < current_year or self.expiry_year > current_year + 20):
            raise ValidationError({'expiry_year': 'Año de expiración inválido'})

class RefundRequest(models.Model):
    REASON_CHOICES = [
    ('Salud', 'Problemas de salud'),
    ('Emergencia Familiar', 'Emergencia familiar'),
    ('Trabajo', 'Compromisos laborales'),
    ('Transporte', 'Problemas de transporte'),
    ('Evento cancelado', 'El evento fue pospuesto o cancelado'),
    ('Otros', 'Otro motivo'),]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refund_requests")
    ticket_code = models.CharField(max_length=100)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details= models.TextField(blank=True)
    approved = models.BooleanField(null=True, default=None)
    approval_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def event(self):
        from .models import Ticket
        ticket = Ticket.objects.get(ticket_code=self.ticket_code)
        return ticket.event

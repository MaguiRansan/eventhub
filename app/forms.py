import re
from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone

from .models import Category, Event, PaymentInfo, Rating, RefundRequest, Ticket, Venue


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['title', 'score', 'comment']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)

def clean(self):
    cleaned_data = super().clean()
    title = cleaned_data.get('title', '').strip()
    comment = cleaned_data.get('comment', '').strip()
    score = cleaned_data.get('score')

    if not title:
        self.add_error('title', "El título no puede estar vacío.")
    if not comment:
        self.add_error('comment', "El comentario no puede estar vacío.")
    if not score:
        self.add_error('score', "Debe seleccionar una calificación.")

    if self.user and self.event:
        if Rating.objects.filter(user=self.user, event=self.event).exists():
            self.add_error(None, "Ya has calificado este evento.")

    return cleaned_data

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        labels = {
            'name': 'Nombre',
            'description': 'Descripción',
            'is_active': 'Activo',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        error_messages = {
            'name': {
                'required': 'Por favor, ingrese un nombre',
                'max_length': 'El nombre es demasiado largo',
                'min_length': 'El nombre es demasiado corto',
            },
            'description': {
                'required': 'Por favor, ingrese una descripción',
                'max_length': 'La descripción es demasiado extensa',
                'min_length': 'La descripción es muy corta',
            },
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        if not name:
            raise forms.ValidationError("El nombre no puede estar vacío o tener solo espacios")

        if len(name) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres")

        if len(name) > 100:
            raise forms.ValidationError("El nombre no puede tener más de 100 caracteres")

        qs = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ya existe una categoría con ese nombre")

        return name.capitalize()

    def clean_description(self):
        description = self.cleaned_data.get("description", "").strip()

        if not description:
            raise forms.ValidationError("La descripción no puede estar vacía o tener solo espacios")

        if len(description) < 10:
            raise forms.ValidationError("La descripción debe tener al menos 10 caracteres")

        if len(description) > 500:
            raise forms.ValidationError("La descripción no puede tener más de 500 caracteres")

        return description


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ['name', 'address', 'city', 'capacity', 'contact']
        labels = {
            'name': 'Nombre de la ubicación',
            'address': 'Dirección',
            'city': 'Ciudad',
            'capacity': 'Capacidad (número de personas)',
            'contact': 'Contacto',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Ej: Estadio Nacional',
                'class': 'form-control',
                'maxlength': '100'
            }),
            'address': forms.TextInput(attrs={
                'placeholder': 'Ej: Av. Grecia 2001',
                'class': 'form-control'
            }),
            'city': forms.TextInput(attrs={
                'placeholder': 'Ej: Santiago',
                'class': 'form-control',
                'maxlength': '100'
            }),
            'capacity': forms.NumberInput(attrs={
                'placeholder': 'Ej: 1000',
                'class': 'form-control'
            }),
            'contact': forms.Textarea(attrs={
                'placeholder': 'Ej: contacto@email.com o +54 911 12345678',
                'class': 'form-control',
                'rows': 3,
                'maxlength': '100'
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("El nombre de la ubicación es obligatorio.")
        if len(name) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        if not re.match(r"^[\w\s\-\']+$", name):
            raise ValidationError("El nombre solo puede contener letras, números, espacios, guiones y apóstrofes.")
        return name

    def clean_address(self):
        address = self.cleaned_data.get('address', '').strip()
        if not address:
            raise ValidationError("La dirección es obligatoria.")
        if len(address) < 5:
            raise ValidationError("La dirección es demasiado corta.")
        if not re.search(r'\d', address):
            raise ValidationError("La dirección debe incluir un número (ej. calle y número).")
        return address

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not city:
            raise ValidationError("La ciudad es obligatoria.")
        if len(city) < 3:
            raise ValidationError("La ciudad debe tener al menos 3 caracteres.")
        if not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúñÑ\s\-]+$", city):
            raise ValidationError("La ciudad solo puede contener letras, espacios y guiones.")
        return city

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity is None or capacity <= 0:
            raise ValidationError("La capacidad debe ser mayor que cero.")
        if capacity > 100000:
            raise ValidationError("La capacidad no puede superar las 100.000 personas.")
        return capacity

    def clean_contact(self):
        contact = self.cleaned_data.get('contact', '').strip()

        try:
            validate_email(contact)
            return contact
        except ValidationError:
            pass

        if re.match(r'^\+?\d[\d\s\-\(\)]{7,}$', contact):
            return contact

        raise ValidationError("El contacto debe ser un número de teléfono válido o una dirección de email.")

class EventForm(forms.ModelForm):
    scheduled_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Fecha del evento"
    )
    scheduled_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        label="Hora del evento"
    )

    class Meta:
        model = Event
        exclude = ['scheduled_at', 'organizer', 'general_tickets_available', 'vip_tickets_available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'venue': forms.Select(attrs={'class': 'form-control'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        venues = Venue.objects.all()
        if venues.exists():
            self.fields['venue'] = forms.ModelChoiceField(
                queryset=venues,
                widget=forms.Select(attrs={'class': 'form-control'})
            )
        else:
            self.fields['venue'] = forms.ChoiceField(
                choices=[('', 'No hay ubicaciones disponibles')],
                widget=forms.Select(attrs={'class': 'form-control', 'disabled': True})
            )

    def clean(self):
        cleaned_data = super().clean()
        venue = cleaned_data.get('venue')
        general_tickets = cleaned_data.get('general_tickets_total', 0) or 0
        vip_tickets = cleaned_data.get('vip_tickets_total', 0) or 0

        if venue and (general_tickets or vip_tickets):
            total = general_tickets + vip_tickets
            if total > venue.capacity:
                raise ValidationError(
                    f"La cantidad total de tickets ({total}) excede la capacidad del lugar ({venue.capacity})."
                )

        scheduled_date = cleaned_data.get('scheduled_date')
        scheduled_time = cleaned_data.get('scheduled_time')

        if scheduled_date and scheduled_time:
            try:
                event_dt = timezone.make_aware(datetime.combine(scheduled_date, scheduled_time))
                if event_dt < timezone.now():
                    self.add_error('scheduled_date', 'La fecha del evento no puede estar en el pasado')
            except (TypeError, ValueError):
                self.add_error('scheduled_date', 'Fecha u hora inválida')

        if general_tickets < 0:
            self.add_error('general_tickets_total', 'La cantidad de tickets generales no puede ser negativa')
        if vip_tickets < 0:
            self.add_error('vip_tickets_total', 'La cantidad de tickets VIP no puede ser negativa')
        if general_tickets == 0 and vip_tickets == 0:
            raise ValidationError('Debe haber al menos un ticket disponible (general o VIP)')

        return cleaned_data


class TicketForm(forms.ModelForm):
    accept_terms = forms.BooleanField(
        required=True,
        label="Acepto los términos y condiciones y la política de privacidad",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Ticket
        fields = ['type', 'quantity']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10,
            }),
        }

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean() or {}
        scheduled_date = cleaned_data.get('scheduled_date')
        scheduled_time = cleaned_data.get('scheduled_time')


        if scheduled_date and scheduled_time:
            try:

                naive_datetime = datetime.combine(scheduled_date, scheduled_time)

                event_datetime = timezone.make_aware(naive_datetime)


                print(f"Current time: {timezone.now()}")
                print(f"Event time: {event_datetime}")

                if event_datetime < timezone.now():
                    self.add_error('scheduled_date', 'La fecha del evento no puede estar en el pasado')

            except Exception as e:
                self.add_error(None, f"Error al procesar la fecha: {str(e)}")

        return cleaned_data
class PaymentForm(forms.ModelForm):
    expiry_date = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'MM/AA'})
    )

    class Meta:
        model = PaymentInfo
        fields = ['card_type', 'card_number', 'expiry_date', 'cvv', 'card_holder', 'save_card']
        widgets = {
            'card_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234 5678 9012 3456',
                'data-mask': '0000 0000 0000 0000'
            }),
            'cvv': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CVV',
                'data-mask': '0000'
            }),
            'card_holder': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre como aparece en la tarjeta'
            }),
            'card_type': forms.Select(attrs={'class': 'form-control'})
        }

    def clean_card_number(self):
        card_number = self.cleaned_data.get('card_number', '')
        if not card_number:
            raise ValidationError('Número de tarjeta requerido')

        card_number = card_number.replace(' ', '')
        if not card_number.isdigit() or len(card_number) not in (13, 15, 16):
            raise ValidationError('Número de tarjeta inválido')
        return card_number

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date', '')
        if not expiry_date:
            raise ValidationError('La fecha de expiración es requerida')

        expiry_date = expiry_date.strip()
        if not re.match(r'^(0[1-9]|1[0-2])/\d{2}$', expiry_date):
            raise ValidationError('Formato inválido. Use MM/AA (ej. 12/28)')

        try:
            month, year = map(int, expiry_date.split('/'))
            full_year = 2000 + year
            now = timezone.now()

            if full_year < now.year or (full_year == now.year and month < now.month):
                raise ValidationError('Tarjeta expirada')

            if full_year > now.year + 10:
                raise ValidationError(f'Año inválido. Máximo permitido: {now.year + 10}')

            self.cleaned_data['expiry_month'] = month
            self.cleaned_data['expiry_year'] = full_year

        except ValueError:
            raise ValidationError('Fecha inválida')

        return expiry_date

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.expiry_month = self.cleaned_data.get('expiry_month')
        instance.expiry_year = self.cleaned_data.get('expiry_year')
        if commit:
            instance.save()
        return instance

class TicketFilterForm(forms.Form):
    FILTER_CHOICES = (
        ('all', 'Todos los tickets'),
        ('upcoming', 'Eventos próximos'),
        ('past', 'Eventos pasados'),
        ('used', 'Tickets usados'),
        ('unused', 'Tickets no usados'),
    )
    filter_by = forms.ChoiceField(
        choices=FILTER_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class RefundRequestForm(forms.ModelForm):
    accept_policy = forms.BooleanField(
        label="Acepto la política de reembolso",
        error_messages={'required': 'Debes aceptar la política para enviar la solicitud.'}
    )

    details = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'placeholder': 'Detalles adicionales (opcional)'}),
        label='Detalles adicionales'
    )

    class Meta:
        model = RefundRequest
        fields = ['ticket_code', 'reason', 'details', 'accept_policy']
        widgets = {
            'ticket_code': forms.TextInput(attrs={'placeholder': 'Código de ticket'}),
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'ticket_code': 'Código de ticket *',
            'reason': 'Razón del reembolso *',
            'details': 'Detalles adicionales',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_ticket_code(self):
        ticket_code = self.cleaned_data.get('ticket_code')
        if not ticket_code:
            raise forms.ValidationError("El código de ticket es requerido.")

        try:
            ticket = Ticket.objects.get(ticket_code=ticket_code)
        except Ticket.DoesNotExist:
            raise forms.ValidationError(
                "El código de ticket no es válido o no está registrado."
            )

        requesting_user = self.user or (self.instance.user if self.instance.pk else None)

        if requesting_user and ticket.user != requesting_user:
            raise forms.ValidationError("Este ticket no te pertenece o no puedes solicitar un reembolso para él.")

        existing_processed_request = RefundRequest.objects.filter(
            ticket_code=ticket_code
        ).exclude(pk=self.instance.pk if self.instance.pk else 0).filter(
            approved__isnull=False
        )

        if existing_processed_request.exists():
            raise forms.ValidationError("Ya existe una solicitud de reembolso procesada para este ticket. No se pueden generar nuevas solicitudes.")

        existing_pending_request = RefundRequest.objects.filter(
            ticket_code=ticket_code
        ).exclude(pk=self.instance.pk if self.instance.pk else 0).filter(
            approved__isnull=True
        )
        if existing_pending_request.exists():
            raise forms.ValidationError("Ya existe una solicitud de reembolso pendiente para este ticket. Por favor, espera a que sea procesada o edita la existente.")

        user_pending_requests = RefundRequest.objects.filter(
            user=requesting_user,
            approved__isnull=True  
        ).exclude(pk=self.instance.pk if self.instance.pk else 0)

        if user_pending_requests.exists():
            pending_tickets = [req.ticket_code for req in user_pending_requests]
            raise forms.ValidationError(
                f"Ya tienes solicitudes de reembolso pendientes para los tickets: {', '.join(pending_tickets)}. "
                "Debes esperar a que sean procesadas antes de crear una nueva solicitud."
            )

        if ticket.is_used:
            raise forms.ValidationError("No se puede reembolsar un ticket que ya ha sido usado.")

        current_time = timezone.now()
        if ticket.event.scheduled_at < current_time:
            raise forms.ValidationError("No se puede solicitar un reembolso para un evento que ya ocurrió.")

        if not ticket.is_refundable:
            raise forms.ValidationError("Este ticket no es elegible para reembolso según nuestras políticas. (Ej. fuera de plazo permitido)")

        if (ticket.event.scheduled_at - current_time).total_seconds() < 48 * 3600:
            raise forms.ValidationError(
                "No puedes solicitar un reembolso con menos de 48 horas de anticipación al evento."
            )

        self._ticket = ticket
        return ticket_code

    def clean(self):
        cleaned_data = super().clean()
        if not hasattr(self, '_ticket'):
            return cleaned_data

        reason = cleaned_data.get('reason')
        details = cleaned_data.get('details')

        if reason == 'Otros' and not details:
            self.add_error('details', "Si la razón es 'Otro motivo', debes especificar detalles.")

        return cleaned_data

class RefundApprovalForm(forms.ModelForm):
    class Meta:
        model = RefundRequest
        fields = []

    approve = forms.BooleanField(required=False, label='Aprobar')
    reject = forms.BooleanField(required=False, label='Rechazar')

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('approve') and cleaned_data.get('reject'):
            raise forms.ValidationError("No puedes aprobar y rechazar al mismo tiempo.")
        if not cleaned_data.get('approve') and not cleaned_data.get('reject'):
            raise forms.ValidationError("Debes seleccionar una acción.")
        return cleaned_data

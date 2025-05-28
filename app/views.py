import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Sum
from django.core.exceptions import ValidationError
from decimal import Decimal
import qrcode
from io import BytesIO
import qrcode.constants
from django.db import transaction
from django.db import IntegrityError

from .models import Event, Ticket, User, PaymentInfo, Rating, Category, Venue, RefundRequest
from .forms import EventForm, TicketForm, PaymentForm, TicketFilterForm, RatingForm, CategoryForm, VenueForm, RefundRequestForm, RefundApprovalForm

def register(request):
    if request.method == "POST":
        email = request.POST.get("email")
        username = request.POST.get("username")
        is_organizer = request.POST.get("is-organizer") is not None
        password = request.POST.get("password")
        password_confirm = request.POST.get("password-confirm")

        errors = User.validate_new_user(email, username, password, password_confirm)

        if len(errors) > 0:
            return render(
                request,
                "accounts/register.html",
                {"errors": errors, "data": request.POST},
            )
        else:
            user = User.objects.create_user(
                email=email, username=username, password=password, is_organizer=is_organizer
            )
            login(request, user)
            return redirect("events")

    return render(request, "accounts/register.html", {})

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(
                request, "accounts/login.html", {"error": "Usuario o contraseña incorrectos"}
            )

        login(request, user)
        return redirect("events")

    return render(request, "accounts/login.html")

def home(request):
    return render(request, "home.html")

@login_required
def events(request):

    fecha = request.GET.get("fecha")
    categoria_id = request.GET.get("categoria")
    venue_id = request.GET.get("venue")
    mostrar_pasados = request.GET.get("mostrar_pasados", "false") == "true"

    events = Event.objects.all()

    if fecha:
        events = events.filter(scheduled_at__date=fecha)
    elif mostrar_pasados:
        events = events.filter(scheduled_at__lt=timezone.now())
    else:
        events = events.filter(scheduled_at__gte=timezone.now())

    if categoria_id:
        events = events.filter(categories__id=categoria_id)
    if venue_id:
        events = events.filter(venue_id=venue_id)

   
    return render(
        request,
        "app/events.html",
        {
            "events": events,
            "user_is_organizer": request.user.is_organizer,
            "categorias": Category.objects.all(),
            "venues": Venue.objects.all(),
        },
    )

@login_required
def event_detail(request, id):
    event = get_object_or_404(Event.objects.prefetch_related('ratings'), pk=id)
    
    user_is_organizer = event.organizer == request.user
    now = timezone.now()
    rating_to_edit = None
    rating_id = request.GET.get('rating_id') or request.POST.get('rating_id')
    event_has_started = event.scheduled_at <= now


    has_ticket = Ticket.objects.filter(event=event, user=request.user, payment_confirmed=True).exists()


    if rating_id:
        rating_to_edit = get_object_or_404(Rating, pk=rating_id, event=event)
        if user_is_organizer or rating_to_edit.user != request.user:
            messages.error(request, "No tienes permiso para editar esta calificación.")
            return redirect('event_detail', id=id) 

    if request.method == 'POST':
        if rating_to_edit:
            form = RatingForm(request.POST, instance=rating_to_edit)
        else:
            if user_is_organizer:
                messages.error(request, "Los organizadores no pueden dejar calificaciones.")
                return redirect('event_detail', id=id) 
            form = RatingForm(request.POST)

        if form.is_valid():
            if not event_has_started:

                form.add_error(None, "Solo puedes calificar eventos que ya ocurrieron.")
            elif not has_ticket:
                form.add_error(None, "Solo puedes calificar si tienes una entrada comprada para este evento.")

            else:
                try:
                    new_rating = form.save(commit=False)
                    new_rating.event = event
                    new_rating.user = request.user
                    new_rating.save()
                    messages.success(request, "¡Tu calificación ha sido guardada con éxito!")
                    return redirect('event_detail', id=id)
                except IntegrityError:
                    messages.warning(request, "Ya has calificado este evento. Puedes editar tu calificación existente.")
                except Exception as e:
                    messages.error(request, f"Error al guardar la calificación: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en el campo '{field if field != '__all__' else 'general'}': {error}")
    else:
        form = RatingForm(instance=rating_to_edit)

    context = {
        'event': event,
        'form': form,
        'rating_to_edit': rating_to_edit,
        'can_edit': user_is_organizer,
        'now': now,
        'event_has_started': event_has_started,
        'has_ticket': has_ticket,

    }
    return render(request, 'app/event_detail.html', context)


@login_required
def rating_delete(request, id, rating_id):
    event = get_object_or_404(Event, pk=id)
    rating = get_object_or_404(Rating, pk=rating_id, event=event)
    if request.user == rating.user or request.user.is_organizer:
        if request.method == "POST":
            rating.delete()
            return redirect("event_detail", id=id) 
    return redirect("event_detail", id=id) 

@login_required
def create_event(request):
    if not request.user.is_organizer:
        return redirect('events')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user

            scheduled_date = form.cleaned_data.get('scheduled_date')
            scheduled_time = form.cleaned_data.get('scheduled_time')

            if scheduled_date and scheduled_time:
                combined_datetime = datetime.datetime.combine(scheduled_date, scheduled_time)
                event.scheduled_at = timezone.make_aware(combined_datetime)

            event.general_tickets_available = event.general_tickets_total
            event.vip_tickets_available = event.vip_tickets_total

            event.save()
            form.save_m2m()
            return redirect('event_detail', id=event.id) 
    else:
        form = EventForm()

    return render(request, "app/event_form.html", {
        "form": form,
        "title": "Crear Evento",
    })

@login_required
def edit_event(request, event_id): 
    event = get_object_or_404(Event, id=event_id)

    if not request.user.is_organizer:
        return redirect('events')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            updated_event = form.save(commit=False)

            scheduled_date = form.cleaned_data.get('scheduled_date')
            scheduled_time = form.cleaned_data.get('scheduled_time')

            if scheduled_date and scheduled_time:
                combined_datetime = datetime.datetime.combine(scheduled_date, scheduled_time)
                updated_event.scheduled_at = timezone.make_aware(combined_datetime)

            general_diff = updated_event.general_tickets_total - event.general_tickets_total
            vip_diff = updated_event.vip_tickets_total - event.vip_tickets_total

            updated_event.general_tickets_available = event.general_tickets_available + general_diff
            updated_event.vip_tickets_available = event.vip_tickets_available + vip_diff

            updated_event.save()
            form.save_m2m()
            return redirect('event_detail', id=event.pk) 
    else:
        initial_data = {
            'title': event.title,
            'description': event.description,
            'general_price': event.general_price,
            'vip_price': event.vip_price,
            'general_tickets_total': event.general_tickets_total,
            'vip_tickets_total': event.vip_tickets_total,
            'scheduled_date': event.scheduled_at.date(),
            'scheduled_time': event.scheduled_at.time(),
            'venue': event.venue.id if event.venue else None,
        }
        form = EventForm(initial=initial_data, instance=event)

    categories = Category.objects.all()
    venues = Venue.objects.all()

    return render(
        request,
        "app/event_form.html",
        {
            "form": form,
            "title": "Editar Evento",
            "event": event,
            "categories": categories,
            "venues": venues,
        },
    )

@login_required
def event_delete(request, id):
    if not request.user.is_organizer:
        return redirect("events")

    event = get_object_or_404(Event, pk=id)

    if request.method == "POST":
        event.delete()
        return redirect("events")

    return redirect("event_detail", id=id) 

@login_required
def organizer_tickets(request, event_id=None): 
    if not request.user.is_organizer:
        return redirect('events')

    if event_id:
        event = get_object_or_404(Event, pk=event_id, organizer=request.user)
        tickets = Ticket.objects.filter(event=event).select_related('user').order_by('-buy_date')
        return render(request, 'app/organizer_tickets_event.html', {
            'event': event,
            'tickets': tickets,
            'total_sales': sum(t.total for t in tickets),
            'tickets_count': tickets.count()
        })
    else:
        events = Event.objects.filter(organizer=request.user).annotate(
            tickets_sold=Count('ticket'),
            total_sales=Sum('ticket__total')
        ).order_by('-scheduled_at')

        return render(request, 'app/organizer_event_list.html', {
            'events': events
        })

@login_required
@transaction.atomic
def ticket_purchase(request, event_id): 
    event = get_object_or_404(Event, pk=event_id)

    if request.user.is_organizer:

        return redirect('event_detail', id=event.pk)


    refund_codes = RefundRequest.objects.filter(
        user=request.user,
        approved__in=[True, None]
    ).values_list('ticket_code', flat=True)


    total_ya_compradas = Ticket.objects.filter(
        user=request.user,
        event=event
    ).exclude(ticket_code__in=refund_codes).aggregate(
        total=Sum('quantity')
    )['total'] or 0


    if request.method == 'POST':
        ticket_form = TicketForm(request.POST, event=event)
        payment_form = PaymentForm(request.POST)

        if ticket_form.is_valid() and payment_form.is_valid():
            cantidad_a_comprar = ticket_form.cleaned_data['quantity']
            if total_ya_compradas + cantidad_a_comprar > 4:
                messages.error(request, "No podés comprar más de 4 entradas para este evento.")
                return redirect('ticket_purchase', event_id=event.pk)

            try:
                with transaction.atomic():
                    ticket = ticket_form.save(commit=False)
                    ticket.user = request.user
                    ticket.event = event
                    ticket.ticket_code = ticket._generate_ticket_code()


                    price = event.general_price if ticket.type == Ticket.TicketType.GENERAL else event.vip_price
                    ticket.subtotal = price * Decimal(ticket.quantity)
                    ticket.taxes = ticket.subtotal * Decimal('0.10')
                    ticket.total = ticket.subtotal + ticket.taxes
                    ticket.payment_confirmed = True


                    payment_info = payment_form.save(commit=False)
                    payment_info.user = request.user
                    if payment_form.cleaned_data.get('save_card'):
                        payment_info.save()


                    ticket.save()


                    if ticket.type == Ticket.TicketType.GENERAL:
                        event.general_tickets_available -= ticket.quantity
                    else:
                        event.vip_tickets_available -= ticket.quantity
                    event.save()

                    messages.success(request, "Compra realizada con éxito.")
                    return redirect('ticket_detail', ticket_id=ticket.id)

            except Exception as e:
                messages.error(request, f"Error al procesar la compra: {str(e)}")
        else:
            messages.error(request, "Revisá los campos ingresados.")
    else:
        ticket_form = TicketForm(event=event)
        payment_form = PaymentForm()

    return render(request, 'app/ticket_purchase.html', {
        'event': event,
        'ticket_form': ticket_form,
        'payment_form': payment_form,
        'total_ya_compradas': total_ya_compradas
    })

@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.user != request.user and (not request.user.is_organizer or request.user != ticket.event.organizer):
        return HttpResponseForbidden("No tienes permiso para ver este ticket")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(ticket.ticket_code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, 'PNG')
    qr_code_base64 = ticket.qr_code_base64()

    return render(request, 'app/ticket_detail.html', {
        'ticket': ticket,
        'qr_code': qr_code_base64,
        'is_editable': ticket.can_be_modified_by(request.user),
        'is_organizer': request.user.is_organizer and request.user == ticket.event.organizer
    })

@login_required
@transaction.atomic
def ticket_update(request, ticket_id):
    ticket = get_object_or_404(Ticket.objects.select_related('event'), pk=ticket_id)

    if not ticket.can_be_modified_by(request.user):
        return redirect('ticket_detail', ticket_id=ticket_id)

    if not ticket._is_within_edit_window():
        return redirect('ticket_detail', ticket_id=ticket_id)

    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket, event=ticket.event)
        if form.is_valid():
            try:
                with transaction.atomic():
                    original_type = ticket.type
                    original_quantity = ticket.quantity

                    updated_ticket = form.save(commit=False)

                    new_type = updated_ticket.type
                    new_quantity = updated_ticket.quantity

                    type_changed = original_type != new_type
                    quantity_diff = new_quantity - original_quantity

                    if quantity_diff > 0:  
                        total_otros_tickets = Ticket.objects.filter(
                            user=request.user,
                            event=ticket.event
                        ).exclude(pk=ticket.pk).aggregate(
                            total=Sum('quantity')
                        )['total'] or 0

                        if total_otros_tickets + new_quantity > 4:
                            messages.error(request, "No podés tener más de 4 entradas para este evento.")
                            return redirect('ticket_update', ticket_id=ticket_id)

                    
                    if type_changed or quantity_diff > 0:
                        if type_changed:
                            available = ticket.event.get_available_tickets(new_type)
                            if available < new_quantity:
                                messages.error(request, f"No hay suficientes entradas {new_type.lower()} disponibles")
                                return redirect('ticket_update', ticket_id=ticket_id)
                        else:
                            available = ticket.event.get_available_tickets(new_type)
                            if available < quantity_diff:
                                messages.error(request, f"No hay suficientes entradas {new_type.lower()} disponibles")
                                return redirect('ticket_update', ticket_id=ticket_id)

                    price = ticket.event.general_price if new_type == Ticket.TicketType.GENERAL else ticket.event.vip_price

                    updated_ticket.subtotal = price * Decimal(new_quantity)
                    updated_ticket.taxes = updated_ticket.subtotal * Decimal('0.10')
                    updated_ticket.total = updated_ticket.subtotal + updated_ticket.taxes

                    
                    if type_changed:
                        if original_type == Ticket.TicketType.GENERAL:
                            ticket.event.general_tickets_available += original_quantity
                        else:
                            ticket.event.vip_tickets_available += original_quantity
                        if new_type == Ticket.TicketType.GENERAL:
                            ticket.event.general_tickets_available -= new_quantity
                        else:
                            ticket.event.vip_tickets_available -= new_quantity
                    else:
                        if new_type == Ticket.TicketType.GENERAL:
                            ticket.event.general_tickets_available -= quantity_diff
                        else:
                            ticket.event.vip_tickets_available -= quantity_diff

                    ticket.event.save()
                    updated_ticket.save()

                    messages.success(request, "Ticket actualizado correctamente")
                    return redirect('ticket_detail', ticket_id=ticket_id)

            except Exception as e:
                messages.error(request, f"Error al actualizar el ticket: {str(e)}")
                print(f"Error updating ticket: {str(e)}")
                return redirect('ticket_update', ticket_id=ticket_id)
    else:
        form = TicketForm(instance=ticket, event=ticket.event)

    total_ya_compradas = Ticket.objects.filter(
        user=request.user,
        event=ticket.event
    ).aggregate(total=Sum('quantity'))['total'] or 0

    return render(request, 'app/ticket_update.html', {
        'form': form,
        'ticket': ticket,
        'now': timezone.now(),
        'original_price': ticket.event.general_price if ticket.type == Ticket.TicketType.GENERAL else ticket.event.vip_price,
        'total_ya_compradas': total_ya_compradas  
    })

@login_required
@transaction.atomic
def ticket_delete(request, ticket_id):
    ticket = get_object_or_404(Ticket.objects.select_related('event', 'user'), pk=ticket_id)

    if not (ticket.user == request.user or
            (request.user.is_organizer and request.user == ticket.event.organizer)):
        return redirect('ticket_detail', ticket_id=ticket_id)

    if request.user.is_organizer and request.user == ticket.event.organizer:
        redirect_url = 'organizer_tickets_event'
        redirect_kwargs = {'event_id': ticket.event.pk}
    else:
        redirect_url = 'ticket_list'
        redirect_kwargs = {}

    if request.method == 'POST':
        try:
            with transaction.atomic():
                if ticket.type == Ticket.TicketType.GENERAL:
                    ticket.event.general_tickets_available += ticket.quantity
                else:
                    ticket.event.vip_tickets_available += ticket.quantity

                ticket.event.save()
                ticket.delete()

                return redirect(redirect_url, **redirect_kwargs)

        except Exception as e:
            messages.error(request, f"Error al eliminar el ticket: {str(e)}")
            return redirect('ticket_detail', ticket_id=ticket_id)

    return render(request, 'app/ticket_delete.html', {
        'ticket': ticket,
        'is_organizer': request.user.is_organizer and request.user == ticket.event.organizer,
        'redirect_url': redirect_url,
        'redirect_kwargs': redirect_kwargs
    })

@login_required
def ticket_use(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.is_organizer or ticket.event.organizer != request.user:
        messages.error(request, "No tienes permiso para marcar este ticket")
        return redirect('event_detail', id=ticket.event.pk)

    if request.method == 'POST':
        if ticket.is_used:
            messages.warning(request, "Este ticket ya estaba marcado como usado")
        else:
            ticket.is_used = True
            ticket.save()
            messages.success(request, f"Ticket #{ticket.ticket_code} marcado como usado")

    return redirect('event_detail', id=ticket.event.pk)

from app.models import RefundRequest  

@login_required
def ticket_list(request):
    now = timezone.now()
    tickets = Ticket.objects.filter(user=request.user).select_related('event').order_by('-buy_date')
    refund_codes = RefundRequest.objects.exclude(approved=False).values_list('ticket_code', flat=True)
    tickets = tickets.exclude(ticket_code__in=refund_codes)

    filter_form = TicketFilterForm(request.GET or None)

    if filter_form.is_valid():
        filter_by = filter_form.cleaned_data.get('filter_by', 'all')

        if filter_by == 'upcoming':
            tickets = tickets.filter(event__scheduled_at__gt=now)
        elif filter_by == 'past':
            tickets = tickets.filter(event__scheduled_at__lte=now)
        elif filter_by == 'used':
            tickets = tickets.filter(is_used=True)
        elif filter_by == 'unused':
            tickets = tickets.filter(is_used=False)

    return render(request, 'app/ticket_list.html', {
        'tickets': tickets,
        'filter_form': filter_form,
        'now': now
    })


@login_required
def category_list(request):
    if request.user.is_organizer:
        categories = Category.objects.all().annotate(event_count=Count('event'))
    else:
        categories = Category.objects.filter(is_active=True).annotate(event_count=Count('event'))

    return render(
        request,
        'app/category_list.html',
        {'categories': categories, 'user_is_organizer': request.user.is_organizer}
    )

@login_required
def category_form(request, id=None):
    if not request.user.is_organizer:
        return redirect('category_list')

    if id:
        category = get_object_or_404(Category, pk=id)
    else:
        category = None

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            if id:
                messages.success(request, 'La categoría fue actualizada con éxito')
            else:
                messages.success(request, 'La categoría fue creada con éxito')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'app/category_form.html', {'form': form})

@login_required
def category_detail(request, id):
    category = get_object_or_404(Category, pk=id)
    return render(request, 'app/category_detail.html', {
        'category': category,
        'user_is_organizer': request.user.is_organizer
    })

@login_required
def category_delete(request, id):
    if not request.user.is_organizer:
        return redirect('category_list')

    category = get_object_or_404(Category, pk=id)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'La categoría fue eliminada con éxito')
        return redirect('category_list')
    return redirect('category_list')

@login_required
def venue_list(request):
    venues = Venue.objects.all()
    return render(request, 'venues/venue_list.html', {'venues': venues})

@login_required
def create_venue(request):
    if not request.user.is_organizer:
        return HttpResponseForbidden("Solo los organizadores pueden crear ubicaciones.")

    form = VenueForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        venue = form.save(commit=False)
        venue.organizer = request.user
        venue.save()
        messages.success(request, "¡Ubicación creada con éxito!")
        return redirect('venue_list')

    return render(request, 'venues/create_venue.html', {'form': form})

@login_required
def edit_venue(request, venue_id):
    venue = get_object_or_404(Venue, id=venue_id)

    if not request.user.is_organizer:
        return HttpResponseForbidden("Solo los organizadores pueden editar ubicaciones.")

    form = VenueForm(request.POST or None, instance=venue)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "¡Ubicación editada con éxito!")
        return redirect('venue_list')

    return render(request, 'venues/edit_venue.html', {'form': form})

@login_required
def delete_venue(request, venue_id):
    venue = get_object_or_404(Venue, id=venue_id)

    if not request.user.is_organizer:
        return HttpResponseForbidden("Solo los organizadores pueden eliminar ubicaciones.")

    if request.method == 'POST':
        venue.delete()
        messages.success(request, "¡Ubicación eliminada con éxito!")
        return redirect('venue_list')

    return render(request, 'venues/delete_venue.html', {'venue': venue})

@login_required
def venue_detail(request, venue_id):
    venue = get_object_or_404(Venue, id=venue_id)
    return render(request, 'venues/venue_detail.html', {'venue': venue})

def calculate_refund_fee(ticket):
    days_until_event = (ticket.event.scheduled_at - timezone.now()).days

    if days_until_event > 7:
        return 0
    elif 3 < days_until_event <= 7:
        return 10
    elif 1 < days_until_event <= 3:
        return 20
    else:
        return 30

def process_payment(card_type, card_number, expiry_month, expiry_year, cvv, card_holder, amount):
    if card_number.endswith('1111'):
        return False, "Tarjeta declinada por el banco emisor"

    import random
    if random.random() < 0.05:
        return False, "Error de conexión con el procesador de pagos"

    return True, "Pago procesado exitosamente"

def process_refund(ticket, amount):
    import random
    if random.random() < 0.05:
        return False

    return True

@login_required
def event_form(request, id=None):
    if not request.user.is_organizer:
        return redirect("events")

    if id:
        event = get_object_or_404(Event, pk=id)
        form = EventForm(request.POST or None, request.FILES or None, instance=event)
    else:
        event = None
        form = EventForm(request.POST or None, request.FILES or None)

    venues = Venue.objects.all()
    categories = Category.objects.all()

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                event = form.save(commit=False)
                event.organizer = request.user

                scheduled_date = form.cleaned_data.get('scheduled_date')
                scheduled_time = form.cleaned_data.get('scheduled_time')

                if scheduled_date and scheduled_time:
                    combined_datetime = datetime.datetime.combine(scheduled_date, scheduled_time)
                    event.scheduled_at = timezone.make_aware(combined_datetime)

                if not id:
                    event.general_tickets_available = event.general_tickets_total
                    event.vip_tickets_available = event.vip_tickets_total

                event.save()
                form.save_m2m()

                messages.success(request, "Evento guardado exitosamente")
                return redirect('event_detail', id=event.id)

        except Exception as e:
            messages.error(request, f"Error al guardar el evento: {str(e)}")
            print(f"Error saving event: {str(e)}")

    initial = {}
    if event:
        initial = {
            'scheduled_date': event.scheduled_at.date(),
            'scheduled_time': event.scheduled_at.time()
        }

    return render(request, 'app/event_form.html', {
        'form': form,
        'event': event,
        'venues': venues,
        'categories': categories,
        'initial': initial,
        'min_date': timezone.now().date() + datetime.timedelta(days=1),
        'user_is_organizer': request.user.is_organizer  # ← ESTA LÍNEA ES CLAVE
    })


@login_required
def rating_create(request, id): 
    if request.user.is_organizer:
        messages.error(request, "Los organizadores no pueden dejar calificaciones.")
        return redirect("event_detail", id=id)

    if request.method == "POST":
        event = get_object_or_404(Event, pk=id)
        title = request.POST.get("title", "").strip()
        score = request.POST.get("score")
        comment = request.POST.get("comment", "").strip()

        Rating.objects.create(
            event=event, user=request.user, title=title, score=score, comment=comment
        )

    return redirect("event_detail", id=id)

@login_required
def my_refunds(request):
    refunds = RefundRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'app/my_refunds.html', {'reembolsos': refunds})

@login_required
@transaction.atomic
def refund_request(request):
    if request.method == 'POST':
        form = RefundRequestForm(request.POST, initial={'user': request.user})
        if form.is_valid():
            try:
                reembolso = form.save(commit=False)
                reembolso.user = request.user
                reembolso.approved = None
                reembolso.approval_date = None
                reembolso.save()
                messages.success(request, "¡Solicitud de reembolso enviada con éxito! Será revisada por un organizador.")
                return redirect('my_refunds')
            except IntegrityError:
                messages.error(request, "Ya existe una solicitud de reembolso para este ticket.")
            except ValidationError as e:
                form.add_error(None, str(e))
                messages.error(request, f"Error en la solicitud: {str(e)}")
            except Exception as e:
                messages.error(request, f"Ocurrió un error inesperado al procesar tu solicitud: {str(e)}")
                print(f"Error inesperado en refund_request (creación): {e}")
        else:
            pass
    else:
        form = RefundRequestForm(initial={'user': request.user})

    return render(request, 'app/refund_request.html', {'form': form})

@login_required
@transaction.atomic
def manage_refunds(request):
    if not request.user.is_organizer:
        messages.error(request, "Solo los organizadores pueden gestionar reembolsos.")
        return redirect('my_refunds')

    if request.method == "POST":
        refund_id = request.POST.get("refund_id")
        refund = get_object_or_404(RefundRequest, id=refund_id)

        if refund.approved is not None:
            messages.warning(request, "Esta solicitud de reembolso ya fue procesada.")
            return redirect('manage_refunds')

        try:
            ticket = Ticket.objects.get(ticket_code=refund.ticket_code)
        except Ticket.DoesNotExist:
            messages.error(request, "El ticket asociado a esta solicitud de reembolso no existe.")
            return redirect('manage_refunds')

        if ticket.event.organizer != request.user:
            messages.error(request, "No tienes permiso para gestionar reembolsos de este evento.")
            return redirect('manage_refunds')

        form = RefundApprovalForm(request.POST, instance=refund)
        if form.is_valid():
            try:
                with transaction.atomic():
                    if form.cleaned_data["approve"]:

                        refund_fee_percentage = calculate_refund_fee(ticket)
                        amount_to_refund = ticket.total * (1 - Decimal(str(refund_fee_percentage / 100)))

                        refund_processed_successfully = process_refund(ticket, amount_to_refund)

                        if refund_processed_successfully:
                            refund.approved = True
                            refund.approval_date = timezone.now()
                            refund.save()

                            ticket.payment_confirmed = False
                            if ticket.type == Ticket.TicketType.GENERAL:
                                ticket.event.general_tickets_available += ticket.quantity
                            else:
                                ticket.event.vip_tickets_available += ticket.quantity
                            ticket.event.save()
                            ticket.save()

                            messages.success(request, f"¡Reembolso aprobado y procesado para ticket {ticket.ticket_code}! Se reembolsarán ${amount_to_refund:.2f}. Stock de tickets repuesto.")
                        else:
                            refund.approved = False
                            refund.approval_date = timezone.now()
                            refund.save()
                            messages.error(request, f"Error al procesar el reembolso monetario para ticket {ticket.ticket_code}. La solicitud fue rechazada por fallo de pago. Contacta a soporte.")

                    elif form.cleaned_data["reject"]:
                        refund.approved = False
                        refund.approval_date = timezone.now()
                        refund.save()
                        messages.warning(request, f"Solicitud de reembolso para ticket {ticket.ticket_code} rechazada.")

                    return redirect('manage_refunds')

            except IntegrityError:
                messages.error(request, "Error de integridad de datos al procesar el reembolso.")
            except Exception as e:
                messages.error(request, f"Ocurrió un error inesperado al procesar la solicitud: {str(e)}")
                print(f"Error inesperado en manage_refunds: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en el formulario de aprobación: {error}")
            return redirect('manage_refunds')

    refunds = RefundRequest.objects.all().order_by("-created_at")
    forms_dict = {r.pk: RefundApprovalForm(instance=r) for r in refunds}
    return render(request, 'app/manage_refund.html', {
        'refunds': refunds,
        'forms_dict': forms_dict
    })

@login_required
def refund_detail(request, id):
    refund = get_object_or_404(RefundRequest, id=id)

    if refund.user != request.user and not request.user.is_organizer:
        messages.error(request, "No tienes permiso para ver los detalles de esta solicitud de reembolso.")
        return redirect('my_refunds')

    ticket = None
    event = None
    try:
        ticket = Ticket.objects.get(ticket_code=refund.ticket_code)
        event = ticket.event

        if request.user.is_organizer and event.organizer != request.user:
            messages.error(request, "No tienes permiso para ver los detalles de reembolsos de eventos que no organizas.")
            return redirect('manage_refunds')

    except Ticket.DoesNotExist:
        messages.warning(request, "Ticket asociado no encontrado.")

    return render(request, 'app/refund_detail.html', {
        'refund': refund,
        'event': event,
        'ticket': ticket,
    })

@login_required
def edit_refund(request, id):
    refund_request_obj = get_object_or_404(RefundRequest, id=id)

    if refund_request_obj.user != request.user:
        messages.error(request, "No tienes permiso para editar esta solicitud de reembolso.")
        return redirect('my_refunds')

    if refund_request_obj.approved is not None:
        messages.warning(request, "Esta solicitud de reembolso ya fue procesada y no puede ser editada.")
        return redirect('refund_detail', id=id)

    if request.method == 'POST':
        form = RefundRequestForm(request.POST, instance=refund_request_obj, initial={'user': request.user})
        if form.is_valid():
            form.save()
            messages.success(request, "¡Reembolso editado con éxito!")
            return redirect('my_refunds')
    else:
        form = RefundRequestForm(instance=refund_request_obj, initial={'user': request.user})

    return render(request, 'app/refund_request.html', {'form': form})

@login_required
def delete_refund(request, id):
    refund = get_object_or_404(RefundRequest, pk=id)

    if refund.user != request.user and not request.user.is_organizer:
        messages.error(request, "No tienes permiso para eliminar esta solicitud.")
        return redirect("my_refunds")

    if refund.approved is not None:
        messages.warning(request, "No puedes eliminar una solicitud de reembolso que ya ha sido procesada.")
        return redirect("refund_detail", id=id)

    if request.method == "POST":
        refund.delete()
        messages.success(request, "¡Reembolso eliminado con éxito!")
        return redirect("my_refunds")

    messages.info(request, "Por favor, confirma la eliminación de la solicitud de reembolso.")
    return render(request, 'app/refund_confirm_delete.html', {'refund': refund})

def refund_detail(request, id):
    refund = get_object_or_404(RefundRequest, id=id)
    try:
        ticket = Ticket.objects.get(ticket_code=refund.ticket_code)
        event = ticket.event
    except Ticket.DoesNotExist:
        ticket = None
        event = None

    return render(request, 'app/refund_detail.html', {
        'refund': refund,
        'event': event,
        'ticket': ticket,
    })

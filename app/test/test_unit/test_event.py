import datetime
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from app.models import Event, User, Venue, Category
from typing import cast 

class EventModelTest(TestCase):
    def setUp(self):
        
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="test123",
            is_organizer=True,
        )
        
        self.venue = Venue.objects.create(
            name="Estadio Test",
            address="Calle Test 123",
            city="Ciudad Test",
            capacity=1000,
            contact="contacto@test.com",
            organizer=self.organizer
        )
        
        self.category = Category.objects.create(
            name="Concierto",
            description="Eventos musicales",
            is_active=True
        )
        
        
        self.future_date = timezone.now() + datetime.timedelta(days=1)
        self.past_date = timezone.now() - datetime.timedelta(days=1)
        self.very_future_date = timezone.now() + datetime.timedelta(days=2) 

        
        self.base_event_data = {
            "title": "Evento base",
            "description": "Descripción base",
            "scheduled_at": self.future_date,
            "organizer": self.organizer,
            "venue": self.venue,
            "general_price": Decimal('50.00'),
            "vip_price": Decimal('100.00'),
            "general_tickets_total": 100,
            "general_tickets_available": 100,
            "vip_tickets_total": 20,
            "vip_tickets_available": 20
        }

   
    def test_event_creation(self):
        """
        Verifica que un evento se crea correctamente con todos sus atributos.
        """
        event = Event.objects.create(**self.base_event_data)
        event.categories.add(self.category)
        
        self.assertEqual(event.title, "Evento base")
        self.assertEqual(event.description, "Descripción base")
        self.assertEqual(event.scheduled_at, self.future_date)
        self.assertEqual(event.organizer, self.organizer)
        self.assertEqual(event.venue, self.venue)
        self.assertEqual(event.general_price, Decimal('50.00'))
        self.assertEqual(event.vip_price, Decimal('100.00'))
        self.assertEqual(event.general_tickets_total, 100)
        self.assertEqual(event.general_tickets_available, 100)
        self.assertEqual(event.vip_tickets_total, 20)
        self.assertEqual(event.vip_tickets_available, 20)
        self.assertIn(self.category, event.categories.all())
        self.assertFalse(event.is_past)
        self.assertFalse(event.is_sold_out)
        self.assertIsNotNone(event.created_at)
        self.assertIsNotNone(event.updated_at)

    def test_event_validate_with_valid_data(self):
        """
        Verifica que la función `Event.validate()` retorna un diccionario vacío
        cuando se le pasan datos válidos, indicando que no hay errores.
        """
        errors = Event.validate(
            title="Título válido", 
            description="Descripción válida", 
            scheduled_at=self.future_date,
            general_tickets=100,
            vip_tickets=50
        )
        self.assertDictEqual(errors, {}) 

    def test_event_validate_with_invalid_title(self):
        """
        Verifica que `Event.validate()` detecta correctamente un título vacío.
        """
        errors = Event.validate(title="", description="Descripción válida", scheduled_at=self.future_date)
        self.assertIn("title", errors)
        self.assertEqual(errors["title"], "Por favor ingrese un titulo")

    def test_event_validate_with_invalid_description(self):
        """
        Verifica que `Event.validate()` detecta una descripción vacía.
        Asume que el modelo tiene un mensaje de error específico para descripción vacía.
        """
        errors = Event.validate(title="Título válido", description="", scheduled_at=self.future_date)
        self.assertIn("description", errors)
       

    def test_event_validate_with_past_scheduled_at(self):
        """
        Verifica que `Event.validate()` detecta una fecha programada en el pasado.
        """
        errors = Event.validate(title="Título válido", description="Descripción válida", scheduled_at=self.past_date)
        self.assertIn("scheduled_at", errors)
        self.assertEqual(errors["scheduled_at"], "La fecha del evento debe ser en el futuro")

    def test_event_validate_with_negative_general_tickets(self):
        """
        Verifica que `Event.validate()` detecta una cantidad negativa de tickets generales.
        """
        errors = Event.validate(
            title="Título válido", description="Descripción válida", scheduled_at=self.future_date, general_tickets=-1
        )
        self.assertIn("general_tickets", errors)
        self.assertEqual(errors["general_tickets"], "Ingrese una cantidad válida de tickets generales")

    def test_event_validate_with_negative_vip_tickets(self):
        """
        Verifica que `Event.validate()` detecta una cantidad negativa de tickets VIP.
        """
        errors = Event.validate(
            title="Título válido", description="Descripción válida", scheduled_at=self.future_date, vip_tickets=-1
        )
        self.assertIn("vip_tickets", errors)
        self.assertEqual(errors["vip_tickets"], "Ingrese una cantidad válida de tickets VIP")


    def test_event_new_with_valid_data(self):
        """
        Verifica que el método `Event.new()` crea un evento exitosamente
        cuando se le proporcionan datos válidos.
        """
        success, result_or_errors = Event.new(
            title="Nuevo evento",
            description="Descripción del nuevo evento",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            venue=self.venue,
            categories=[self.category],
            general_price=Decimal('50.00'),
            vip_price=Decimal('100.00'),
            general_tickets=200,
            vip_tickets=50
        )
        self.assertTrue(success)
      
        event = cast(Event, result_or_errors) 
        self.assertIsInstance(event, Event)
        
        self.assertEqual(event.title, "Nuevo evento")
        self.assertEqual(event.description, "Descripción del nuevo evento")
        self.assertEqual(event.organizer, self.organizer)
        self.assertEqual(event.venue, self.venue)
        self.assertEqual(event.general_tickets_total, 200)
        self.assertEqual(event.general_tickets_available, 200)
        self.assertEqual(event.vip_tickets_total, 50)
        self.assertEqual(event.vip_tickets_available, 50)
        
       
        saved_event = Event.objects.get(title="Nuevo evento")
        self.assertEqual(saved_event.description, "Descripción del nuevo evento")
        self.assertEqual(saved_event.organizer, self.organizer)
        self.assertIn(self.category, saved_event.categories.all())

    def test_event_new_with_invalid_title_does_not_create_event(self):
        """
        Verifica que `Event.new()` falla (retorna `False` y un diccionario de errores)
        y no crea un evento si el título es inválido.
        """
        initial_count = Event.objects.count()
        success, result_or_errors = Event.new(
            title="",
            description="Descripción válida",
            scheduled_at=self.future_date,
            organizer=self.organizer
        )
        self.assertFalse(success)
        errors = cast(dict, result_or_errors) 
        self.assertIsInstance(errors, dict)
        self.assertIn("title", errors)
        self.assertEqual(errors["title"], "Por favor ingrese un titulo")
        self.assertEqual(Event.objects.count(), initial_count) 

    def test_event_new_with_past_date_does_not_create_event(self):
        """
        Verifica que `Event.new()` falla y no crea un evento
        si la fecha programada está en el pasado.
        """
        initial_count = Event.objects.count()
        success, result_or_errors = Event.new(
            title="Título válido",
            description="Descripción válida",
            scheduled_at=self.past_date,
            organizer=self.organizer
        )
        self.assertFalse(success)
        errors = cast(dict, result_or_errors) 
        self.assertIsInstance(errors, dict)
        self.assertIn("scheduled_at", errors)
        self.assertEqual(errors["scheduled_at"], "La fecha del evento debe ser en el futuro")
        self.assertEqual(Event.objects.count(), initial_count) 


    def test_event_update_all_fields(self):
        """
        Verifica la actualización completa de todos los campos de un evento existente.
        """
        event = Event.objects.create(**self.base_event_data)
        
     
        new_venue = Venue.objects.create(
            name="Nuevo Venue",
            address="Nueva Dirección",
            city="Nueva Ciudad",
            capacity=500,
            contact="nuevo@test.com",
            organizer=self.organizer
        )
        new_category = Category.objects.create(
            name="Teatro",
            description="Eventos teatrales",
            is_active=True
        )
        
        event.update(
            title="Evento actualizado",
            description="Descripción actualizada",
            scheduled_at=self.very_future_date,
            venue=new_venue,
            categories=[new_category],
            general_price=Decimal('60.00'),
            vip_price=Decimal('120.00'),
            general_tickets=150,
            vip_tickets=30
        )

       
        updated_event = Event.objects.get(pk=event.pk)
        self.assertEqual(updated_event.title, "Evento actualizado")
        self.assertEqual(updated_event.description, "Descripción actualizada")
        self.assertEqual(updated_event.scheduled_at, self.very_future_date)
        self.assertEqual(updated_event.venue, new_venue)
        self.assertEqual(updated_event.general_price, Decimal('60.00'))
        self.assertEqual(updated_event.vip_price, Decimal('120.00'))
        self.assertEqual(updated_event.general_tickets_total, 150)
        self.assertEqual(updated_event.general_tickets_available, 150)
        self.assertEqual(updated_event.vip_tickets_total, 30)
        self.assertEqual(updated_event.vip_tickets_available, 30)
        self.assertIn(new_category, updated_event.categories.all())

    def test_event_partial_update_title_and_vip_tickets(self):
        """
        Verifica la actualización parcial de un evento, cambiando solo el título y los tickets VIP.
        Los demás campos deben permanecer inalterados.
        """
        event = Event.objects.create(**self.base_event_data)
        
        event.update(
            title="Solo título cambiado",
            vip_tickets=30
        )
        
        updated_event = Event.objects.get(pk=event.pk)
        self.assertEqual(updated_event.title, "Solo título cambiado")
        self.assertEqual(updated_event.description, self.base_event_data["description"]) 
        self.assertEqual(updated_event.vip_tickets_total, 30)
        self.assertEqual(updated_event.vip_tickets_available, 30) 
        self.assertEqual(updated_event.general_tickets_total, self.base_event_data["general_tickets_total"]) 



    def test_event_is_past_property_for_past_event(self):
        """
        Verifica que la propiedad `is_past` retorna `True` para un evento con fecha pasada.
        """
        past_event = Event.objects.create(
            title="Evento pasado",
            description="Descripción",
            scheduled_at=self.past_date,
            organizer=self.organizer
        )
        self.assertTrue(past_event.is_past)
        
    def test_event_is_past_property_for_future_event(self):
        """
        Verifica que la propiedad `is_past` retorna `False` para un evento con fecha futura.
        """
        future_event = Event.objects.create(
            title="Evento futuro",
            description="Descripción",
            scheduled_at=self.future_date,
            organizer=self.organizer
        )
        self.assertFalse(future_event.is_past)

    def test_event_is_sold_out_property_when_not_sold_out(self):
        """
        Verifica que la propiedad `is_sold_out` retorna `False` si hay tickets disponibles
        (generales y VIP).
        """
        event = Event.objects.create(
            title="Evento con tickets",
            description="Descripción",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            general_tickets_total=100,
            general_tickets_available=100,
            vip_tickets_total=50,
            vip_tickets_available=50
        )
        self.assertFalse(event.is_sold_out)

    def test_event_is_sold_out_property_when_only_general_sold_out(self):
        """
        Verifica que la propiedad `is_sold_out` retorna `False` si solo los tickets generales
        están agotados, pero aún quedan VIPs.
        """
        event = Event.objects.create(
            title="Evento con tickets",
            description="Descripción",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            general_tickets_total=100,
            general_tickets_available=0, 
            vip_tickets_total=50,
            vip_tickets_available=10 
        )
        self.assertFalse(event.is_sold_out)

    def test_event_is_sold_out_property_when_all_tickets_sold_out(self):
        """
        Verifica que la propiedad `is_sold_out` retorna `True` si todos los tickets
        (generales y VIP) están agotados.
        """
        event = Event.objects.create(
            title="Evento con tickets",
            description="Descripción",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            general_tickets_total=100,
            general_tickets_available=0,
            vip_tickets_total=50,
            vip_tickets_available=0
        )
        self.assertTrue(event.is_sold_out)

    def test_get_available_tickets_general(self):
        """
        Verifica que el método `get_available_tickets()` retorna la cantidad correcta
        de tickets generales disponibles.
        """
        event = Event.objects.create(
            title="Evento con tickets",
            description="Descripción",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            general_tickets_total=100,
            general_tickets_available=80, 
            vip_tickets_total=50,
            vip_tickets_available=30
        )
        self.assertEqual(event.get_available_tickets('GENERAL'), 80)

    def test_get_available_tickets_vip(self):
        """
        Verifica que el método `get_available_tickets()` retorna la cantidad correcta
        de tickets VIP disponibles.
        """
        event = Event.objects.create(
            title="Evento con tickets",
            description="Descripción",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            general_tickets_total=100,
            general_tickets_available=80, 
            vip_tickets_total=50,
            vip_tickets_available=30
        )
        self.assertEqual(event.get_available_tickets('VIP'), 30)

    def test_get_available_tickets_invalid_type(self):
        """
        Verifica que el método `get_available_tickets()` retorna 0
        cuando se le pasa un tipo de ticket inválido.
        """
        event = Event.objects.create(
            title="Evento con tickets",
            description="Descripción",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            general_tickets_total=100,
            general_tickets_available=80, 
            vip_tickets_total=50,
            vip_tickets_available=30
        )
        self.assertEqual(event.get_available_tickets('INVALID'), 0)

    def test_formatted_date_property(self):
        """
        Verifica que la propiedad `formatted_date` retorna la fecha del evento
        en el formato esperado.
        """
        test_date = timezone.make_aware(datetime.datetime(2023, 12, 25, 20, 0))
        event = Event.objects.create(
            title="Evento con fecha",
            description="Descripción",
            scheduled_at=test_date,
            organizer=self.organizer
        )
        formatted = event.formatted_date
        self.assertIn("lunes 25 de diciembre del 2023", formatted.lower())

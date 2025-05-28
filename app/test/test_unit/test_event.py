import datetime
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from app.models import Event, User, Venue, Category


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


    def test_event_new_with_valid_data(self):
        """Test que verifica la creación de eventos con datos válidos"""
        scheduled_at = timezone.now() + datetime.timedelta(days=2)



    def test_event_creation(self):
        """Test que verifica la creación correcta de eventos"""
        event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            venue=self.venue,
            general_price=Decimal('100.00'),
            vip_price=Decimal('200.00'),
            general_tickets_total=500,
            general_tickets_available=500,
            vip_tickets_total=100,
            vip_tickets_available=100
        )
        event.categories.add(self.category)
        
        self.assertEqual(event.title, "Evento de prueba")
        self.assertEqual(event.description, "Descripción del evento de prueba")
        self.assertEqual(event.organizer, self.organizer)
        self.assertEqual(event.venue, self.venue)
        self.assertEqual(event.general_price, Decimal('100.00'))
        self.assertEqual(event.vip_price, Decimal('200.00'))
        self.assertEqual(event.general_tickets_total, 500)
        self.assertEqual(event.general_tickets_available, 500)
        self.assertEqual(event.vip_tickets_total, 100)
        self.assertEqual(event.vip_tickets_available, 100)
        self.assertIn(self.category, event.categories.all())
        self.assertFalse(event.is_past)
        self.assertFalse(event.is_sold_out)
        self.assertIsNotNone(event.created_at)
        self.assertIsNotNone(event.updated_at)

    def test_event_validate_with_valid_data(self):
        """Test que verifica la validación de eventos con datos válidos"""
        errors = Event.validate(
            title="Título válido", 
            description="Descripción válida", 
            scheduled_at=self.future_date,
            general_tickets=100,
            vip_tickets=50
        )
        self.assertEqual(errors, {})

    def test_event_validate_with_invalid_data(self):
        """Test que verifica la validación de eventos con datos inválidos"""
       
        errors = Event.validate(
            title="", 
            description="Descripción válida", 
            scheduled_at=self.future_date
        )
        self.assertIn("title", errors)
        self.assertEqual(errors["title"], "Por favor ingrese un titulo")
        errors = Event.validate(
            title="Título válido", 
            description="", 
            scheduled_at=self.future_date
        )
        self.assertIn("description", errors)
        errors = Event.validate(
            title="Título válido", 
            description="Descripción válida", 
            scheduled_at=self.past_date
        )
        self.assertIn("scheduled_at", errors)
        self.assertEqual(errors["scheduled_at"], "La fecha del evento debe ser en el futuro")
        errors = Event.validate(
            title="Título válido", 
            description="Descripción válida", 
            scheduled_at=self.future_date,
            general_tickets=-1
        )
        self.assertIn("general_tickets", errors)
        self.assertEqual(errors["general_tickets"], "Ingrese una cantidad válida de tickets generales")
        errors = Event.validate(
            title="Título válido", 
            description="Descripción válida", 
            scheduled_at=self.future_date,
            vip_tickets=-1
        )
        self.assertIn("vip_tickets", errors)
        self.assertEqual(errors["vip_tickets"], "Ingrese una cantidad válida de tickets VIP")

    def test_event_new_with_valid_data(self):
        """Test que verifica la creación de eventos con datos válidos"""

        success, result = Event.new(
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
        self.assertIsInstance(result, Event)
        
       
        if success and isinstance(result, Event):
            self.assertEqual(result.title, "Nuevo evento")
            self.assertEqual(result.description, "Descripción del nuevo evento")
            self.assertEqual(result.organizer, self.organizer)
            self.assertEqual(result.venue, self.venue)
            self.assertEqual(result.general_tickets_total, 200)
            self.assertEqual(result.general_tickets_available, 200)
            self.assertEqual(result.vip_tickets_total, 50)
            self.assertEqual(result.vip_tickets_available, 50)
        saved_event = Event.objects.get(title="Nuevo evento")
        self.assertEqual(saved_event.description, "Descripción del nuevo evento")
        self.assertEqual(saved_event.organizer, self.organizer)
        self.assertIn(self.category, saved_event.categories.all())


    def test_event_new_with_invalid_data(self):
        """Test que verifica que Event.new() retorna errores con datos inválidos"""
        initial_count = Event.objects.count()
        success, errors = Event.new(
            title="",
            description="Descripción válida",
            scheduled_at=self.future_date,
            organizer=self.organizer
        )
        
        self.assertFalse(success)
        self.assertIsInstance(errors, dict)
        self.assertIn("title", errors)
        if isinstance(errors, dict) and "title" in errors:
            self.assertEqual(errors["title"], "Por favor ingrese un titulo")
        self.assertEqual(Event.objects.count(), initial_count)
        success, errors = Event.new(
            title="Título válido",
            description="Descripción válida",
            scheduled_at=self.past_date,
            organizer=self.organizer
        )
        self.assertFalse(success)
        self.assertIsInstance(errors, dict)
        self.assertIn("scheduled_at", errors)
        if isinstance(errors, dict) and "scheduled_at" in errors:
            self.assertEqual(errors["scheduled_at"], "La fecha del evento debe ser en el futuro")
            self.assertEqual(Event.objects.count(), initial_count)

    def test_event_update(self):
        """Test que verifica la actualización completa de eventos"""
        event = Event.objects.create(
            title="Evento original",
            description="Descripción original",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            general_price=Decimal('50.00'),
            vip_price=Decimal('100.00'),
            general_tickets_total=100,
            general_tickets_available=100,
            vip_tickets_total=20,
            vip_tickets_available=20
        )
        
        new_date = self.future_date + datetime.timedelta(days=2)
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
            scheduled_at=new_date,
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
        self.assertEqual(updated_event.scheduled_at, new_date)
        self.assertEqual(updated_event.venue, new_venue)
        self.assertEqual(updated_event.general_price, Decimal('60.00'))
        self.assertEqual(updated_event.vip_price, Decimal('120.00'))
        self.assertEqual(updated_event.general_tickets_total, 150)
        self.assertEqual(updated_event.general_tickets_available, 150)
        self.assertEqual(updated_event.vip_tickets_total, 30)
        self.assertEqual(updated_event.vip_tickets_available, 30)
        self.assertIn(new_category, updated_event.categories.all())

    def test_event_partial_update(self):
        """Test que verifica la actualización parcial de eventos"""
        event = Event.objects.create(
            title="Evento original",
            description="Descripción original",
            scheduled_at=self.future_date,
            organizer=self.organizer,
            general_price=Decimal('50.00'),
            vip_price=Decimal('100.00'),
            general_tickets_total=100,
            general_tickets_available=100,
            vip_tickets_total=20,
            vip_tickets_available=20
        )
        
        event.update(
            title="Solo título cambiado",
            vip_tickets=30
        )
        
        updated_event = Event.objects.get(pk=event.pk)
        self.assertEqual(updated_event.title, "Solo título cambiado")
        self.assertEqual(updated_event.description, "Descripción original")  
        self.assertEqual(updated_event.vip_tickets_total, 30)
        self.assertEqual(updated_event.vip_tickets_available, 30)  
        self.assertEqual(updated_event.general_tickets_total, 100) 
        
    def test_event_is_past_property(self):
        """Test para la propiedad is_past"""
        past_event = Event.objects.create(
            title="Evento pasado",
            description="Descripción",
            scheduled_at=self.past_date,
            organizer=self.organizer
        )
        self.assertTrue(past_event.is_past)
        
        future_event = Event.objects.create(
            title="Evento futuro",
            description="Descripción",
            scheduled_at=self.future_date,
            organizer=self.organizer
        )
        self.assertFalse(future_event.is_past)

    def test_event_is_sold_out_property(self):
        """Test para la propiedad is_sold_out"""
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
        event.general_tickets_available = 0
        self.assertFalse(event.is_sold_out)  
        event.vip_tickets_available = 0
        self.assertTrue(event.is_sold_out)

    def test_get_available_tickets(self):
        """Test para el método get_available_tickets"""
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
        self.assertEqual(event.get_available_tickets('VIP'), 30)
        self.assertEqual(event.get_available_tickets('INVALID'), 0)

    def test_formatted_date_property(self):
        """Test para la propiedad formatted_date"""
        test_date = timezone.make_aware(datetime.datetime(2023, 12, 25, 20, 0))
        event = Event.objects.create(
            title="Evento con fecha",
            description="Descripción",
            scheduled_at=test_date,
            organizer=self.organizer
        )
        
        formatted = event.formatted_date
        self.assertIn("lunes 25 de diciembre del 2023", formatted.lower())


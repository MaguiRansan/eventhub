from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/login/", views.login_view, name="login"),

    path("events/", views.events, name="events"),
    path("events/create/", views.event_form, name="event_form"),
    path("events/<int:id>/edit/", views.event_form, name="event_edit"),
    path("events/<int:id>/", views.event_detail, name="event_detail"),
    path("events/<int:id>/delete/", views.event_delete, name="event_delete"),

    path("events/<int:id>/ratings/create/", views.rating_create, name="rating_create"),
    path("events/<int:id>/ratings/<int:rating_id>/delete/", views.rating_delete, name="rating_delete"),

    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_form, name="category_form"),
    path("categories/<int:id>/edit/", views.category_form, name="category_edit"),
    path("categories/<int:id>/", views.category_detail, name="category_detail"),
    path("categories/<int:id>/delete/", views.category_delete, name="category_delete"),

    path('venues/', views.venue_list, name='venue_list'),
    path('venues/nuevo/', views.create_venue, name='create_venue'),
    path('venues/<int:venue_id>/editar/', views.edit_venue, name='edit_venue'),
    path('venues/<int:venue_id>/eliminar/', views.delete_venue, name='delete_venue'),
    path('venues/<int:venue_id>/', views.venue_detail, name='venue_detail'),

    path("events/<int:event_id>/purchase/", views.ticket_purchase, name="ticket_purchase"),
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/<int:ticket_id>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:ticket_id>/update/", views.ticket_update, name="ticket_update"),
    path("tickets/<int:ticket_id>/delete/", views.ticket_delete, name="ticket_delete"),
    path("tickets/<int:ticket_id>/use/", views.ticket_use, name="ticket_use"),
    path('organizer/tickets/', views.organizer_tickets, name='organizer_tickets'),
    path('organizer/tickets/<int:event_id>/', views.organizer_tickets, name='organizer_tickets_event'),

    path('refund_request/', views.refund_request, name='refund_request'),
    path('my_refunds/', views.my_refunds, name='my_refunds'),
    path('manage_refunds/', views.manage_refunds, name='manage_refunds'),
    path('refund_detail/<int:id>/', views.refund_detail, name='refund_detail'),
    path('edit_refund/<int:id>/', views.edit_refund, name='edit_refund'),  
    path('delete_refund/<int:id>/', views.delete_refund, name='delete_refund'),  

]

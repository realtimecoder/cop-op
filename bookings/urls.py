from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('new/<int:service_id>/<int:worker_id>/', views.create_booking, name='create_booking'),
    path('availability/<int:worker_id>/', views.worker_availability_json, name='worker_availability'),
    path('mine/', views.my_bookings, name='my_bookings'),
    path('<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('<int:booking_id>/status/', views.booking_status_json, name='booking_status_json'),
    path('<int:booking_id>/action/<str:action>/', views.worker_action, name='worker_action'),
    path('<int:booking_id>/confirm/', views.confirm_completion, name='confirm_completion'),
    path('<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('<int:booking_id>/pay/', views.make_payment, name='make_payment'),
    path('<int:booking_id>/pay/callback/', views.razorpay_callback, name='razorpay_callback'),
    path('<int:booking_id>/review/', views.submit_review, name='submit_review'),
    path('<int:booking_id>/complaint/', views.file_complaint, name='file_complaint'),
]

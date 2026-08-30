from django.contrib import admin
from .models import Booking, Complaint


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'service', 'worker', 'scheduled_date', 'status', 'total_amount')
    list_filter = ('status', 'is_emergency', 'is_recurring')
    search_fields = ('customer__phone_number', 'service__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'raised_by', 'status', 'created_at')
    list_filter = ('status',)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTPRequest


@admin.register(User)
class CoopSevaUserAdmin(UserAdmin):
    list_display = ('username', 'phone_number', 'first_name', 'last_name', 'role', 'city', 'is_phone_verified', 'is_active')
    list_filter = ('role', 'city', 'is_phone_verified', 'is_active')
    search_fields = ('username', 'phone_number', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Co-opSeva Profile', {'fields': ('role', 'phone_number', 'preferred_language', 'address', 'city',
                                           'pincode', 'profile_photo', 'emergency_contact', 'is_phone_verified')}),
    )


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'code', 'purpose', 'created_at', 'is_used')
    list_filter = ('purpose', 'is_used')

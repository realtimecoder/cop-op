from django.contrib import admin
from .models import ServiceCategory, Service


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 0
    fields = ('name', 'variant', 'fixed_labour_charge', 'warranty_days', 'is_active')


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'fixed_visit_charge', 'is_active')
    list_editable = ('fixed_visit_charge', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ServiceInline]
    search_fields = ('name',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'fixed_labour_charge', 'variant', 'is_active')
    list_editable = ('fixed_labour_charge', 'is_active')
    list_filter = ('category', 'variant', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'category__name')

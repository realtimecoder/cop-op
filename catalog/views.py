from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from .models import ServiceCategory, Service


def category_list(request):
    """Public browsing — no login required (Udemy-style discovery)."""
    categories = ServiceCategory.objects.filter(is_active=True).prefetch_related('services')
    query = request.GET.get('q', '').strip()
    if query:
        categories = categories.filter(
            Q(name__icontains=query) | Q(services__name__icontains=query)
        ).distinct()
    return render(request, 'catalog/category_list.html', {'categories': categories, 'query': query})


def category_detail(request, slug):
    category = get_object_or_404(ServiceCategory, slug=slug, is_active=True)
    services = category.services.filter(is_active=True)
    return render(request, 'catalog/category_detail.html', {'category': category, 'services': services})


def service_detail(request, category_slug, service_slug):
    service = get_object_or_404(
        Service, slug=service_slug, category__slug=category_slug, is_active=True
    )
    related = Service.objects.filter(category=service.category, is_active=True).exclude(id=service.id)[:4]
    return render(request, 'catalog/service_detail.html', {'service': service, 'related': related})

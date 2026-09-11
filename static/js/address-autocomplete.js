/**
 * Google Maps Address Autocomplete Utility
 * This utility attaches to a search input and populates related form fields
 * with formatted address, city, pincode, latitude, and longitude.
 */

function initAddressAutocomplete(searchInputId, fieldMappings) {
    const searchInput = document.getElementById(searchInputId);
    if (!searchInput) return;

    // 1. Initialize Autocomplete
    const autocomplete = new google.maps.places.Autocomplete(searchInput, {
        types: ['address'],
        componentRestrictions: { country: 'IN' }
    });

    autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace();
        fillFieldsFromPlace(place, fieldMappings);
    });

    // 2. Initialize "Current Location" button if it exists
    const locationBtn = document.getElementById('btn-current-location');
    if (locationBtn) {
        locationBtn.addEventListener('click', () => {
            handleCurrentLocation(fieldMappings);
        });
    }
}

function fillFieldsFromPlace(place, fieldMappings) {
    if (!place.geometry) {
        console.error("No geometry available for the selected place.");
        return;
    }

    // Formatted Address
    if (fieldMappings.address) {
        const el = document.getElementById(fieldMappings.address);
        if (el) el.value = place.formatted_address || '';
    }

    // Coordinates
    if (fieldMappings.latitude) {
        const el = document.getElementById(fieldMappings.latitude);
        if (el) el.value = place.geometry.location.lat();
    }
    if (fieldMappings.longitude) {
        const el = document.getElementById(fieldMappings.longitude);
        if (el) el.value = place.geometry.location.lng();
    }

    // Address Components
    let city = '', state = '', country = '', pincode = '';
    place.address_components.forEach(comp => {
        const types = comp.types;
        if (types.includes('locality')) city = comp.long_name;
        else if (types.includes('administrative_area_level_1')) state = comp.long_name;
        else if (types.includes('country')) country = comp.long_name;
        else if (types.includes('postal_code')) pincode = comp.long_name;
        else if (types.includes('administrative_area_level_2') && !city) city = comp.long_name;
    });

    if (fieldMappings.city) {
        const el = document.getElementById(fieldMappings.city);
        if (el) el.value = city;
    }
    if (fieldMappings.state) {
        const el = document.getElementById(fieldMappings.state);
        if (el) el.value = state;
    }
    if (fieldMappings.country) {
        const el = document.getElementById(fieldMappings.country);
        if (el) el.value = country;
    }
    if (fieldMappings.pincode) {
        const el = document.getElementById(fieldMappings.pincode);
        if (el) el.value = pincode;
    }
}

function handleCurrentLocation(fieldMappings) {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }

    const btn = document.getElementById('btn-current-location');
    if (btn) btn.disabled = true;

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            const geocoder = new google.maps.Geocoder();

            geocoder.geocode({ location: { lat, lng } }, (results, status) => {
                if (btn) btn.disabled = false;
                if (status === "OK" && results[0]) {
                    fillFieldsFromPlace(results[0], fieldMappings);
                } else {
                    alert("Unable to retrieve address from location.");
                }
            });
        },
        (error) => {
            if (btn) btn.disabled = false;
            console.error("Geolocation error:", error);
            alert("Unable to retrieve your location. Please enter the address manually.");
        },
        { enableHighAccuracy: true, timeout: 5000 }
    );
}

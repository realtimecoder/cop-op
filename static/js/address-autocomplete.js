/**
 * Google Maps Address Autocomplete Utility
 * This utility attaches to a search input and populates related form fields
 * with formatted address, city, pincode, latitude, and longitude.
 */

function initAddressAutocomplete(searchInputId, fieldMappings) {
    const searchInput = document.getElementById(searchInputId);
    if (!searchInput) return;

    const autocomplete = new google.maps.places.Autocomplete(searchInput, {
        types: ['address'],
        componentRestrictions: { country: 'IN' } // Restrict to India as per Co-opSeva context
    });

    autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace();

        if (!place.geometry) {
            console.error("No geometry available for the selected place.");
            return;
        }

        // 1. Formatted Address
        if (fieldMappings.address) {
            const addressField = document.getElementById(fieldMappings.address);
            if (addressField) addressField.value = place.formatted_address;
        }

        // 2. Coordinates
        if (fieldMappings.latitude) {
            const latField = document.getElementById(fieldMappings.latitude);
            if (latField) latField.value = place.geometry.location.lat();
        }
        if (fieldMappings.longitude) {
            const lngField = document.getElementById(fieldMappings.longitude);
            if (lngField) lngField.value = place.geometry.location.lng();
        }

        // 3. Address Components (City, Pincode)
        let city = '';
        let pincode = '';

        place.address_components.forEach(component => {
            const types = component.types;
            if (types.includes('locality')) {
                city = component.long_name;
            } else if (types.includes('postal_code')) {
                pincode = component.long_name;
            } else if (types.includes('administrative_area_level_2') && !city) {
                // Fallback for city if locality is missing
                city = component.long_name;
            }
        });

        if (fieldMappings.city) {
            const cityField = document.getElementById(fieldMappings.city);
            if (cityField) cityField.value = city;
        }
        if (fieldMappings.pincode) {
            const pincodeField = document.getElementById(fieldMappings.pincode);
            if (pincodeField) pincodeField.value = pincode;
        }
    });
}

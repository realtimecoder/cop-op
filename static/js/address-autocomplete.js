/**
 * Google Maps Address Autocomplete Utility
 * This utility attaches to a search input and populates related form fields
 * with formatted address, city, pincode, latitude, and longitude.
 */

function initAddressAutocomplete(searchInputId, fieldMappings) {
    const searchInput = document.getElementById(searchInputId);
    if (!searchInput) return;

    // Initialize autocomplete immediately without requesting browser geolocation
    // This removes the "Allow Location" popup
    setupAutocomplete(searchInput, fieldMappings, null);
}

function setupAutocomplete(searchInput, fieldMappings, bounds) {
    const options = {
        types: [],
        componentRestrictions: { country: 'IN' },
        bounds: bounds,
        strictBounds: false
    };

    const autocomplete = new google.maps.places.Autocomplete(searchInput, options);

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

        // 3. Address Components (City, State, Country, Pincode)
        let city = '';
        let state = '';
        let country = '';
        let pincode = '';

        place.address_components.forEach(component => {
            const types = component.types;
            if (types.includes('locality')) {
                city = component.long_name;
            } else if (types.includes('administrative_area_level_1')) {
                state = component.long_name;
            } else if (types.includes('country')) {
                country = component.long_name;
            } else if (types.includes('postal_code')) {
                pincode = component.long_name;
            } else if (types.includes('administrative_area_level_2') && !city) {
                city = component.long_name;
            }
        });

        if (fieldMappings.city) {
            const cityField = document.getElementById(fieldMappings.city);
            if (cityField) cityField.value = city;
        }
        if (fieldMappings.state) {
            const stateField = document.getElementById(fieldMappings.state);
            if (stateField) stateField.value = state;
        }
        if (fieldMappings.country) {
            const countryField = document.getElementById(fieldMappings.country);
            if (countryField) countryField.value = country;
        }
        if (fieldMappings.pincode) {
            const pincodeField = document.getElementById(fieldMappings.pincode);
            if (pincodeField) pincodeField.value = pincode;
        }
    });
}

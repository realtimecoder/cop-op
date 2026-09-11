/**
 * Google Maps Address Autocomplete Utility
 * This utility attaches to a search input and populates related form fields
 * with formatted address, city, pincode, latitude, and longitude.
 */

function initAddressAutocomplete(searchInputId, fieldMappings) {
    console.log("Initializing Address Autocomplete for:", searchInputId);
    const searchInput = document.getElementById(searchInputId);
    if (!searchInput) {
        console.error("Search input element not found:", searchInputId);
        return;
    }

    // 1. Initialize Autocomplete
    try {
        const autocomplete = new google.maps.places.Autocomplete(searchInput, {
            types: ['address'],
            componentRestrictions: { country: 'IN' }
        });

        autocomplete.addListener('place_changed', () => {
            console.log("Place changed event fired");
            const place = autocomplete.getPlace();
            fillFieldsFromPlace(place, fieldMappings);
        });
        console.log("Autocomplete initialized successfully");
    } catch (e) {
        console.error("Error initializing Google Autocomplete:", e);
    }

    // 2. Initialize "Current Location" button if it exists
    const locationBtn = document.getElementById('btn-current-location');
    if (locationBtn) {
        console.log("Current location button found, adding listener");
        locationBtn.addEventListener('click', () => {
            console.log("Current location button clicked");
            handleCurrentLocation(fieldMappings);
        });
    } else {
        console.warn("Current location button not found in DOM");
    }
}

function fillFieldsFromPlace(place, fieldMappings) {
    console.log("Filling fields from place:", place.formatted_address);
    if (!place.geometry) {
        console.error("No geometry available for the selected place.");
        return;
    }

    // Formatted Address
    if (fieldMappings.address) {
        const el = document.getElementById(fieldMappings.address);
        if (el) {
            el.value = place.formatted_address || '';
            console.log("Address field updated");
        }
    }

    // Coordinates
    if (fieldMappings.latitude) {
        const el = document.getElementById(fieldMappings.latitude);
        if (el) {
            el.value = place.geometry.location.lat();
            console.log("Latitude updated");
        }
    }
    if (fieldMappings.longitude) {
        const el = document.getElementById(fieldMappings.longitude);
        if (el) {
            el.value = place.geometry.location.lng();
            console.log("Longitude updated");
        }
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
    console.log("Handling current location request");
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
            console.log(`Got location: ${lat}, ${lng}`);
            const geocoder = new google.maps.Geocoder();

            geocoder.geocode({ location: { lat, lng } }, (results, status) => {
                if (btn) btn.disabled = false;
                if (status === "OK" && results[0]) {
                    console.log("Reverse geocoding successful");
                    fillFieldsFromPlace(results[0], fieldMappings);
                } else {
                    console.error("Geocoding failed:", status);
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

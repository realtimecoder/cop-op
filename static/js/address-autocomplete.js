/**
 * Google Maps Address Autocomplete Utility
 * This utility attaches to a search input and populates related form fields
 * with formatted address, city, pincode, latitude, and longitude.
 */

function initAddressAutocomplete(searchInputId, fieldMappings) {
    console.log("Initializing Address Autocomplete for:", searchInputId);
    const searchInput = document.getElementById(searchInputId);
    if (!searchInput) {
        console.error("Search input not found:", searchInputId);
        return;
    }

    try {
        // CHANGED: Removed types: ['address'] to allow a broader range of results
        // including localities, landmarks, and establishments (like Zomato/Swiggy)
        const autocomplete = new google.maps.places.Autocomplete(searchInput, {
            componentRestrictions: { country: 'IN' }
        });

        autocomplete.addListener('place_changed', () => {
            const place = autocomplete.getPlace();
            console.log("Place selected:", place);

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

            // 3. Address Components (City, State, Pincode, Country)
            let city = '';
            let state = '';
            let pincode = '';
            let country = '';

            place.address_components.forEach(component => {
                const types = component.types;

                // Logic to capture city/locality more broadly
                if (types.includes('locality')) {
                    city = component.long_name;
                } else if (types.includes('administrative_area_level_2') && !city) {
                    city = component.long_name;
                } else if (types.includes('sublocality_level_1') && !city) {
                    city = component.long_name;
                }

                if (types.includes('administrative_area_level_1')) {
                    state = component.long_name;
                } else if (types.includes('postal_code')) {
                    pincode = component.long_name;
                } else if (types.includes('country')) {
                    country = component.long_name;
                }
            });

            console.log("Extracted components:", { city, state, pincode, country });

            // Helper to set value for both Text and Select inputs
            const setFieldValue = (id, value) => {
                if (!id) return;
                const field = document.getElementById(id);
                if (!field) return;

                if (field.tagName === 'SELECT') {
                    let exists = false;
                    for (let i = 0; i < field.options.length; i++) {
                        if (field.options[i].value === value) {
                            exists = true;
                            break;
                        }
                    }
                    if (!exists && value) {
                        const opt = document.createElement('option');
                        opt.value = value;
                        opt.textContent = value;
                        field.appendChild(opt);
                    }
                    field.value = value;
                    field.dispatchEvent(new Event('change'));
                } else {
                    field.value = value;
                }
            };

            setFieldValue(fieldMappings.city, city);
            setFieldValue(fieldMappings.state, state);
            setFieldValue(fieldMappings.pincode, pincode);
            setFieldValue(fieldMappings.country, country);
        });
    } catch (e) {
        console.error("Google Maps Autocomplete initialization failed:", e);
    }
}

/**
 * Reverse Geocoding Utility
 * Converts lat/lng to a human-readable address and components.
 */
async function reverseGeocode(lat, lng, fieldMappings) {
    console.log("Performing reverse geocode for:", lat, lng);
    const geocoder = new google.maps.Geocoder();
    try {
        const response = await geocoder.geocode({ location: { lat, lng } });
        if (response.results && response.results[0]) {
            const result = response.results[0];
            console.log("Reverse geocode result:", result);

            if (fieldMappings.address) {
                const addressField = document.getElementById(fieldMappings.address);
                if (addressField) addressField.value = result.formatted_address;
            }

            let city = '';
            let state = '';
            let pincode = '';
            let country = '';

            result.address_components.forEach(component => {
                const types = component.types;
                if (types.includes('locality')) {
                    city = component.long_name;
                } else if (types.includes('administrative_area_level_2') && !city) {
                    city = component.long_name;
                } else if (types.includes('sublocality_level_1') && !city) {
                    city = component.long_name;
                }

                if (types.includes('administrative_area_level_1')) {
                    state = component.long_name;
                } else if (types.includes('postal_code')) {
                    pincode = component.long_name;
                } else if (types.includes('country')) {
                    country = component.long_name;
                }
            });

            const setFieldValue = (id, value) => {
                if (!id) return;
                const field = document.getElementById(id);
                if (!field) return;
                if (field.tagName === 'SELECT') {
                    let exists = false;
                    for (let i = 0; i < field.options.length; i++) {
                        if (field.options[i].value === value) {
                            exists = true;
                            break;
                        }
                    }
                    if (!exists && value) {
                        const opt = document.createElement('option');
                        opt.value = value;
                        opt.textContent = value;
                        field.appendChild(opt);
                    }
                    field.value = value;
                    field.dispatchEvent(new Event('change'));
                } else {
                    field.value = value;
                }
            };

            setFieldValue(fieldMappings.city, city);
            setFieldValue(fieldMappings.state, state);
            setFieldValue(fieldMappings.pincode, pincode);
            setFieldValue(fieldMappings.country, country);
            return true;
        }
    } catch (error) {
        console.error("Reverse Geocoding failed:", error);
    }
    return false;
}

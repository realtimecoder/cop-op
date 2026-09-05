/**
 * Co-opSeva Interactive Onboarding Tour
 * Powered by Driver.js
 */

const TOUR_CONFIGS = {
    customer: [
        {
            element: '.main-nav a[href*="catalog:category_list"]',
            popover: {
                title: '🌟 Browse Services',
                description: 'Explore our wide range of verified cooperative services. From cleaning to technical work, everything is here!',
                position: 'bottom'
            }
        },
        {
            element: '.hero-search input.input-field',
            popover: {
                title: '🔍 Quick Search',
                description: 'Looking for something specific? Just type the service you need right here.',
                position: 'bottom'
            }
        },
        {
            element: '.main-nav a[href*="bookings:my_bookings"]',
            popover: {
                title: '📅 My Bookings',
                description: 'Keep track of your active and past bookings all in one place.',
                position: 'bottom'
            }
        },
        {
            element: '.main-nav a[href*="payments:wallet_dashboard"]',
            popover: {
                title: '💰 Digital Wallet',
                description: 'Manage your payments and top up your wallet for seamless bookings.',
                position: 'bottom'
            }
        },
        {
            element: '.header-actions a[href*="accounts:profile"]',
            popover: {
                title: '👤 Your Profile',
                description: 'Manage your details, preferences, and account settings here.',
                position: 'left'
            }
        }
    ],
    worker: [
        {
            element: '.main-nav a[href*="workers:my_dashboard"]',
            popover: {
                title: '📈 Worker Dashboard',
                description: 'Your command center! See your stats, upcoming work, and active bookings.',
                position: 'bottom'
            }
        },
        {
            element: '.data-table',
            popover: {
                title: '🛠 Your Bookings',
                description: 'View and manage your scheduled jobs. Ensure you arrive on time for a 5-star rating!',
                position: 'top'
            }
        },
        {
            element: '.grid.grid-4 .card',
            popover: {
                title: '💸 Earnings',
                description: 'Track your income and see how much you have earned through the cooperative.',
                position: 'bottom'
            }
        }
    ],
    admin: [
        {
            element: '.main-nav a[href*="dashboard:overview"]',
            popover: {
                title: '🏛 Admin Hub',
                description: 'The heart of platform governance. Monitor everything from here.',
                position: 'bottom'
            }
        },
        {
            element: 'a[href*="dashboard:customer_list"], a[href*="dashboard:worker_list"]',
            popover: {
                title: '👥 User Management',
                description: 'Manage verified workers and customers across the entire federation.',
                position: 'bottom'
            }
        },
        {
            element: 'a[href*="dashboard:pricing_config"]',
            popover: {
                title: '⚙️ Platform Controls',
                description: 'Configure fair pricing and system-wide settings to maintain transparency.',
                position: 'bottom'
            }
        }
    ]
};

async function initTour() {
    const userRole = document.body.dataset.userRole;
    const hasCompletedTour = document.body.dataset.hasCompletedTour === 'true';

    if (!userRole || hasCompletedTour) return;

    const role = userRole === 'platform_admin' ? 'admin' : userRole;
    const steps = TOUR_CONFIGS[role];

    if (!steps) return;

    const driver = window.driver.js.driver({
        showProgress: true,
        steps: steps,
        onDevDebug: (element, step, { config }) => {
            console.log(`Tour step ${step} on element:`, element);
        },
        onClose: async () => {
            await markTourComplete();
        },
        onNext: async (element, step, { config }) => {
            if (step === steps.length - 1) {
                // Last step logic if needed
            }
        }
    });

    driver.drive();
}

async function markTourComplete() {
    try {
        await fetch('/accounts/tour/complete/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({})
        });
    } catch (e) {
        console.error("Failed to mark tour as complete", e);
    }
}

async function resetTour() {
    try {
        const res = await fetch('/accounts/tour/reset/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({})
        });
        if (res.ok) {
            window.location.reload();
        }
    } catch (e) {
        console.error("Failed to reset tour", e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initTour();

    const retakeBtn = document.getElementById('retake-tour-btn');
    if (retakeBtn) {
        retakeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            resetTour();
        });
    }
});

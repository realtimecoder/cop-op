"""
Razorpay TEST MODE integration.

Set these two environment variables to enable real Razorpay checkout
(use your Razorpay **test** key pair, from the Razorpay Dashboard →
Settings → API Keys, with "Test Mode" toggled on):

    export RAZORPAY_KEY_ID="rzp_test_xxxxxxxxxxxx"
    export RAZORPAY_KEY_SECRET="xxxxxxxxxxxxxxxxxxxx"

If these are not set, the platform automatically falls back to a clearly
labelled simulated payment (Payment.is_simulated = True) so the booking
flow never breaks — this mirrors how the Google Maps integration degrades
gracefully without a key.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import razorpay
except ImportError:  # pragma: no cover
    razorpay = None


def is_configured():
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and razorpay is not None)


def get_client():
    if not is_configured():
        return None
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_order(amount_rupees, receipt):
    """Creates a Razorpay order in test mode. Amount must be in paise."""
    client = get_client()
    if not client:
        return None
    try:
        order = client.order.create({
            'amount': int(round(float(amount_rupees) * 100)),
            'currency': 'INR',
            'receipt': receipt,
            'payment_capture': 1,
        })
        return order
    except Exception as exc:  # pragma: no cover
        logger.warning("Razorpay order creation failed: %s", exc)
        return None


def verify_payment_signature(order_id, payment_id, signature):
    client = get_client()
    if not client:
        return False
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature,
        })
        return True
    except Exception as exc:
        logger.warning("Razorpay signature verification failed: %s", exc)
        return False

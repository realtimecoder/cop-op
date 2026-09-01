from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Wallet, WalletTransaction

@login_required
def wallet_dashboard(request):
    """View for users to check their balance and transaction history."""
    wallet, _created = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')

    return render(request, 'payments/wallet.html', {
        'wallet': wallet,
        'transactions': transactions,
    })

@login_required
def withdraw_funds(request):
    """Handle fund withdrawal requests."""
    wallet = getattr(request.user, 'wallet', None)
    if not wallet:
        messages.error(request, "Wallet not found.")
        return redirect('payments:wallet_dashboard')

    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")

            wallet.debit(amount, transaction_type='withdrawal')
            messages.success(request, f"Successfully withdrawn ₹{amount:.2f} to your linked account.")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, "An error occurred during withdrawal.")

    return redirect('payments:wallet_dashboard')

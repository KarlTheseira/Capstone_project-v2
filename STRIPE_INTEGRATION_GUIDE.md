# Stripe Payment Integration - FlashStudio

## Overview
FlashStudio now includes a comprehensive Stripe payment integration with both fake/test and real payment capabilities. This system allows customers to securely checkout using credit/debit cards through Stripe's secure payment platform.

## Features Implemented

### 🔄 **Dual Payment Options**
- **Stripe Checkout**: Secure card payments with Stripe's hosted checkout
- **Direct Order**: Traditional order placement for alternative payment methods

### 🛡️ **Security & Testing**
- Fake Stripe checkout for development/testing
- Real Stripe integration ready (just update API keys)
- SSL-encrypted payment processing
- PCI-compliant payment handling

### 📱 **User Experience**
- Seamless checkout flow from cart to confirmation
- Mobile-responsive payment pages
- Real-time form validation
- Toast notifications for user feedback
- Payment outcome simulation (success/failure/cancel)

## File Structure

```
routes/
├── payment.py              # Stripe payment routes and logic
templates/payment/
├── fake_checkout.html      # Test Stripe checkout page
├── success.html           # Payment success page  
└── cancel.html           # Payment cancelled/failed page
templates/
└── checkout.html          # Enhanced checkout with Stripe option
config.py                  # Stripe API keys and configuration
```

## Configuration

### Environment Variables
```bash
# Stripe Configuration (Test Mode)
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Payment Settings
CURRENCY=sgd
PAYMENT_SUCCESS_URL=http://127.0.0.1:5001/payment/success
PAYMENT_CANCEL_URL=http://127.0.0.1:5001/payment/cancel
```

### Fake Testing (Current Setup)
The system is configured with fake Stripe keys for testing:
- Uses `sk_test_fake_*` pattern to trigger fake mode
- No real payments are processed
- Allows testing all payment outcomes

## Routes

### Payment Routes (`/payment/`)
- `POST /payment/create-checkout-session` - Create Stripe checkout session
- `GET /payment/fake-checkout` - Fake Stripe checkout page (testing)
- `POST /payment/fake-checkout/complete` - Complete fake checkout
- `GET /payment/success` - Payment success page
- `GET /payment/cancel` - Payment cancelled/failed page
- `POST /payment/webhook` - Stripe webhook handler

## Usage Flow

### 1. Customer Journey
1. Add items to cart (`/cart`)
2. Proceed to checkout (`/checkout`)
3. Choose payment method:
   - **Stripe Checkout**: Redirects to secure payment page
   - **Direct Order**: Creates order for manual payment
4. Complete payment and receive confirmation

### 2. Testing Fake Payments
1. Add products to cart
2. Go to checkout and click "Pay with Stripe"
3. On fake checkout page, select desired outcome:
   - ✅ **Success**: Simulates successful payment
   - ❌ **Failure**: Simulates declined card
   - ⚠️ **Cancel**: Simulates cancelled payment
4. View results on success/cancel pages

### 3. Order Management
- Orders are created with `pending` status during checkout
- Status updates to `paid` on successful payment
- Status updates to `failed` or `cancelled` on failures
- Admin can view all orders in `/admin/orders`

## Real Stripe Integration

### To Enable Real Payments:
1. Update `config.py` with real Stripe API keys:
```python
STRIPE_PUBLISHABLE_KEY = "pk_live_your_real_key"
STRIPE_SECRET_KEY = "sk_live_your_real_key"
```

2. Update `StripeService.create_checkout_session()` in `payment.py`:
```python
# Uncomment real Stripe session creation
checkout_session = stripe.checkout.Session.create(**session_data)
return checkout_session
```

3. Configure webhook endpoint:
```python
STRIPE_WEBHOOK_SECRET = "whsec_your_webhook_secret"
```

## Database Changes
- `Order.stripe_payment_intent`: Stores Stripe payment intent ID
- `Order.status`: Tracks payment status (pending/paid/failed/cancelled)

## Security Features
- CSRF protection on all forms
- Server-side validation of all inputs
- Secure session management
- PCI-compliant payment processing (when using real Stripe)
- SSL encryption for all payment data

## Testing Scenarios

### Successful Payment Flow
1. Cart → Checkout → Stripe Checkout → Select "Success" → Success Page
2. Order status: `paid`
3. Cart: Cleared
4. Confirmation email: Sent (if configured)

### Failed Payment Flow  
1. Cart → Checkout → Stripe Checkout → Select "Failure" → Cancel Page
2. Order status: `failed` 
3. Cart: Preserved
4. User can retry payment

### Cancelled Payment Flow
1. Cart → Checkout → Stripe Checkout → Select "Cancel" → Cancel Page
2. Order status: `cancelled`
3. Cart: Preserved  
4. User can return to cart or try different payment method

## Integration with Existing Features
- ✅ Works with existing cart system
- ✅ Integrates with user authentication 
- ✅ Compatible with product catalog
- ✅ Connects to admin order management
- ✅ Supports customization options (size, frame)
- ✅ Maintains order history for logged-in users

## Next Steps for Production
1. **Get Real Stripe Account**: Replace test keys with live keys
2. **Configure Webhooks**: Set up Stripe webhook endpoints  
3. **Email Integration**: Add order confirmation emails
4. **Inventory Management**: Connect payments to inventory updates
5. **Refund System**: Implement refund handling
6. **Analytics**: Add payment analytics and reporting

## Support & Troubleshooting
- All payment errors are logged to Flask logs
- Use fake checkout page to test different scenarios
- Check browser console for JavaScript errors
- Verify cart contents before checkout
- Ensure all required form fields are filled

---

**Status**: ✅ **Implemented and Ready for Testing**
**Last Updated**: October 7, 2025
**Integration**: Complete with fake Stripe checkout for development/testing
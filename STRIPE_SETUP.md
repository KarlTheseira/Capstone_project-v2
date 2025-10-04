# Stripe Payment Integration Setup Guide

This guide covers setting up Stripe payments for FlashStudio in development and production (Kubernetes/Azure).

## 🚀 Quick Start

### 1. Get Stripe API Keys

1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe Dashboard:
   - **Publishable Key**: `pk_test_...` (for frontend)
   - **Secret Key**: `sk_test_...` (for backend)
   - **Webhook Secret**: `whsec_...` (for webhook verification)

### 2. Development Setup

#### Environment Variables
Create a `.env` file in your project root:

```bash
# Stripe Configuration (Test Keys)
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Payment Configuration
CURRENCY=sgd
PAYMENT_SUCCESS_URL=/payment-success
PAYMENT_CANCEL_URL=/cart
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Run Database Migration
```bash
python migrate_stripe_fields.py
```

#### Start Development Server
```bash
python app.py
```

### 3. Webhook Setup (Development)

For development, you'll need to set up webhook forwarding:

#### Using Stripe CLI (Recommended)
```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to localhost:5001/payment/webhooks/stripe
```

#### Using ngrok (Alternative)
```bash
# Install ngrok: https://ngrok.com/
ngrok http 5001
# Copy the HTTPS URL and add /payment/webhooks/stripe
# Add this URL to your Stripe Dashboard webhooks
```

## 🏗️ Production Setup (Kubernetes/Azure)

### 1. Create Stripe Secrets in Kubernetes

#### Option A: Using kubectl command
```bash
kubectl create secret generic stripe-secrets \
  --from-literal=STRIPE_PUBLISHABLE_KEY=pk_live_your_live_key \
  --from-literal=STRIPE_SECRET_KEY=sk_live_your_live_key \
  --from-literal=STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret \
  --namespace=flash
```

#### Option B: Using secret manifest
```bash
# Edit k8-deploy/stripe-secrets.yaml with your base64 encoded keys
kubectl apply -f k8-deploy/stripe-secrets.yaml
```

### 2. Deploy Updated Application
```bash
kubectl apply -f k8-deploy/deployment.yaml
kubectl apply -f k8-deploy/service.yaml
```

### 3. Configure Production Webhooks

1. Go to Stripe Dashboard → Webhooks
2. Add endpoint: `https://your-domain.com/payment/webhooks/stripe`
3. Select events to send:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `payment_intent.requires_action`

## 📋 Testing the Integration

### Test Cards (Stripe Test Mode)

| Card Number | Description |
|-------------|-------------|
| 4242424242424242 | Visa - Succeeds |
| 4000000000000002 | Visa - Declined |
| 4000000000009995 | Visa - Insufficient funds |
| 4000000000000069 | Visa - Expired card |

### Test Flow
1. Add items to cart
2. Go to checkout
3. Fill customer information
4. Click "Pay Securely" 
5. Use test card: `4242424242424242`
6. Any future expiry date and CVC
7. Verify payment success page

## 🔒 Security Best Practices

### Environment Configuration
- ✅ **DO**: Use environment variables for API keys
- ✅ **DO**: Use Kubernetes secrets in production
- ❌ **DON'T**: Commit API keys to version control
- ❌ **DON'T**: Use test keys in production

### Webhook Security
- ✅ **DO**: Verify webhook signatures
- ✅ **DO**: Use HTTPS endpoints only
- ✅ **DO**: Implement idempotency for webhook handlers
- ❌ **DON'T**: Trust webhook data without verification

### Payment Processing
- ✅ **DO**: Validate amounts server-side
- ✅ **DO**: Use Payment Intents for stronger authentication
- ✅ **DO**: Handle failed payments gracefully
- ❌ **DON'T**: Store sensitive card data

## 🐛 Troubleshooting

### Common Issues

#### 1. "Stripe not configured" error
- **Cause**: Missing or incorrect API keys
- **Solution**: Verify environment variables are set correctly

#### 2. Webhook signature verification failed
- **Cause**: Incorrect webhook secret or payload
- **Solution**: Check webhook secret matches Stripe dashboard

#### 3. Payment intent creation fails
- **Cause**: Invalid currency or amount
- **Solution**: Verify currency is supported and amount > 0

#### 4. CORS errors in development
- **Cause**: Stripe.js loading issues
- **Solution**: Ensure proper HTTPS configuration

### Debug Logging

Enable debug logging in development:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Stripe Dashboard

Monitor payments and debug issues:
- **Payments**: View all payment attempts
- **Logs**: See API request logs
- **Webhooks**: Monitor webhook deliveries
- **Balance**: Track funds and payouts

## 📈 Monitoring & Analytics

### Key Metrics to Track
- Payment success rate
- Average order value
- Failed payment reasons
- Webhook delivery success

### Stripe Dashboard Features
- Real-time payment monitoring
- Revenue analytics
- Customer insights
- Dispute management

## 🔄 Going Live Checklist

### Pre-Production
- [ ] Test with Stripe test cards
- [ ] Verify webhook handling
- [ ] Test error scenarios
- [ ] Review security configuration
- [ ] Test payment flow end-to-end

### Production Deployment
- [ ] Switch to live Stripe keys
- [ ] Configure production webhooks
- [ ] Update CORS settings if needed
- [ ] Monitor initial transactions
- [ ] Set up alerting for failed payments

### Post-Deployment
- [ ] Verify payments are processing
- [ ] Check webhook delivery logs
- [ ] Monitor error rates
- [ ] Test customer support flow

## 🆘 Support

### Stripe Resources
- [Stripe Documentation](https://stripe.com/docs)
- [Stripe Support](https://support.stripe.com)
- [Stripe Status Page](https://status.stripe.com)

### Application Support
- Check application logs for errors
- Verify Kubernetes pod status
- Monitor webhook delivery in Stripe Dashboard
- Review payment intent details in Stripe Dashboard

## 🔗 Related Documentation

- [Stripe Payment Intents API](https://stripe.com/docs/payments/payment-intents)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [Stripe Elements](https://stripe.com/docs/stripe-js)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
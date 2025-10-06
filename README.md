# Flash Studio - Video Production Company Website

A comprehensive Flask-based web application for a video production company, featuring e-commerce capabilities, admin dashboard with analytics, booking system, and content management.

## Features

### Core Functionality
- **Product Catalog**: Video services and digital products with customization options
- **E-commerce**: Shopping cart, checkout process, order management
- **User Authentication**: Customer registration and login system
- **Admin Dashboard**: Comprehensive analytics and content management
- **Booking System**: Service booking with calendar integration
- **Quote Requests**: Customer inquiry and quotation system

### Analytics Dashboard
- Revenue trends and financial metrics
- Service popularity tracking
- Customer analytics and booking statistics
- Interactive charts powered by Chart.js
- Real-time business intelligence

### Technical Features
- Flask 3.x with Blueprint architecture
- SQLAlchemy ORM with database migrations
- Responsive Bootstrap 5 UI
- Media file management and serving
- Professional admin interface

## Prerequisites

- Python 3.11+ (3.12 recommended)
- Git for version control
- Virtual environment support

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd Capstone
```

2. **Create and activate virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Set up environment variables (optional):**
Create a `.env` file in the root directory:
```bash
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False  # Set to True for development
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-password
SQLALCHEMY_DATABASE_URI=sqlite:///filmcompany.db
```

5. **Initialize the database:**
```bash
python create_tables.py
```

6. **Optional - Load sample data:**
```bash
python create_sample_analytics_data.py
```

7. **Run the application:**
```bash
python app.py
```

Visit `http://127.0.0.1:5001` to view the application.

## Configuration

The application uses environment variables for configuration. Key settings include:

- `FLASK_SECRET_KEY`: Session encryption key (required)
- `FLASK_DEBUG`: Enable/disable debug mode
- `ADMIN_USERNAME`/`ADMIN_PASSWORD`: Admin login credentials
- `SQLALCHEMY_DATABASE_URI`: Database connection string

Default values are provided for development, but should be overridden in production.

## Database

The application uses SQLAlchemy with support for multiple database engines. By default, it uses SQLite for development.

### Migrations
Database migrations are handled through Flask-Migrate:
```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade
```

## Project Structure

```
├── app.py                 # Main application file
├── config.py             # Configuration settings
├── models.py             # Database models and analytics engine
├── requirements.txt      # Python dependencies
├── routes/               # Application blueprints
│   ├── admin.py         # Admin dashboard and management
│   ├── auth.py          # Authentication routes
│   ├── public.py        # Public-facing routes
│   └── video.py         # Video content management
├── templates/            # Jinja2 templates
├── static/              # Static assets (CSS, JS, images)
├── utils/               # Utility modules
├── services/            # Service layer
└── migrations/          # Database migration files
```

## Admin Panel

Access the admin panel at `/admin` with credentials:
- Username: admin (configurable)
- Password: admin (configurable via environment)

### Admin Features
- **Analytics Dashboard**: Revenue, booking, and performance metrics
- **Order Management**: View and manage customer orders
- **Product Management**: Add, edit, and customize products
- **Booking Management**: Handle service bookings
- **Quote Management**: Process customer inquiries

## Development

### Adding Sample Data
Use the included script to populate the database with sample analytics data:
```bash
python create_sample_analytics_data.py
```

### Development Mode
For development, set `FLASK_DEBUG=True` in your environment or `.env` file to enable:
- Hot reloading
- Debug toolbar
- Detailed error messages

### Code Style
The project follows standard Python conventions:
- Use meaningful variable names
- Follow PEP 8 guidelines
- Add docstrings for functions and classes

## Deployment

### Production Considerations
1. **Security**:
   - Use strong SECRET_KEY
   - Set FLASK_DEBUG=False
   - Use HTTPS in production
   - Secure admin credentials

2. **Database**:
   - Use PostgreSQL or MySQL for production
   - Configure proper database URLs
   - Run migrations before deployment

3. **Static Files**:
   - Configure proper static file serving
   - Consider using a CDN for media files

### Environment Variables for Production
```bash
FLASK_SECRET_KEY=secure-random-key
FLASK_DEBUG=False
SQLALCHEMY_DATABASE_URI=postgresql://user:pass@localhost/dbname
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-admin-password
```

## API Endpoints

### Public Routes
- `/` - Homepage
- `/products` - Product catalog
- `/cart` - Shopping cart
- `/checkout` - Checkout process
- `/auth/login` - User login
- `/auth/register` - User registration

### Admin Routes (Authentication Required)
- `/admin` - Admin dashboard
- `/admin/analytics` - Analytics data API
- `/admin/orders` - Order management
- `/admin/products` - Product management
- `/admin/bookings` - Booking management

## Payments (Dummy Mode)

The application currently ships with a safe, non-transactional dummy payment provider that simulates a minimal subset of Stripe's PaymentIntent lifecycle for local development and UI integration testing.

### How It Works
- Endpoint: `POST /api/payments/create-intent` creates an in-memory intent and a provisional `Order` plus its `OrderItem` records.
- Endpoint: `POST /api/payments/confirm` transitions the intent to `succeeded` and marks the related `Order.status` as `paid`.
- Endpoint: `GET /api/payments/intent/<id>` returns current intent details.
- No real card details are processed; amounts are derived from product prices to exercise order math & analytics.

### Configuration
Environment variable: `PAYMENTS_PROVIDER` (defaults to `dummy`).

Planned real integration:
```
PAYMENTS_PROVIDER=stripe
STRIPE_API_KEY=sk_live_xxx
```
When Stripe support is added, the same endpoints will return live Stripe objects while preserving the contract used by the dummy provider.

### Sample cURL Flow
```
curl -X POST http://127.0.0.1:5001/api/payments/create-intent \
   -H 'Content-Type: application/json' \
   -d '{"email":"buyer@example.com","items":[{"product_id":1,"quantity":2}],"currency":"usd"}'

curl -X POST http://127.0.0.1:5001/api/payments/confirm \
   -H 'Content-Type: application/json' \
   -d '{"payment_intent_id":"<intent_id_from_previous_response>"}'
```

### Notes
- Field `stripe_payment_intent` on `Order` is reused to store dummy intent IDs for a smooth future transition.
- Analytics (revenue, etc.) treat dummy-paid orders identically, enabling end-to-end dashboard testing.
- Never enable real Stripe in production without adding secret management and webhook signature validation.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## License

This project is available under the MIT License. See LICENSE file for details.

## Support

For questions or support, please open an issue in the GitHub repository.

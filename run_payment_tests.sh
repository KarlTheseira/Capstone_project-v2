#!/bin/bash

# FlashStudio Payment Testing Suite
# Comprehensive testing for all payment system components

echo "🎬 FlashStudio Payment Testing Suite"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "FAIL")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Check if virtual environment exists and is activated
check_environment() {
    print_status "INFO" "Checking environment setup..."
    
    if [ ! -d "venv" ]; then
        print_status "FAIL" "Virtual environment not found. Please run: python3 -m venv venv"
        exit 1
    fi
    
    # Activate virtual environment if not already active
    if [ -z "$VIRTUAL_ENV" ]; then
        print_status "INFO" "Activating virtual environment..."
        source venv/bin/activate
    fi
    
    # Check if required packages are installed
    if ! python -c "import flask, stripe, requests" 2>/dev/null; then
        print_status "WARNING" "Installing required test dependencies..."
        pip install flask stripe requests unittest-xml-reporting coverage
    fi
    
    print_status "SUCCESS" "Environment setup complete"
}

# Start the Flask application in background for testing
start_test_server() {
    print_status "INFO" "Starting test server..."
    
    # Set test environment variables
    export FLASK_ENV=testing
    export STRIPE_SECRET_KEY="sk_test_fake_key_for_testing"
    export STRIPE_PUBLISHABLE_KEY="pk_test_fake_key_for_testing"
    export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=devtest;AccountKey=test;EndpointSuffix=core.windows.net"
    export FLASK_SECRET_KEY="test-secret-key-for-testing"
    
    # Start server in background
    python app.py &
    SERVER_PID=$!
    
    # Wait for server to start
    sleep 3
    
    # Check if server is running
    if curl -s http://localhost:5001/ > /dev/null; then
        print_status "SUCCESS" "Test server started (PID: $SERVER_PID)"
        return 0
    else
        print_status "FAIL" "Failed to start test server"
        kill $SERVER_PID 2>/dev/null
        return 1
    fi
}

# Stop the test server
stop_test_server() {
    if [ ! -z "$SERVER_PID" ]; then
        print_status "INFO" "Stopping test server..."
        kill $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null
        print_status "SUCCESS" "Test server stopped"
    fi
}

# Run unit tests
run_unit_tests() {
    print_status "INFO" "Running unit tests..."
    echo ""
    
    # Create test results directory
    mkdir -p test_results
    
    # Run unit tests with coverage
    if command -v coverage &> /dev/null; then
        coverage run --source=. -m pytest tests/test_payment_flows.py -v --tb=short
        coverage report --show-missing
        coverage html -d test_results/coverage_html
        print_status "SUCCESS" "Unit tests completed with coverage report"
    else
        python -m pytest tests/test_payment_flows.py -v --tb=short
        print_status "SUCCESS" "Unit tests completed"
    fi
    
    echo ""
}

# Run API integration tests
run_api_tests() {
    print_status "INFO" "Running API integration tests..."
    echo ""
    
    # Run API tests
    python tests/test_payment_api.py
    
    print_status "SUCCESS" "API tests completed"
    echo ""
}

# Generate test report
generate_report() {
    print_status "INFO" "Generating test report..."
    
    cat > test_results/test_report.md << EOF
# FlashStudio Payment System Test Report

**Generated:** $(date)
**Test Environment:** Testing

## Test Summary

### Unit Tests
- **Location:** \`tests/test_payment_flows.py\`
- **Coverage:** See \`test_results/coverage_html/index.html\`
- **Tests Include:**
  - Payment Intent Creation
  - Payment Confirmation
  - Stripe Webhook Handling
  - Edge Cases and Error Scenarios
  - Complete Payment Flow Integration

### API Integration Tests
- **Location:** \`tests/test_payment_api.py\`
- **Tests Include:**
  - Payment Endpoint Availability
  - Response Time Measurement
  - Load Testing
  - Error Handling Validation

### System Health Checks
- Server Availability
- Payment Endpoint Accessibility
- Analytics Dashboard Functionality

## Test Results

Check the console output above for detailed test results.

## Coverage Report

Open \`test_results/coverage_html/index.html\` in your browser to view the detailed coverage report.

## Recommendations

1. **For Production:** Ensure all tests pass before deploying
2. **Monitoring:** Set up continuous testing in CI/CD pipeline
3. **Performance:** Monitor API response times in production
4. **Security:** Validate webhook signatures in production environment

EOF

    print_status "SUCCESS" "Test report generated: test_results/test_report.md"
}

# Cleanup function
cleanup() {
    stop_test_server
    deactivate 2>/dev/null || true
}

# Set up cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    # Check command line arguments
    case "${1:-all}" in
        "unit")
            check_environment
            run_unit_tests
            ;;
        "api")
            check_environment
            if start_test_server; then
                run_api_tests
            fi
            ;;
        "health")
            check_environment
            if start_test_server; then
                python -c "from tests.test_payment_api import PaymentSystemValidator; PaymentSystemValidator().check_system_health()"
            fi
            ;;
        "all"|*)
            check_environment
            run_unit_tests
            if start_test_server; then
                run_api_tests
            fi
            generate_report
            ;;
    esac
}

# Help message
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "FlashStudio Payment Testing Suite"
    echo ""
    echo "Usage: $0 [test-type]"
    echo ""
    echo "Test Types:"
    echo "  all     - Run all tests (default)"
    echo "  unit    - Run unit tests only"
    echo "  api     - Run API integration tests only"
    echo "  health  - Run system health check only"
    echo ""
    echo "Examples:"
    echo "  $0              # Run all tests"
    echo "  $0 unit         # Run unit tests only"
    echo "  $0 api          # Run API tests only"
    echo "  $0 health       # System health check"
    exit 0
fi

# Run main function
main "$@"
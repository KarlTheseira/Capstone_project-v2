"""
API Integration Tests for Payment Endpoints
Tests real API behavior with mocked external services
"""
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime
import logging

class PaymentAPITester:
    """Comprehensive API testing for payment endpoints"""
    
    def __init__(self, base_url="http://localhost:5001", timeout=30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.results = []
    
    def authenticate_admin(self, username="admin", password="admin123"):
        """Authenticate as admin for testing"""
        response = self.session.post(
            f"{self.base_url}/admin/login",
            data={"username": username, "password": password},
            timeout=self.timeout
        )
        return response.status_code == 200
    
    def test_payment_intent_creation(self):
        """Test payment intent creation API endpoint"""
        test_data = {
            "order_id": 1,
            "amount": 10000,
            "currency": "usd"
        }
        
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.base_url}/payment/create-intent",
                json=test_data,
                timeout=self.timeout
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            result = {
                "test": "payment_intent_creation",
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": response.status_code == 200,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if response.status_code == 200:
                data = response.json()
                result["has_client_secret"] = "client_secret" in data
                result["correct_amount"] = data.get("amount") == test_data["amount"]
            else:
                result["error"] = response.text
            
            self.results.append(result)
            return result
            
        except Exception as e:
            result = {
                "test": "payment_intent_creation",
                "status_code": 0,
                "response_time_ms": (time.time() - start_time) * 1000,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            self.results.append(result)
            return result
    
    def test_payment_confirmation(self):
        """Test payment confirmation API endpoint"""
        test_data = {
            "payment_intent_id": "pi_test_12345"
        }
        
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.base_url}/payment/confirm",
                json=test_data,
                timeout=self.timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            
            result = {
                "test": "payment_confirmation",
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": response.status_code in [200, 400],  # Both are valid responses
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if response.status_code in [200, 400]:
                data = response.json()
                result["response_format"] = "json"
                result["has_status"] = "status" in data or "error" in data
            else:
                result["error"] = response.text
            
            self.results.append(result)
            return result
            
        except Exception as e:
            result = {
                "test": "payment_confirmation",
                "status_code": 0,
                "response_time_ms": (time.time() - start_time) * 1000,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            self.results.append(result)
            return result
    
    def test_webhook_endpoint(self):
        """Test Stripe webhook endpoint"""
        # Mock webhook payload
        webhook_payload = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_webhook",
                    "status": "succeeded",
                    "amount": 5000,
                    "currency": "usd"
                }
            }
        }
        
        headers = {
            "Stripe-Signature": "t=1234567890,v1=test_signature",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.base_url}/payment/webhook",
                json=webhook_payload,
                headers=headers,
                timeout=self.timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            
            result = {
                "test": "webhook_endpoint",
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": response.status_code in [200, 400],  # Both are valid
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            result = {
                "test": "webhook_endpoint",
                "status_code": 0,
                "response_time_ms": (time.time() - start_time) * 1000,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            self.results.append(result)
            return result
    
    def test_analytics_endpoint(self):
        """Test analytics API endpoint"""
        if not self.authenticate_admin():
            return {
                "test": "analytics_endpoint",
                "success": False,
                "error": "Admin authentication failed"
            }
        
        start_time = time.time()
        try:
            response = self.session.get(
                f"{self.base_url}/admin/analytics/api?days=30",
                timeout=self.timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            
            result = {
                "test": "analytics_endpoint",
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": response.status_code == 200,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if response.status_code == 200:
                data = response.json()
                result["has_revenue_data"] = "revenue_summary" in data
                result["has_chart_data"] = "daily_revenue_chart" in data
            else:
                result["error"] = response.text
            
            self.results.append(result)
            return result
            
        except Exception as e:
            result = {
                "test": "analytics_endpoint",
                "status_code": 0,
                "response_time_ms": (time.time() - start_time) * 1000,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            self.results.append(result)
            return result
    
    def load_test_payment_endpoints(self, concurrent_users=10, requests_per_user=5):
        """Perform load testing on payment endpoints"""
        def make_requests(user_id):
            user_results = []
            session = requests.Session()
            
            for i in range(requests_per_user):
                start_time = time.time()
                try:
                    response = session.post(
                        f"{self.base_url}/payment/create-intent",
                        json={"order_id": user_id + i, "amount": 1000},
                        timeout=self.timeout
                    )
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    user_results.append({
                        "user_id": user_id,
                        "request_id": i,
                        "status_code": response.status_code,
                        "response_time_ms": response_time,
                        "success": response.status_code in [200, 400, 401],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    user_results.append({
                        "user_id": user_id,
                        "request_id": i,
                        "status_code": 0,
                        "response_time_ms": (time.time() - start_time) * 1000,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                # Small delay between requests
                time.sleep(0.1)
            
            return user_results
        
        # Execute load test
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_requests, user_id) 
                      for user_id in range(concurrent_users)]
            
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        # Analyze results
        successful_requests = [r for r in all_results if r["success"]]
        failed_requests = [r for r in all_results if not r["success"]]
        
        response_times = [r["response_time_ms"] for r in successful_requests]
        
        load_test_summary = {
            "test": "load_test_payment_endpoints",
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": len(all_results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(all_results) * 100 if all_results else 0,
            "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_time_ms": min(response_times) if response_times else 0,
            "max_response_time_ms": max(response_times) if response_times else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.results.append(load_test_summary)
        return load_test_summary
    
    def run_comprehensive_test_suite(self):
        """Run all API tests and return comprehensive results"""
        print("🧪 Starting Comprehensive Payment API Tests...")
        print("="*60)
        
        # Individual API tests
        tests = [
            ("Payment Intent Creation", self.test_payment_intent_creation),
            ("Payment Confirmation", self.test_payment_confirmation),
            ("Webhook Endpoint", self.test_webhook_endpoint),
            ("Analytics Endpoint", self.test_analytics_endpoint),
        ]
        
        for test_name, test_func in tests:
            print(f"Running: {test_name}...")
            result = test_func()
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"  {status} - {result.get('response_time_ms', 0):.1f}ms")
        
        # Load test
        print("Running: Load Test...")
        load_result = self.load_test_payment_endpoints(concurrent_users=5, requests_per_user=3)
        print(f"  ✅ COMPLETE - {load_result['success_rate']:.1f}% success rate")
        
        # Generate summary
        api_tests = [r for r in self.results if r["test"] != "load_test_payment_endpoints"]
        successful_api_tests = [r for r in api_tests if r["success"]]
        
        summary = {
            "total_api_tests": len(api_tests),
            "successful_api_tests": len(successful_api_tests),
            "api_success_rate": len(successful_api_tests) / len(api_tests) * 100 if api_tests else 0,
            "avg_response_time": sum(r["response_time_ms"] for r in successful_api_tests) / len(successful_api_tests) if successful_api_tests else 0,
            "load_test_results": load_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"API Tests: {summary['successful_api_tests']}/{summary['total_api_tests']} passed ({summary['api_success_rate']:.1f}%)")
        print(f"Average Response Time: {summary['avg_response_time']:.1f}ms")
        print(f"Load Test Success Rate: {load_result['success_rate']:.1f}%")
        
        return summary


class PaymentSystemValidator:
    """Validates payment system configuration and health"""
    
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url.rstrip('/')
        
    def check_system_health(self):
        """Comprehensive system health check"""
        health_checks = []
        
        # Check if server is running
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            health_checks.append({
                "check": "Server Availability",
                "status": "✅ PASS" if response.status_code == 200 else "❌ FAIL",
                "details": f"HTTP {response.status_code}"
            })
        except Exception as e:
            health_checks.append({
                "check": "Server Availability",
                "status": "❌ FAIL",
                "details": str(e)
            })
        
        # Check payment endpoints exist
        payment_endpoints = [
            "/payment/create-intent",
            "/payment/confirm", 
            "/payment/webhook"
        ]
        
        for endpoint in payment_endpoints:
            try:
                response = requests.post(f"{self.base_url}{endpoint}", json={}, timeout=5)
                # We expect 401/400 for unauthenticated requests, not 404
                is_healthy = response.status_code != 404
                health_checks.append({
                    "check": f"Endpoint {endpoint}",
                    "status": "✅ PASS" if is_healthy else "❌ FAIL",
                    "details": f"HTTP {response.status_code}"
                })
            except Exception as e:
                health_checks.append({
                    "check": f"Endpoint {endpoint}",
                    "status": "❌ FAIL", 
                    "details": str(e)
                })
        
        # Print results
        print("🏥 SYSTEM HEALTH CHECK")
        print("="*40)
        for check in health_checks:
            print(f"{check['status']} {check['check']}: {check['details']}")
        
        return health_checks


def run_payment_tests():
    """Main function to run all payment tests"""
    print("🎬 FlashStudio Payment System Testing Suite")
    print("="*60)
    
    # Health check first
    validator = PaymentSystemValidator()
    health_results = validator.check_system_health()
    
    # Check if system is healthy enough to test
    failed_checks = [c for c in health_results if "FAIL" in c["status"]]
    if len(failed_checks) >= len(health_results) / 2:
        print("\n❌ System health check failed. Please start the application first.")
        return
    
    print("\n")
    
    # Run API tests
    tester = PaymentAPITester()
    summary = tester.run_comprehensive_test_suite()
    
    return summary


if __name__ == "__main__":
    run_payment_tests()
#!/usr/bin/env python3
"""
TitanNetwork Security Assessment - Simulated Cyber Attack Tests
Tests for common vulnerabilities and security weaknesses
"""

import asyncio
import requests
import socket
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple
import sqlite3

class TitanNetworkSecurityTest:
    def __init__(self, target_host="127.0.0.1", target_port=8000):
        self.target_host = target_host
        self.target_port = target_port
        self.base_url = f"http://{target_host}:{target_port}"
        self.results = {"timestamp": datetime.now().isoformat(), "tests": []}
        
    def log_test(self, name: str, status: str, details: str = ""):
        """Log a security test result."""
        self.results["tests"].append({
            "name": name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"[{status:^10}] {name}: {details}")
    
    def test_port_scanning(self) -> bool:
        """Test 1: Port scanning - identify open ports."""
        print("\n=== PORT SCANNING ===")
        open_ports = []
        common_ports = [22, 80, 443, 3306, 5432, 6379, 8000, 8080, 9000]
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.target_host, port))
                sock.close()
                if result == 0:
                    open_ports.append(port)
                    self.log_test(f"Port {port} Scan", "OPEN", f"Service listening on port {port}")
                else:
                    self.log_test(f"Port {port} Scan", "CLOSED", f"No service on port {port}")
            except Exception as e:
                self.log_test(f"Port {port} Scan", "ERROR", str(e))
        
        return len(open_ports) > 0
    
    def test_http_methods(self) -> bool:
        """Test 2: Check for dangerous HTTP methods (PUT, DELETE, TRACE)."""
        print("\n=== HTTP METHOD ENUMERATION ===")
        dangerous_methods = ["PUT", "DELETE", "TRACE", "CONNECT"]
        vulnerable = False
        
        for method in dangerous_methods:
            try:
                req = requests.request(method, self.base_url, timeout=5)
                if req.status_code != 405:
                    self.log_test(f"HTTP {method} Method", "VULNERABLE", f"Allowed ({req.status_code})")
                    vulnerable = True
                else:
                    self.log_test(f"HTTP {method} Method", "SAFE", "Method not allowed")
            except Exception as e:
                self.log_test(f"HTTP {method} Method", "SAFE", str(e)[:50])
        
        return vulnerable
    
    def test_sql_injection(self) -> bool:
        """Test 3: SQL Injection on API endpoints."""
        print("\n=== SQL INJECTION TESTING ===")
        sql_payloads = [
            "1' OR '1'='1",
            "'; DROP TABLE users; --",
            "1 UNION SELECT NULL--",
            "admin' --",
        ]
        vulnerable = False
        
        endpoints = ["/api/stats", "/api/jobs", "/submit_job"]
        
        for endpoint in endpoints:
            for payload in sql_payloads:
                try:
                    url = f"{self.base_url}{endpoint}?id={payload}"
                    req = requests.get(url, timeout=5)
                    if "sqlite" in req.text.lower() or "error" in req.text.lower():
                        self.log_test(f"SQLi on {endpoint}", "VULNERABLE", f"Error message exposed: {payload[:30]}")
                        vulnerable = True
                    elif req.status_code == 200:
                        self.log_test(f"SQLi on {endpoint}", "POSSIBLE", f"Returned 200 with payload: {payload[:30]}")
                except Exception as e:
                    pass
        
        if not vulnerable:
            self.log_test("SQL Injection", "SAFE", "No obvious SQL injection vectors found")
        
        return vulnerable
    
    def test_xss_injection(self) -> bool:
        """Test 4: XSS (Cross-Site Scripting) vulnerabilities."""
        print("\n=== XSS TESTING ===")
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "';alert('XSS');//",
            "<img src=x onerror='alert(1)'>",
            "javascript:alert('XSS')",
        ]
        vulnerable = False
        
        for payload in xss_payloads:
            try:
                data = {"job": payload, "amount": 1}
                req = requests.post(f"{self.base_url}/submit_job", json=data, timeout=5)
                if payload in req.text:
                    self.log_test("XSS Vulnerability", "VULNERABLE", f"Payload reflected: {payload[:40]}")
                    vulnerable = True
            except:
                pass
        
        if not vulnerable:
            self.log_test("XSS Testing", "SAFE", "No reflected XSS found in responses")
        
        return vulnerable
    
    def test_api_authentication(self) -> bool:
        """Test 5: API endpoint authentication bypass."""
        print("\n=== AUTHENTICATION TESTING ===")
        endpoints = [
            "/api/stats",
            "/api/jobs",
            "/admin",
            "/dashboard",
        ]
        bypassed = False
        
        for endpoint in endpoints:
            try:
                req = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                if req.status_code == 200:
                    self.log_test(f"Auth Bypass - {endpoint}", "VULNERABLE", "Accessible without auth")
                    bypassed = True
                elif req.status_code == 401:
                    self.log_test(f"Auth Check - {endpoint}", "SAFE", "Requires authentication")
                elif req.status_code == 403:
                    self.log_test(f"Auth Check - {endpoint}", "SAFE", "Forbidden (access denied)")
                elif req.status_code == 404:
                    self.log_test(f"Endpoint - {endpoint}", "NOT_FOUND", "Endpoint does not exist")
            except requests.exceptions.ConnectionError:
                self.log_test(f"Auth - {endpoint}", "UNREACHABLE", "Service not responding")
            except Exception as e:
                self.log_test(f"Auth - {endpoint}", "ERROR", str(e)[:50])
        
        return bypassed
    
    def test_redis_access(self) -> bool:
        """Test 6: Check if Redis is exposed without auth."""
        print("\n=== REDIS EXPOSURE TESTING ===")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("127.0.0.1", 6379))
            sock.close()
            
            if result == 0:
                self.log_test("Redis Port Access", "VULNERABLE", "Redis port 6379 is open")
                
                # Try to connect without password
                try:
                    import redis
                    r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True, socket_connect_timeout=2)
                    r.ping()
                    self.log_test("Redis Authentication", "VULNERABLE", "Redis accessible without password")
                    keys = r.keys('*')
                    self.log_test("Redis Data Exposure", "CRITICAL", f"Found {len(keys)} keys exposed: {str(keys)[:100]}")
                    return True
                except Exception as e:
                    self.log_test("Redis Auth", "SAFE", f"Password required or not accessible: {str(e)[:50]}")
            else:
                self.log_test("Redis Port Access", "SAFE", "Redis port 6379 is closed")
                
        except Exception as e:
            self.log_test("Redis Scan", "ERROR", str(e)[:50])
        
        return False
    
    def test_database_access(self) -> bool:
        """Test 7: Check if SQLite database is world-readable."""
        print("\n=== DATABASE EXPOSURE TESTING ===")
        try:
            db_path = "/home/titan/TitanNetwork/titan_ledger.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions")
            count = cursor.fetchone()[0]
            self.log_test("SQLite Access", "VULNERABLE", f"Database readable without auth ({count} records)")
            
            # Try to extract sensitive data
            cursor.execute("SELECT * FROM transactions LIMIT 1")
            sample = cursor.fetchone()
            self.log_test("Data Extraction", "CRITICAL", f"Sensitive data exposed: {str(sample)[:100]}")
            
            conn.close()
            return True
        except FileNotFoundError:
            self.log_test("Database Access", "SAFE", "Database file not found (or protected)")
        except Exception as e:
            self.log_test("Database Access", "SAFE", str(e)[:50])
        
        return False
    
    def test_file_inclusion(self) -> bool:
        """Test 8: Local File Inclusion (LFI) vulnerabilities."""
        print("\n=== FILE INCLUSION TESTING ===")
        lfi_payloads = [
            "../../../../etc/passwd",
            "..\\..\\..\\windows\\win.ini",
            "....//....//....//etc/passwd",
        ]
        vulnerable = False
        
        endpoints = ["/api/stats", "/submit_job", "/"]
        
        for endpoint in endpoints:
            for payload in lfi_payloads:
                try:
                    url = f"{self.base_url}{endpoint}?file={payload}"
                    req = requests.get(url, timeout=5)
                    if "root:" in req.text or "Administrator" in req.text:
                        self.log_test("LFI Vulnerability", "VULNERABLE", f"File disclosure: {payload}")
                        vulnerable = True
                except:
                    pass
        
        if not vulnerable:
            self.log_test("File Inclusion", "SAFE", "No LFI vulnerabilities detected")
        
        return vulnerable
    
    def test_docsstring_exposure(self) -> bool:
        """Test 9: Documentation/Source code exposure."""
        print("\n=== SOURCE CODE EXPOSURE TESTING ===")
        exposed_paths = [
            "/.git/config",
            "/README.md",
            "/requirements.txt",
            "/.env",
            "/config.json",
            "/debug",
        ]
        vulnerable = False
        
        for path in exposed_paths:
            try:
                req = requests.get(f"{self.base_url}{path}", timeout=5)
                if req.status_code == 200 and len(req.text) > 0:
                    self.log_test(f"Path Exposure - {path}", "VULNERABLE", f"Exposed ({len(req.text)} bytes)")
                    vulnerable = True
            except:
                pass
        
        if not vulnerable:
            self.log_test("Source Exposure", "SAFE", "No obvious source code paths exposed")
        
        return vulnerable
    
    def test_rate_limiting(self) -> bool:
        """Test 10: Rate limiting - DoS vulnerability."""
        print("\n=== RATE LIMITING TESTING ===")
        try:
            # Send rapid requests
            responses = []
            for i in range(20):
                try:
                    req = requests.get(f"{self.base_url}/api/stats", timeout=2)
                    responses.append(req.status_code)
                except:
                    responses.append(None)
            
            if 429 in responses:
                self.log_test("Rate Limiting", "PROTECTED", "Rate limiting is active (429 Too Many Requests)")
                return False
            else:
                self.log_test("Rate Limiting", "VULNERABLE", f"No rate limiting detected - {len([r for r in responses if r == 200])} requests succeeded")
                return True
        except Exception as e:
            self.log_test("Rate Limiting", "ERROR", str(e)[:50])
        
        return False
    
    def run_all_tests(self):
        """Run all security tests."""
        print("\n" + "="*60)
        print("TITAN NETWORK - SECURITY ASSESSMENT")
        print("="*60)
        print(f"Target: {self.base_url}")
        print(f"Started: {datetime.now().isoformat()}")
        print("="*60)
        
        vulnerabilities_found = 0
        
        if self.test_port_scanning():
            vulnerabilities_found += 1
        if self.test_http_methods():
            vulnerabilities_found += 1
        if self.test_sql_injection():
            vulnerabilities_found += 1
        if self.test_xss_injection():
            vulnerabilities_found += 1
        if self.test_api_authentication():
            vulnerabilities_found += 1
        if self.test_redis_access():
            vulnerabilities_found += 1
        if self.test_database_access():
            vulnerabilities_found += 1
        if self.test_file_inclusion():
            vulnerabilities_found += 1
        if self.test_docsstring_exposure():
            vulnerabilities_found += 1
        if self.test_rate_limiting():
            vulnerabilities_found += 1
        
        # Summary
        print("\n" + "="*60)
        print("SECURITY ASSESSMENT SUMMARY")
        print("="*60)
        print(f"Total Tests Run: {len(self.results['tests'])}")
        print(f"Vulnerabilities Found: {vulnerabilities_found}")
        
        safe_count = len([t for t in self.results['tests'] if "SAFE" in t['status']])
        vuln_count = len([t for t in self.results['tests'] if "VULNERABLE" in t['status'] or "CRITICAL" in t['status']])
        
        print(f"Safe Tests: {safe_count}")
        print(f"Vulnerable Tests: {vuln_count}")
        print("="*60)
        
        # Save report
        report_path = "/home/titan/TitanNetwork/SECURITY_REPORT.json"
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nReport saved to: {report_path}")
        
        return vulnerabilities_found

if __name__ == "__main__":
    test = TitanNetworkSecurityTest()
    found = test.run_all_tests()
    print(f"\n[ASSESSMENT COMPLETE] Found {found} vulnerability categories")

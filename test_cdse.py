import os
from pathlib import Path

# 1. Load .env directly
env_path = Path(__file__).resolve().parent / ".env"
print(f"[1] Checking .env at: {env_path}")
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'\"")
    print("    -> .env loaded successfully.")
else:
    print("    -> ERROR: .env file NOT found at project root!")

cid = os.getenv("CDSE_CLIENT_ID", "")
csec = os.getenv("CDSE_CLIENT_SECRET", "")
cuser = os.getenv("CDSE_USERNAME", "")
cpass = os.getenv("CDSE_PASSWORD", "")

print(f"[2] Environment Keys:")
print(f"    - CDSE_CLIENT_ID: {'SET (' + cid[:12] + '...)' if cid and 'your_' not in cid else 'NOT SET or placeholder'}")
print(f"    - CDSE_CLIENT_SECRET: {'SET' if csec and 'your_' not in csec else 'NOT SET or placeholder'}")
print(f"    - CDSE_USERNAME: {cuser if cuser else '(empty/commented out)'}")

# 2. Test provider
try:
    from app.providers import get_provider
    p = get_provider("cdse")
    is_cfg = p.has_configured_credentials()
    print(f"[3] Provider Status: {'CONFIGURED (Ready)' if is_cfg else 'NOT CONFIGURED'}")
    if is_cfg:
        print("[4] Testing Copernicus Auth Token...")
        auth_ok = p.authenticate()
        print(f"    -> Auth Success: {auth_ok}")
        if auth_ok:
            print("\n>>> ALL TESTS PASSED! CDSE is working properly. <<<")
        else:
            print("\n>>> Auth failed with CDSE server. Check network or credentials. <<<")
    else:
        print("\n>>> Provider is not configured. Check the values in .env. <<<")
except Exception as e:
    import traceback
    print(f"\nError: {e}")
    traceback.print_exc()

import requests
import uuid

BASE_URL = "http://localhost:8000/api/user/v1"

def register_user(device_id):
    response = requests.post(f"{BASE_URL}/prefrence", json={
        "device_id": device_id,
        "platform": "ios",
        "interests": ["Art"]
    })
    return response.json()['result']['saved_user']

def get_profile(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/profile", headers=headers)
    return response.json()['result']

def generate_codes(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/referral/generate?count=1", headers=headers)
    return response.json()['results']

def redeem_code(token, code):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/referral/redeem", headers=headers, json={
        "referral_code": code
    })
    return response.json()

def main():
    owner_id = f"owner_{uuid.uuid4()}"
    redeemer_id = f"redeemer_{uuid.uuid4()}"
    
    print("--- Registering Users ---")
    owner = register_user(owner_id)
    redeemer = register_user(redeemer_id)
    
    owner_token = owner['access_token']
    redeemer_token = redeemer['access_token']
    
    print(f"Owner initial points: {get_profile(owner_token)['total_points']}")
    print(f"Redeemer initial points: {get_profile(redeemer_token)['total_points']}")
    
    print("--- Generating Code ---")
    codes = generate_codes(owner_token)
    code = codes[0]['code']
    
    print(f"--- Redeeming Code {code} ---")
    redeem_result = redeem_code(redeemer_token, code)
    print(f"Redeem Result: {redeem_result['status']}")
    
    print("--- Checking Points After Redemption ---")
    print(f"Owner final points: {get_profile(owner_token).get('total_points', 0)}")
    print(f"Redeemer final points: {get_profile(redeemer_token).get('total_points', 0)}")

if __name__ == "__main__":
    main()

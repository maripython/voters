import requests


def get_voter_list(api_key, voter_id):
    url = f"http://localhost:8000/voter_list/{voter_id}"  # Adjust port number as needed
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # Assuming the response is in JSON format
            voter_list = response.json()
            return voter_list
        else:
            print("Failed to fetch voter list. Status code:", response.status_code)
            return None
    except Exception as e:
        print("An error occurred:", e)
        return None


# Replace 'your_api_key' with your actual API key
api_key = ('T1gwWnRIanVrV2Z4WnNsR3Q2LmU0ZDdiZWMwNzE2OWYxOTcyYT'
           'I2NWM1NjViYTVkNTE5OjhhZTkyNmRmMDUwOThkY2QxOTkxNGI3NGRmOWExZDBmNjg5YTk4YWM1MDVjNDk2Yw==')
# Replace 'your_voter_id' with the actual voter ID
voter_id = 'TKJ1057462'
voter_list = get_voter_list(api_key, voter_id)
if voter_list:
    print("Voter list fetched successfully:", voter_list)

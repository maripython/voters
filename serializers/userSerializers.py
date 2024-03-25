def userInfoSerializer(user) -> dict:
    if user["role"] == "admin":
        return {
            "name": user["name"],
            "email": user["email"],
            "username": user["username"],
            "provider": user["provider"],
            "role": user["role"],
            "verified": user["verified"],
            "initial_product": user["initial_product"]
        }
    else:
        return {
            "name": user["name"],
            "email": user["email"],
            "username": user["username"],
            "provider": user["provider"],
            "role": user["role"],
            "free_plan": user["free_plan"],
            "verified": user["verified"],
            "subscription_level": user["subscription_level"],
            "initial_product": user["initial_product"]
        }

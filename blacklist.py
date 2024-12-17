import redis
from datetime import timedelta

# Connect to Redis
r = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

# Constants
REQUEST_LIMIT = 40
TIME_WINDOW = 3600  # in seconds (1 hour)
BLACKLIST_TTL = 86400  # in seconds (24 hours)

def handle_request(ip):
    # Check if the IP is blacklisted
    if r.sismember("blacklist", ip):
        return f"IP {ip} is blacklisted. Access denied."

    # Increment the request count for the IP
    current_count = r.incr(ip)

    # If it's the first request, set a TTL for the key
    if current_count == 1:
        r.expire(ip, TIME_WINDOW)

    # Check if the request count exceeds the limit
    if current_count > REQUEST_LIMIT:
        # Add to blacklist
        r.sadd("blacklist", ip)
        r.expire(f"blacklist:{ip}", BLACKLIST_TTL)
        return f"IP {ip} has been blacklisted."

    return f"IP {ip} request count: {current_count}."

# Example usage
if __name__ == "__main__":
    ip_address = "192.168.1.1"
    response = handle_request(ip_address)
    print(response)

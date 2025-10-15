import redis
import os

redis_host = os.getenv("COMPARIA_REDIS_HOST", False)
# redis_host = os.environ("COMPARIA_REDIS_HOST", 'languia-redis')

r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

from languia.config import RATELIMIT_PRICEY_MODELS_INPUT


def increment_input_chars(ip: str, input_chars: int):
    if not redis_host:
        return False
    r.incrby(f"ip:{ip}", input_chars)
    r.expire(f"ip:{ip}", 3600 * 2)
    return True


def is_ratelimited(ip: str):
    counter = r.get(f"ip:{ip}")
    if counter and int(counter) > RATELIMIT_PRICEY_MODELS_INPUT * 2:
        return True
    else:
        return False


class Session:
    session_hash: str | None
    conversations: tuple[dict, dict]
    # vote: Vote | None
    # reactions: dict = []
    ip: str | None
    total_input_chars: int = 0


def save_session(session: Session):
    r.hset(
        f"session:{session.session_hash}",
        mapping={
            "conversations": session.conversations,
            "ip": session.ip,
        },
    )
    r.hgetall(f"session:{session.session_hash}")


#     r.hset(f'session:{session.session_hash}', mapping={
#         'name': 'John',
#         "surname": 'Smith',
#         "company": 'Redis',
#         "age": 29
#     })
#     r.hgetall(f'session:{session.session_hash}')
#     # True
#     total_input_chars = r.hget(f'session:{session.session_hash}', "total_input_chars")

#     r.hset(f'session:{session.session_hash}', mapping={
#         "total_input_chars": 29
#     })
#     # True
#     r.hgetall('user-session:123')

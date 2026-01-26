_subs = []

def get_subs() -> list[int]:
    return _subs

def set_subs(subs: list[int]):
    global _subs
    if isinstance(subs, list):
        _subs = subs

def add_sub(id: int) -> bool:
    if not (id in _subs):
        _subs.append(id)
        return True
    return False

def remove_user(id: int) -> bool:
    if _subs and id in _subs:
        _subs.remove(id)
        return True
    return False

def user_exists(id: int) -> bool:
    return id in _subs
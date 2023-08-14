from rcon.source import Client


def get_info(host: str, port: int, password: str) -> dict:
    client = Client(host, port, passwd=password)
    client.connect(login=True)
    response = client.run("/players", "online", "count")
    return {"player_count": int(response.strip("Online Players (").strip("):\n"))}

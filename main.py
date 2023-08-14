from logging import getLogger

from fastapi import HTTPException, FastAPI
from fastapi_utils.tasks import repeat_every
from minecraft_utils import get_info as get_mc_info
from factorio_utils import get_info as get_fc_info
from utils import getenv, send_notification
import boto3

SECRET_PASSWORD = getenv("SECRET_PASSWORD")
INSTANCE_ID = getenv("INSTANCE_ID")
AWS_ACCESS_KEY = getenv("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = getenv("AWS_SECRET_ACCESS_KEY")
MINECRAFT_HOST = getenv("MINECRAFT_HOST")
MINECRAFT_PORT = int(getenv("MINECRAFT_PORT"))
FACTORIO_RCON_HOST = getenv("FACTORIO_RCON_HOST")
FACTORIO_RCON_PORT = int(getenv("FACTORIO_RCON_PORT"))
FACTORIO_RCON_PASSWORD = getenv("FACTORIO_RCON_PASSWORD")

FILENAME = "counter.txt"

app = FastAPI()
ec2 = boto3.client(
    "ec2",
    region_name="ap-south-1",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
logger = getLogger()


@app.get("/")
def read_root():
    return {"message": "Fluff off"}


@app.get("/status/{secret_key}")
def get_status(secret_key: str):
    if secret_key != SECRET_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect secret key")
    resp = {}
    try:
        instance_status = ec2.describe_instance_status(
            InstanceIds=[INSTANCE_ID], IncludeAllInstances=True
        )["InstanceStatuses"][0]["InstanceState"]["Name"]
        if instance_status != "running":
            resp["instance_status"] = instance_status
            return resp
    except Exception:
        logger.exception("Unable to get EC2 status.")
        send_notification("Unable to get EC2 status.")
        resp["instance_status"] = "Unable to get EC2 status."
        return resp
    try:
        mc_info = get_mc_info(host=MINECRAFT_HOST, port=MINECRAFT_PORT)
        resp["minecraft_status"] = mc_info
    except Exception:
        logger.exception("Unable to get MC status.")
        send_notification("Unable to get MC status")
        resp["minecraft_status"] = {"error": "Unable to get MC status."}
    try:
        fc_info = get_fc_info(
            host=FACTORIO_RCON_HOST,
            port=FACTORIO_RCON_PORT,
            password=FACTORIO_RCON_PASSWORD,
        )
        resp["factorio_status"] = fc_info
    except Exception:
        logger.exception("Unable to get FC status.")
        send_notification("Unable to get FC status")
        resp["factorio_status"] = {"error": "Unable to get FC status."}
    return resp


@app.get("/start_instance/{secret_key}")
def start_instance(secret_key: str):
    if secret_key != SECRET_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect secret key")
    try:
        instance_status = ec2.describe_instance_status(
            InstanceIds=[INSTANCE_ID], IncludeAllInstances=True
        )["InstanceStatuses"][0]["InstanceState"]["Name"]
        if instance_status == "running":
            return {"instance_status": instance_status}
    except Exception:
        logger.exception("Unable to get EC2 status.")
        return {"error": "Unable to get EC2 status."}
    try:
        ec2.start_instances(InstanceIds=[INSTANCE_ID])
        send_notification("Started instance.")
        return {"message": f"Starting instance {INSTANCE_ID}"}
    except Exception:
        logger.exception("Unable to start instance.")
        return {"error": "Unable to start instance."}


def get_counter(tries: int = 3) -> int:
    try:
        with open(FILENAME, "r") as f:
            return int(f.read())
    except Exception as e:
        logger.exception("Unable to read file, resetting.")
        if tries == 0:
            raise e
        reset_file()
        get_counter(tries - 1)


def update_counter(value: int):
    with open(FILENAME, "w") as f:
        f.write(f"{value}")


@app.on_event("startup")
def reset_file():
    update_counter(0)


@app.on_event("startup")
@repeat_every(seconds=60, logger=logger)
def check_and_close_instance():
    try:
        mc_info = get_mc_info(host=MINECRAFT_HOST, port=MINECRAFT_PORT)
        fc_info = get_fc_info(
            host=FACTORIO_RCON_HOST,
            port=FACTORIO_RCON_PORT,
            password=FACTORIO_RCON_PASSWORD,
        )
    except (ConnectionRefusedError, TimeoutError):
        logger.info("Connection refused or timed out.")
        return  # instance is probably off
    except Exception:
        logger.exception("Unable to connect to server.")
        return
    try:
        mc_num_players_online = mc_info["players"]["online"]
        fc_num_players_online = fc_info["player_count"]
    except KeyError:
        send_notification("Unable to get player count.")
        logger.exception("Unable to get player count.")
        return
    if mc_num_players_online == 0 and fc_num_players_online == 0:
        counter = get_counter()
        counter += 1
        if counter < 3:
            update_counter(counter)
            logger.info(f"ZERO_COUNTER at {counter}, waiting.")
            return
        update_counter(0)
        try:
            ec2.stop_instances(InstanceIds=[INSTANCE_ID])
            send_notification("Stopped instance.")
        except Exception:
            send_notification("Unable to stop instance.")
            logger.exception("Unable to stop instance.")
            return

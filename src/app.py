import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from flask import Flask, request, abort
from flask_cors import CORS
from solana.rpc.api import Client

from forge import Forge

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

network_urls = {
    "localhost": "http://localhost:8899",
    "devnet": "https://api.devnet.solana.com",
    "mainnet": "https://api.devnet.solana.com",
}

s3 = boto3.client("s3")
VAULT = "uniforge-vault"
PUBLIC = "uniforge-public"


@app.route("/")
def hello():
    return "<p>Hello World!</p>"


@app.route("/updateContent", methods=["POST"])
def update_content():
    # Parse input params
    try:
        params = json.loads(request.data)
        network = params["network"]
        forge_id = params["forgeId"]
        assert network in network_urls
    except Exception as e:
        logger.error(request.data)
        logger.error("Bad input params")
        logger.error(e)
        abort(400)

    # Try to get the state of the forge
    try:
        client = Client(network_urls[network])
        res = client.get_account_info(forge_id)
    except Exception as e:
        logger.error("Failed to query Solana network for Forge state")
        logger.error(e)
        abort(404)

    # Unpack on-chain data into Forge
    try:
        forge = Forge(res["result"]["value"]["data"][0])
        state = {"last": forge.max_supply - forge.supply_unclaimed}
    except Exception as e:
        logger.error("Failed to unpack on-chain data")
        logger.error(e)
        abort(404)

    # Get old state
    try:
        res = s3.get_object(
            Bucket=VAULT, Key=os.path.join(network, forge_id, "state.json")
        )
        old_state = json.loads(res["Body"].read())
    except ClientError as e:
        # Assume that the state doesn't exist yet
        logger.error(res)
        old_state = {"last": 0}

    if old_state["last"] == state["last"]:
        return state

    # Move recently forged stuff to public folder
    res = s3.get_object(
        Bucket=VAULT, Key=os.path.join(network, forge_id, "content_hashes.json")
    )
    content_hashes = json.loads(res["Body"].read())

    for i in range(old_state["last"], state["last"]):
        logger.info("Moving content for token {}".format(i + 1))
        content_hash = content_hashes[i]
        source_key = os.path.join(network, forge_id, "{}.png".format(content_hash))

        # ToDo this isn't content based addressing... Figure out storing
        # the hash on chain
        dest_key = os.path.join(network, forge_id, "{:09d}.png".format(i + 1))

        # ToDo move the asset to a distributed service such as Arweave or
        # IPFS
        res = s3.copy_object(
            ACL="public-read",
            Bucket=PUBLIC,
            Key=dest_key,
            CopySource={"Bucket": VAULT, "Key": source_key},
        )

        logger.info(res)

    res = s3.put_object(
        Bucket=VAULT,
        Key=os.path.join(network, forge_id, "state.json"),
        Body=json.dumps(state),
    )

    return state

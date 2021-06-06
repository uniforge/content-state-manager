import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from flask import Flask, request, abort
from flask_cors import CORS
from solana.rpc.api import Client
import requests

from onchain_program import Forge, ForgeEvent, logs_to_event_type, validate_tx
from cover_generation import RAINBOW_COLORS, FOREGROUND_IMAGES, block_hash_to_cover

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

request_id = 0
network_urls = {
    "localhost": "http://localhost:8899",
    "devnet": "https://api.devnet.solana.com",
    "mainnet": "https://api.devnet.solana.com",
}

sqs = boto3.client("sqs")
CSM_Q = (
    "https://sqs.us-east-1.amazonaws.com/364742273493/uniforge-content-state-management"
)
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
        tx_sign = params["txSign"]
        program_id = params["programId"]
        print(tx_sign)
        assert network in network_urls

        # Enqueue the request in case of failures
        res = sqs.send_message(
            QueueUrl=CSM_Q, MessageBody=request.data.decode(errors="ignore")
        )
        print(res)
    except Exception as e:
        logger.error(request.data)
        logger.error("Bad input params")
        logger.error(e)
        abort(400)

    # Try to get the state of the forge
    try:
        client = Client(network_urls[network])
        res = client.get_account_info(forge_id, commitment="single")
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

    # Try to get the transaction and block
    try:
        # solana-py doesn't support the additional commitment parameters of the
        # getConfirmedTransaction endpoint, make a custom request
        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "getConfirmedTransaction",
                "params": [tx_sign, {"commitment": "singleGossip"}],
            }
        )
        tx_res = requests.post(
            network_urls[network],
            headers={"Content-Type": "application/json"},
            data=data,
        ).json()
        # tx_res = client.get_confirmed_transaction(tx_sign)

        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "getConfirmedBlock",
                "params": [tx_res["result"]["slot"], {"commitment": "singleGossip"}],
            }
        )
        block_res = requests.post(
            network_urls[network],
            headers={"Content-Type": "application/json"},
            data=data,
        ).json()
        # block_res = client.get_confirmed_block(tx_res["result"]["slot"])
        block_hash = block_res["result"]["blockhash"]
    except Exception as e:
        logger.error("Failed to query Solana network for transaction and block")
        logger.error(e)
        abort(404)

    # Validate transaction
    try:
        artist = forge.artist.to_base58().decode()
        valid = validate_tx(tx_res, artist, program_id, forge.min_fee_lamports / 1e9)
    except Exception as e:
        logger.error("Failed to query Solana network for transaction")
        logger.error(e)
        abort(404)

    if not valid:
        logger.error("Invalid transaction {}".format(tx_sign))
        abort(404)

    # Create the cover art
    try:
        logs = tx_res["result"]["meta"]["logMessages"]
        logger.info(logs)
        found, data = logs_to_event_type(program_id, logs, ForgeEvent)

        if found and data.token_id <= state["last"]:
            token_id = data.token_id
            cover = block_hash_to_cover(block_hash, RAINBOW_COLORS, FOREGROUND_IMAGES)
            fn = "{}_{:09d}.png".format("cover", token_id)
            cover_local_fn = os.path.join("/tmp", fn)
            cover.save(cover_local_fn)
            # We are using the actual token id from the network, no need to add one
            cover_key = os.path.join(network, forge_id, fn)

            res = s3.upload_file(
                cover_local_fn, PUBLIC, cover_key, ExtraArgs={"ACL": "public-read"}
            )
            os.remove(cover_local_fn)
            logger.info("Saved cover {}".format(token_id))
        else:
            logger.error(
                "Failed to find the event data in logs of valid transaction {}".format(
                    tx_sign
                )
            )
    except Exception as e:
        logger.error("Failed to generate cover art")
        logger.error(e)

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
    for i in range(old_state["last"], state["last"]):
        logger.info("Moving content for token {}".format(i + 1))
        # ToDo this isn't content based addressing... Figure out storing
        # the hash on chain
        # Generation code starts with index i -> token index i + 1
        source_key = os.path.join(
            network, forge_id, "{}_{:09d}.png".format("insert", i)
        )
        dest_key = os.path.join(
            network, forge_id, "{}_{:09d}.png".format("insert", i + 1)
        )

        # ToDo move the asset to a distributed service such as Arweave or
        # IPFS
        try:
            res = s3.copy_object(
                ACL="public-read",
                Bucket=PUBLIC,
                Key=dest_key,
                CopySource={"Bucket": VAULT, "Key": source_key},
            )
        except ClientError as e:
            logger.error("Error moving {} to {}".format(source_key, dest_key))
            logger.error(e)

        logger.info(res)

    res = s3.put_object(
        Bucket=VAULT,
        Key=os.path.join(network, forge_id, "state.json"),
        Body=json.dumps(state),
    )

    return state

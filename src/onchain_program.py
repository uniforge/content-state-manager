import base64
import json
import logging
from solana.account import PublicKey
from spl.token.constants import WRAPPED_SOL_MINT

logger = logging.getLogger(__name__)


def _split_array(data, index):
    return data[:index], data[index:]


def _parse_logs_for_event(program_id, logs):
    """This is, a total hack... ToDo look at Anchor's event handler
    to see what they expect the events to look like. Perhaps
    use the 8-byte discriminator.
    """
    event_data = ""

    for i, log in enumerate(logs):
        if log.split(":")[0].lower() == "program log":
            if logs[i + 1].split(" ")[1] == program_id:
                event_data = log.split(":")[1].strip()

    if event_data == "":
        return False, event_data

    return True, event_data


def logs_to_event_type(program_id, logs, expected_type):
    found, event = _parse_logs_for_event(program_id, logs)

    if found:
        return found, expected_type(event)

    return found, None


def validate_tx(tx, artist, program, min_fee_sol):
    assert tx["result"] != None, "Transaction does not exist"

    accounts = tx["result"]["transaction"]["message"]["accountKeys"]

    # Check that the artist was paid and the payment was sufficient
    tx_artist = None

    for i, account in enumerate(accounts):
        if account == artist:
            tx_artist = i
            break

    if tx_artist == None:
        logger.error("Artist is not in the accounts listed")
        return False

    pre_balance = None

    for balance in tx["result"]["meta"]["preTokenBalances"]:
        if (
            balance["accountIndex"] == tx_artist
            and balance["mint"] == WRAPPED_SOL_MINT.to_base58().decode()
        ):
            pre_balance = balance["uiTokenAmount"]["uiAmount"]
            break

    if pre_balance == None:
        pre_balance = 0

    post_balance = None

    for balance in tx["result"]["meta"]["postTokenBalances"]:
        if (
            balance["accountIndex"] == tx_artist
            and balance["mint"] == WRAPPED_SOL_MINT.to_base58().decode()
        ):
            post_balance = balance["uiTokenAmount"]["uiAmount"]
            break

    if post_balance == None:
        logger.error("Artist does not have a post balance")
        return False

    valid_fee = False
    if post_balance - pre_balance >= min_fee_sol:
        valid_fee = True
    else:
        logger.error("Invalid fee paid to artist")

    # Check instructions
    correct_program = False
    instructions = tx["result"]["transaction"]["message"]["instructions"]
    for instruction in instructions:
        if tx_artist in instruction["accounts"]:
            correct_program = accounts[instruction["programIdIndex"]] == program

    if not correct_program:
        logger.error("Incorrect program")

    return valid_fee and correct_program


class Forge:
    """Object representing Forge program state"""

    def __init__(self, b64_data):
        """Unpack a Forge data structure from Solana
        NB All encoding is little-endian
        """
        bytes_data = base64.b64decode(b64_data)
        self.discriminator, _rest = _split_array(bytes_data, 8)

        # Name
        self.name, _rest = _split_array(_rest, 64)
        self.name = self.name.decode("utf-8").strip()

        # Symbol
        self.symbol, _rest = _split_array(_rest, 16)
        self.symbol = self.symbol.decode("utf-8").strip()

        # Content hash
        self.content_hash, _rest = _split_array(_rest, 32)
        self.content_hash = self.content_hash.hex()

        # Authority
        self.authority, _rest = _split_array(_rest, 32)
        self.authority = PublicKey(self.authority)

        # Max supply
        self.max_supply, _rest = _split_array(_rest, 2)
        self.max_supply = int.from_bytes(self.max_supply, "little")

        # Supply unclaimed
        self.supply_unclaimed, _rest = _split_array(_rest, 2)
        self.supply_unclaimed = int.from_bytes(self.supply_unclaimed, "little")

        # Artist
        self.artist, _rest = _split_array(_rest, 32)
        self.artist = PublicKey(self.artist)

        # Min fee
        self.min_fee_lamports, _rest = _split_array(_rest, 8)
        self.min_fee_lamports = int.from_bytes(self.min_fee_lamports, "little")

        # Secondary fee
        self.secondary_fee_bps, _rest = _split_array(_rest, 8)
        self.secondary_fee_bps = int.from_bytes(self.secondary_fee_bps, "little")

        self._rest = _rest

    def __repr__(self):
        return "{} {} - Max supply: {}, Supply unclaimed: {}".format(
            self.name, self.symbol, self.max_supply, self.supply_unclaimed
        )


class ForgeEvent:
    """Object representing ForgeEvent emitted by Forge"""

    def __init__(self, b64_data):
        bytes_data = base64.b64decode(b64_data)
        self.discriminator, _rest = _split_array(bytes_data, 8)

        # Token Id
        self.token_id, _rest = _split_array(_rest, 2)
        self.token_id = int.from_bytes(self.token_id, "little")

        # Owner
        self.owner, _rest = _split_array(_rest, 32)
        self.owner = PublicKey(self.owner)

    def to_dict(self):
        return {"token_id": self.token_id, "owner": self.owner.to_base58().decode()}

    def __repr__(self):
        return json.dumps(self.to_dict())


class OfferEvent:
    """Object representing OfferEvent emitted by Forge"""

    def __init__(self, b64_data):
        bytes_data = base64.b64decode(b64_data)
        self.discriminator, _rest = _split_array(bytes_data, 8)

        # Token Id
        self.token_id, _rest = _split_array(_rest, 2)
        self.token_id = int.from_bytes(self.token_id, "little")

        # Owner
        self.seller, _rest = _split_array(_rest, 32)
        self.seller = PublicKey(self.seller)

        # min_bid_lamports
        self.min_bid_lamports, _rest = _split_array(_rest, 8)
        self.min_bid_lamports = int.from_bytes(self.min_bid_lamports, "little")

    def to_dict(self):
        return {
            "token_id": self.token_id,
            "seller": self.seller.to_base58().decode(),
            "min_bid_lamports": self.min_bid_lamports,
        }

    def __repr__(self):
        return json.dumps(self.to_dict())


class TransferEvent:
    """Object representing TransferEvent emitted by Forge"""

    def __init__(self, b64_data):
        bytes_data = base64.b64decode(b64_data)
        self.discriminator, _rest = _split_array(bytes_data, 8)

        # Token Id
        self.token_id, _rest = _split_array(_rest, 2)
        self.token_id = int.from_bytes(self.token_id, "little")

        # From
        self.from_address, _rest = _split_array(_rest, 32)
        self.from_address = PublicKey(self.from_address)

        # To
        self.to_address, _rest = _split_array(_rest, 32)
        self.to_address = PublicKey(self.to_address)

    def to_dict(self):
        return {
            "token_id": self.token_id,
            "from": self.from_address.to_base58().decode(),
            "to": self.to_address.to_base58().decode(),
        }

    def __repr__(self):
        return json.dumps(self.to_dict())

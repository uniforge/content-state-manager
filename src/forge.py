import base64
from solana.account import PublicKey


def _split_array(data, index):
    return data[:index], data[index:]


class Forge:
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

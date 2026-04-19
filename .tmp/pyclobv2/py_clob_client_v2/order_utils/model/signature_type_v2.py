from enum import IntEnum


class SignatureTypeV2(IntEnum):
    """
    Signature types for V2 (CTF Exchange V2) orders.
    """

    EOA = 0
    """ECDSA EIP712 signatures signed by EOAs"""

    POLY_PROXY = 1
    """EIP712 signatures signed by EOAs that own Polymarket Proxy wallets"""

    POLY_GNOSIS_SAFE = 2
    """EIP712 signatures signed by EOAs that own Polymarket Gnosis safes"""

    POLY_1271 = 3
    """EIP1271 signatures signed by smart contracts (smart contract wallets or vaults)"""

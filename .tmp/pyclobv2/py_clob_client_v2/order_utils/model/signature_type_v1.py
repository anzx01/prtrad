from enum import IntEnum


class SignatureTypeV1(IntEnum):
    """
    Signature types for V1 (CTF Exchange V1) orders.
    """

    EOA = 0
    """ECDSA EIP712 signatures signed by EOAs"""

    POLY_PROXY = 1
    """EIP712 signatures signed by EOAs that own Polymarket Proxy wallets"""

    POLY_GNOSIS_SAFE = 2
    """EIP712 signatures signed by EOAs that own Polymarket Gnosis safes"""

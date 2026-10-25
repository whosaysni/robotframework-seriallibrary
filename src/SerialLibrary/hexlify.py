"""Registers the ``hexlify`` codec used as the library's default encoding.

The codec is pySerial's ``hexlify_codec`` with one tweak: decoded text has
its trailing space stripped, so ``b'\\x01\\x23'`` reads back as ``'01 23'``.
"""

import codecs

from serial.tools import hexlify_codec

NAME = "hexlify"


def _decode(data: bytes, errors: str = "strict") -> tuple[str, int]:
    text, length = hexlify_codec.hex_decode(data, errors)
    return text.rstrip(), length


_CODEC_INFO = codecs.CodecInfo(
    name=NAME,
    encode=hexlify_codec.hex_encode,
    decode=_decode,
    incrementalencoder=hexlify_codec.IncrementalEncoder,
    incrementaldecoder=hexlify_codec.IncrementalDecoder,
    streamwriter=hexlify_codec.StreamWriter,
    streamreader=hexlify_codec.StreamReader,
)


def _search(name: str) -> codecs.CodecInfo | None:
    return _CODEC_INFO if name == NAME else None


codecs.register(_search)

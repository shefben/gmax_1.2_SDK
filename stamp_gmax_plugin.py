#!/usr/bin/env python3
"""Create or verify GMax 1.2 authentication stamps on Win32 plug-ins.

The tool accepts any PE32 GMax plug-in type, including DLE, DLI, DLM, DLO,
DLU, DLT, DLX, BMI, BMS, and GUP files. It does not require a donor DLL.
"""

import argparse
import ctypes
import hashlib
import math
import os
import struct
import tempfile


TRAILER_SIZE = 48
HEX_BYTES = frozenset(b"0123456789abcdefABCDEF")

# Parameters recovered from the GMax 1.2 core.dll plug-in authenticator.
MODULUS = 0x96A97B1A4D8371CB
GROUP_ORDER = (MODULUS - 1) // 2
CHECKSUM_FACTOR = 0x53C2A34F01677011
PUBLIC_KEY = 0x48775CABC8034574
GENERATOR = 0x4E449034D75840CF
PRIVATE_KEY = 0x39A3337B794E2427


def parse_pe(data):
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a DOS/PE image")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 24 > len(data) or data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("not a PE image")
    optional_offset = pe_offset + 24
    magic = struct.unpack_from("<H", data, optional_offset)[0]
    if magic != 0x10B:
        raise ValueError("GMax 1.2 requires a 32-bit PE32 plug-in")
    checksum_offset = optional_offset + 64
    if checksum_offset + 4 > len(data):
        raise ValueError("truncated PE optional header")
    return checksum_offset


def mapped_checksum(data, mapped_length=None):
    if mapped_length is None:
        mapped_length = len(data)
    if mapped_length < 0 or mapped_length > len(data):
        raise ValueError("invalid mapped length")

    buffer = ctypes.create_string_buffer(bytes(data))
    header_sum = ctypes.c_ulong()
    computed_sum = ctypes.c_ulong()
    function = ctypes.WinDLL("imagehlp").CheckSumMappedFile
    function.argtypes = (
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.c_ulong),
    )
    function.restype = ctypes.c_void_p
    result = function(
        buffer,
        mapped_length,
        ctypes.byref(header_sum),
        ctypes.byref(computed_sum),
    )
    if not result:
        raise OSError("CheckSumMappedFile failed")
    return header_sum.value, computed_sum.value


def checksum_message(checksum):
    return (checksum * CHECKSUM_FACTOR) % MODULUS


def decode_trailer(trailer):
    if len(trailer) != TRAILER_SIZE or any(value not in HEX_BYTES for value in trailer):
        raise ValueError("GMax trailer must contain exactly 48 hexadecimal characters")
    encoded = trailer.decode("ascii")
    return tuple(int(encoded[offset : offset + 16], 16) for offset in (0, 16, 32))


def verify_trailer(trailer, checksum):
    try:
        message, signature_r, signature_s = decode_trailer(trailer)
    except ValueError:
        return False
    if message != checksum_message(checksum):
        return False
    left = (
        pow(PUBLIC_KEY, signature_r, MODULUS)
        * pow(signature_r, signature_s, MODULUS)
    ) % MODULUS
    right = pow(GENERATOR, message, MODULUS)
    return left == right


def create_trailer(payload, checksum):
    message = checksum_message(checksum)
    seed = hashlib.sha256(
        b"GMax 1.2 plug-in stamp\0" + bytes(payload)
    ).digest()
    nonce = int.from_bytes(seed, "big") % (GROUP_ORDER - 1) + 1
    while math.gcd(nonce, GROUP_ORDER) != 1:
        nonce = nonce % (GROUP_ORDER - 1) + 1

    signature_r = pow(GENERATOR, nonce, MODULUS)
    signature_s = (
        (message - PRIVATE_KEY * signature_r)
        * pow(nonce, -1, GROUP_ORDER)
    ) % GROUP_ORDER
    trailer = (
        "%016X%016X%016X" % (message, signature_r, signature_s)
    ).encode("ascii")
    if not verify_trailer(trailer, checksum):
        raise RuntimeError("generated GMax signature did not verify")
    return trailer


def inspect_stamp(data):
    checksum_offset = parse_pe(data)
    stored_checksum = struct.unpack_from("<I", data, checksum_offset)[0]
    if len(data) <= TRAILER_SIZE:
        return False, stored_checksum, 0

    payload_length = len(data) - TRAILER_SIZE
    trailer = data[payload_length:]
    if any(value not in HEX_BYTES for value in trailer):
        return False, stored_checksum, 0
    header_sum, computed_sum = mapped_checksum(data, payload_length)
    valid = (
        header_sum == stored_checksum
        and computed_sum == stored_checksum
        and verify_trailer(trailer, stored_checksum)
    )
    return valid, stored_checksum, computed_sum


def write_atomic(path, data):
    output_directory = os.path.dirname(os.path.abspath(path)) or os.curdir
    os.makedirs(output_directory, exist_ok=True)
    handle, temporary_path = tempfile.mkstemp(
        prefix=os.path.basename(path) + ".",
        suffix=".tmp",
        dir=output_directory,
    )
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temporary_path, path)
    except BaseException:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


def stamp(source_path, output_path, force=False):
    with open(source_path, "rb") as stream:
        source = bytearray(stream.read())
    checksum_offset = parse_pe(source)
    already_valid, old_checksum, _ = inspect_stamp(source)

    if already_valid and not force:
        if os.path.abspath(source_path) != os.path.abspath(output_path):
            write_atomic(output_path, source)
        print("Already stamped:", os.path.abspath(source_path))
        print("GMax checksum:", "0x%X" % old_checksum)
        return

    payload = source[:-TRAILER_SIZE] if already_valid else source
    checksum_offset = parse_pe(payload)
    _, computed_checksum = mapped_checksum(payload)
    struct.pack_into("<I", payload, checksum_offset, computed_checksum)
    header_sum, final_checksum = mapped_checksum(payload)
    if header_sum != computed_checksum or final_checksum != computed_checksum:
        raise RuntimeError("failed to update the PE checksum")

    trailer = create_trailer(payload, computed_checksum)
    result = payload + trailer
    valid, stored_checksum, verified_checksum = inspect_stamp(result)
    if not valid:
        raise RuntimeError(
            "final GMax stamp failed verification: stored=0x%X computed=0x%X"
            % (stored_checksum, verified_checksum)
        )

    write_atomic(output_path, result)
    print("Stamped:", os.path.abspath(output_path))
    print("Payload bytes:", len(payload))
    print("GMax checksum:", "0x%X" % computed_checksum)
    print("GMax trailer:", trailer.decode("ascii"))


def verify(path):
    with open(path, "rb") as stream:
        data = stream.read()
    valid, stored_checksum, computed_checksum = inspect_stamp(data)
    print("VALID" if valid else "INVALID", os.path.abspath(path))
    print("Stored checksum:", "0x%X" % stored_checksum)
    print("Computed checksum:", "0x%X" % computed_checksum)
    return valid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugins", nargs="+", help="Win32 GMax plug-in file(s)")
    parser.add_argument(
        "--output",
        help="output path for one plug-in; defaults to replacing each source",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing valid stamp with a newly generated stamp",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="verify stamps without changing files",
    )
    arguments = parser.parse_args()

    if arguments.output and len(arguments.plugins) != 1:
        parser.error("--output can only be used with one plug-in")
    if arguments.verify and (arguments.output or arguments.force):
        parser.error("--verify cannot be combined with --output or --force")

    success = True
    for plugin in arguments.plugins:
        source_path = os.path.abspath(plugin)
        if arguments.verify:
            success = verify(source_path) and success
        else:
            output_path = os.path.abspath(arguments.output or plugin)
            stamp(source_path, output_path, arguments.force)
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

# Canonical serialization and digests

All released JSON manifests, artifacts, examples, and expected-result documents
use UTF-8 JSON canonicalized with the JSON Canonicalization Scheme defined by
RFC 8785.

The following rules apply:

1. Producers reject duplicate object keys, non-finite numbers, invalid Unicode,
   and values that RFC 8785 cannot represent.
2. Released JSON files contain exactly the RFC 8785 canonical byte sequence.
3. A JSON artifact's `sha256` is the lowercase hexadecimal SHA-256 digest of its
   released canonical bytes.
4. The manifest digest is the SHA-256 digest of the released canonical manifest
   bytes. The manifest does not contain its own digest.
5. String timestamps are UTC instants ending in `Z`. Canonicalization does not
   reinterpret timestamps, units, or decimal values.
6. Producers calculate without intermediate rounding. Serialization follows the
   rounding rules in `DEC-02` before canonicalization.
7. A trailing newline is not part of canonical JSON and is not present in a
   released JSON artifact.

The `contractkit.canonical` module is the repository-neutral reference utility.
Implementations may use another RFC 8785 implementation if it produces
byte-for-byte identical output for the contract tests.

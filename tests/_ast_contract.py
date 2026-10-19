"""Version-stable AST contracts; legacy digest labels keep existing node IDs.

ast.dump's empty-field rendering changed across supported CPython versions.
Only the newer, empty type_params field is normalized away. Source positions
and formatting are not executable behavior; all other body fields are retained.
"""

import ast
import hashlib
import json


def stable_ast_hash(node):
    def normalize(value):
        if isinstance(value, ast.AST):
            return {"node": type(value).__name__, "fields": {
                key: normalize(item) for key, item in ast.iter_fields(value)
                if not (key == "type_params" and item == [])
            }}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value
    serialized = json.dumps(normalize(node), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


# Computed from the unchanged bodies in commit 2f6a465, never the candidate.
FROZEN_BODY_HASHES = {
    "a7b741989312a38f9ec67f742c411cee20642007b3405451378881cef6644533": "bea565043b9315e03ab9d33b142abccc7f2b0ff8402a614183a6eaacd81778ff",
    "9c632a7a29c5e767d0e84aeb7237fdfd9fdc4bedc32c83a63e63070550010cdf": "cd2e3812ef6d2c35aaa7e3b95e0b37394344c872fd7eca85e32f4dde36a64b52",
    "167d9f3ddbee70e29681986fad00ef3a57ac34a94f98c729d260ae917e2bca6d": "513a256494631adf9a0f790ce37443d04e13f6ee14bcd6e1498c3ae464f7129a",
    "c011436de2449fea831642ecc8c3808795ef7df0317eb1c165b158e7f6af95eb": "da0ece19f87b6a9bc086192f5d4da2b4670be9cf0fadbe3adfe64ebd04d727c7",
    "4061fdc6e5018fb3e3bf72ebc432edb5e620a0e657296fa9b554e77dc9966a95": "6827dbe89293e488b45b0444194d3abf59568f281dd57f3c6011a70499f85b83",
    "4ddf84bdcd0f72bd669c7b533f783e125451d2e10815823697a4b996393b5c7e": "4fff0fbc0f58609a910b07504ff652f678f9551682dc25448830606eb972536f",
    "da657770da548fb506ab40fe3e27e76e4d3fb224fbd0cd88923a755358a395e8": "bc5eb47fe4b9feca662c556d24208eb8e57b0ef8e86c339b7df36fe2a2213758"
}

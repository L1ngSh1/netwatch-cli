"""Canonicalization must retain semantic changes, not only fix version rendering."""

import ast

import pytest

from _ast_contract import stable_ast_hash


def fingerprint(source):
    return stable_ast_hash(ast.parse(source))


def test_locations_and_whitespace_do_not_change_the_contract():
    assert fingerprint('answer = 1\n') == fingerprint('# comment\nanswer=1\n\n')


@pytest.mark.parametrize("changed", ['answer = 2', 'answer = -1', 'answer = "1"'])
def test_literal_and_type_changes_break_the_contract(changed):
    assert fingerprint('answer = 1') != fingerprint(changed)

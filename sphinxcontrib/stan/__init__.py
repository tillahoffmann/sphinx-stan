from __future__ import annotations
import re
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.util.docfields import Field, TypedField
from typing import Union


# Regular expression patterns for parsing and substitution.
TYPE_PATTERN = re.compile(r"(?:array\s*\[(?P<dims>[,\s]*)\])?\s*(?P<base_type>\w+)\s+")
IDENTIFIER_PATTERN = re.compile(r"(?P<identifier>\w+)\s*")
OPEN_PATTERN = re.compile(r"\(\s*")
CLOSE_PATTERN = re.compile(r"\)\s*")
SEPARATOR_PATTERN = re.compile(r",\s*")
NAMED_FIELD_PATTERN = re.compile(r"@(?P<field>param)\s+(?P<value>\w+)")
FIELD_PATTERN = re.compile(r"@(?P<field>returns|throws)")
COMMENT_PREFIX_PATTERN = re.compile(r"^(/\*\*)|(\*/)|(\*\s?)")


def replace_doxygen_fields(line: str) -> str:
    """
    Replace doxygen-style fields with sphinx fields. See
    https://mc-stan.org/docs/stan-users-guide/documenting-functions.html for details.
    """
    line = COMMENT_PREFIX_PATTERN.sub("", line)
    line = NAMED_FIELD_PATTERN.sub(r":\g<field> \g<value>:", line)
    line = FIELD_PATTERN.sub(r":\g<field>:", line)
    return line


def match_and_consume(pattern: Union[str, re.Pattern], text: str) -> tuple[re.Match, str]:
    """
    Match a pattern and consume the text.

    Args:
        pattern: Pattern to match.
        text: Text to match:

    Returns:
        match: Matched pattern.
        text: Remaining text after consuming the matched pattern.
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    match = pattern.match(text)
    if not match:
        raise ValueError(f"{pattern} did not match `{text}`")
    return match, text[match.span()[1]:]


def parse_type(text: str) -> tuple[str, Union[str, tuple[str, int]]]:
    """
    Parse a type declaration.

    Args:
        text: Text to parse.

    Returns:
        type: Type name or tuple of `(type_name, num_array_dims)`.
        text: Remaining text after consuming the type declaration.
    """
    match, text = match_and_consume(TYPE_PATTERN, text)
    base_type = match.group("base_type")
    if (dims := match.group("dims")) is not None:
        dims = dims.count(",") + 1
        return (base_type, dims), text
    return base_type, text


def parse_identifier(text: str) -> tuple[str, str]:
    """
    Parse an identifier.

    Args:
        text: Text to parse.

    Returns:
        identifier: Identifier name.
        text: Remaining text after consuming the identifier.
    """
    match, text = match_and_consume(IDENTIFIER_PATTERN, text)
    return match.group("identifier"), text


def parse_signature(text: str) -> tuple[dict, str]:
    """
    Parse a function signature.

    Args:
        text: Text to parse.

    Returns:
        signature: Dictionary comprising a function identifier, return type, and list of arguments.
        text: Remaining text after consuming the signature.
    """
    return_type, text = parse_type(text)
    identifier, text = parse_identifier(text)
    _, text = match_and_consume(OPEN_PATTERN, text)
    args = []
    while True:
        try:
            arg_type, text = parse_type(text)
            arg_identifier, text = parse_identifier(text)
            args.append({
                "identifier": arg_identifier,
                "type": arg_type,
            })
            _, text = match_and_consume(SEPARATOR_PATTERN, text)
        except ValueError:
            break
    _, text = match_and_consume(CLOSE_PATTERN, text)
    return {
        "identifier": identifier,
        "type": return_type,
        "args": args,
    }, text


def desc_type(node: addnodes.desc_signature, type):
    """
    Describe a type declaration.
    """
    if isinstance(type, tuple):
        type, dims = type
        node += addnodes.desc_sig_keyword_type("", "array")
        node += addnodes.desc_sig_space()
        node += addnodes.desc_sig_punctuation("", "[")
        for _ in range(dims - 1):
            node += addnodes.desc_sig_punctuation("", ",")
        node += addnodes.desc_sig_punctuation("", "]")
        node += addnodes.desc_sig_space()
    node += addnodes.desc_sig_keyword_type("", type)


class StanFunctionDirective(ObjectDescription):
    """
    Directive for displaying user-defined functions.
    """
    doc_field_types = [
        TypedField("parameter", label="Parameters", names=("param",), typerolename="class",
                   typenames=("paramtype", "type"), can_collapse=True),
        Field("returnvalue", label="Returns", has_arg=False, names=("return",)),
        Field("throws", label="Throws", has_arg=False, names=("throws",)),
    ]

    def handle_signature(self, signature: str, node: addnodes.desc_signature) -> str:
        signature, _ = parse_signature(signature)

        desc_type(node, signature["type"])
        node += addnodes.desc_sig_space()
        node += addnodes.desc_name(signature["identifier"], signature["identifier"])
        params = addnodes.desc_parameterlist()
        for arg in signature.get("args", []):
            param = addnodes.desc_parameter()
            desc_type(param, arg["type"])
            param += addnodes.desc_sig_space()
            param += addnodes.desc_sig_name("", arg["identifier"])
            params += param
        node += params
        return signature["identifier"]

    def run(self):
        if self.has_content:
            self.content.data = [replace_doxygen_fields(line) for line in self.content.data]
        return super().run()


class StanDomain(Domain):
    name = "stan"
    object_types = {
        "function": ObjType("function", "func", "obj"),
    }
    directives = {
        "function": StanFunctionDirective,
    }


def setup(app: Sphinx) -> None:
    app.add_domain(StanDomain)

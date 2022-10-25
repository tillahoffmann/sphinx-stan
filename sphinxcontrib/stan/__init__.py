from __future__ import annotations
from docutils import nodes
import re
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util.docfields import Field, TypedField
from sphinx.util.docutils import SphinxDirective
from sphinx.util.logging import getLogger
from sphinx.util.nodes import make_refnode
from typing import Iterable, Union
import uuid


LOGGER = getLogger(__name__)


# Regular expression patterns for parsing and substitution.
TYPE_PATTERN = re.compile(r"(?:array\s*\[(?P<dims>[,\s]*)\])?\s*(?P<base_type>\w+)")
IDENTIFIER_PATTERN = re.compile(r"(?P<identifier>\w+)\s*")
OPEN_PATTERN = re.compile(r"\(\s*")
CLOSE_PATTERN = re.compile(r"\)\s*")
SEPARATOR_PATTERN = re.compile(r",\s*")
NAMED_FIELD_PATTERN = re.compile(r"@(?P<field>param)\s+(?P<value>\w+)")
FIELD_PATTERN = re.compile(r"@(?P<field>return|throws)")
COMMENT_PREFIX_PATTERN = re.compile(r"^(/\*\*)|(\*/)|(\*\s?)")
WHITESPACE_PATTERN = re.compile(r"\s+")
TYPED_IDENTIFIER_PATTERN = re.compile(r"(?:array\s*\[[,\s]*\]\s*)?\w+\s+\w+")
FUNCTION_PATTERN = re.compile(
    fr"(?:/\*\*(?P<doc>.*?)\*/\s*)?(?P<signature>{TYPED_IDENTIFIER_PATTERN.pattern}"
    fr"\((?:{TYPED_IDENTIFIER_PATTERN.pattern})*(?:\s*,\s*{TYPED_IDENTIFIER_PATTERN.pattern})*\))",
    re.S
)


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


def parse_signature(text: str, parse_arg_identifiers: bool = True, parse_return_type: bool = True) \
        -> tuple[dict, str]:
    """
    Parse a function signature.

    Args:
        text: Text to parse.

    Returns:
        signature: Dictionary comprising a function identifier, return type, and list of arguments.
        text: Remaining text after consuming the signature.
        parse_arg_identifiers: Whether to parse argument identifiers.
        parse_return_type: Whether to parse the return type.
    """
    return_type = None
    if parse_return_type:
        return_type, text = parse_type(text)
        _, text = match_and_consume(WHITESPACE_PATTERN, text)
    identifier, text = parse_identifier(text)
    _, text = match_and_consume(OPEN_PATTERN, text)
    args = []
    while True:
        try:
            arg = {}
            arg["type"], text = parse_type(text)
            if parse_arg_identifiers:
                _, text = match_and_consume(WHITESPACE_PATTERN, text)
                arg["identifier"], text = parse_identifier(text)
            else:
                arg["identifier"] = None
            args.append(arg)
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

    def add_target_and_index(self, name: str, sig: str, signode: addnodes.desc_signature) -> None:
        node_id = str(uuid.uuid4())
        signode["ids"].append(node_id)
        self.env.get_domain("stan").add_function(sig, node_id)


class StanAutoDocDirective(SphinxDirective):
    @staticmethod
    def _parse_members(args: str):
        members = []
        for arg in args.split(";"):
            arg = arg.strip()
            try:
                signature, _ = parse_signature(arg, parse_arg_identifiers=False,
                                               parse_return_type=False)
            except ValueError:
                signature = {"identifier": arg}
            members.append(signature)
        return members

    required_arguments = 1
    has_content = False
    option_spec = {
        "members": _parse_members,
    }

    def run(self):
        # Load the stan file and get all the signatures.
        stan_file, = self.arguments
        with open(stan_file) as fp:
            text = fp.read()

        candidate_signatures = []
        for doc, unparsed_signature in FUNCTION_PATTERN.findall(text):
            signature, _ = parse_signature(unparsed_signature)
            signature["input"] = unparsed_signature
            signature["doc"] = doc
            candidate_signatures.append(signature)

        # Use all signatures if no members are given or filter preserving the requested order.
        if self.options["members"]:
            signatures = []
            for member in self.options["members"]:
                num_signatures = 0
                for candidate in candidate_signatures:
                    if match_overloaded(member, candidate):
                        signatures.append(candidate)
                        num_signatures += 1
                if num_signatures == 0:
                    LOGGER.warning("found no match for %s in `%s`", member, stan_file)
        else:
            signatures = candidate_signatures

        # TODO: deduplicate signatures

        # Add all the functions to the document by calling the documentation directive.
        node = nodes.container()
        for signature in signatures:
            from docutils.statemachine import StringList
            content = StringList([line.rstrip("\n") for line in signature["doc"].split("\n")])
            directive = StanFunctionDirective("stan:function", [signature["input"]], {}, content, 0,
                                              0, None, self.state, self.state_machine)
            node += directive.run()

        return [node]


def match_overloaded(reference: dict, candidate: dict) -> bool:
    """
    Determine whether the reference signature matches a candidate.
    """
    if reference["identifier"] != candidate["identifier"]:
        return False  # Definitely can't match if the identifiers are different.
    if reference.get("args") is None:
        return True  # Use a greedy match if there are no argument types.
    # Check whether argument types match.
    return [arg["type"] for arg in reference["args"]] == [arg["type"] for arg in candidate["args"]]


class StanDomain(Domain):
    name = "stan"
    object_types = {
        "function": ObjType("function", "func", "obj"),
    }
    roles = {
        "func": XRefRole(),
    }
    directives = {
        "function": StanFunctionDirective,
        "autodoc": StanAutoDocDirective,
    }
    initial_data = {
        "functions": [],
    }

    def get_objects(self) -> Iterable[tuple[str, str, str, str, str, int]]:
        """
        Yield a tuple comprising

        - name: fully-qualified name.
        - dispname: display name.
        - type: a key in `self.object_types`.
        - docname: document where the object is declared.
        - anchor: anchor name for the object.
        - priority: 1 (default), 0 (important), 2 (unimportant), -1 (hidden).
        """
        for signature in self.data["functions"]:
            yield (signature["identifier"], signature["identifier"], "function",
                   signature["docname"], signature["anchor"], 1)

    def resolve_xref(self, env, fromdocname: str, builder, typ: str, target: str, node, contnode):
        # Try to parse the full signature and revert to just the name if not possible.
        try:
            target, _ = parse_signature(target, parse_arg_identifiers=False,
                                        parse_return_type=False)
        except ValueError:
            target = {"identifier": target}
        # Iterate over all functions to try and match the requested target.
        results = []
        for signature in self.data["functions"]:
            if not match_overloaded(target, signature):
                continue
            # This was a fully-qualified match.
            if target.get("args") is not None:
                results = [signature]
                break
            results.append(signature)

        if not results:
            LOGGER.warning("failed to resolve Stan function reference `%s`", target)
            return

        for result in results:
            todocname = result["docname"]
            target_id = result["anchor"]

        if len(results) > 1:
            LOGGER.warning(
                "multiple Stan functions found for reference `%s`: %s (using `%s`); qualify the "
                "target by specifying argument types in the format "
                "`{function_name}({arg1_type}, {arg2_type})`, e.g., `add(array [,] real, int)`",
                target, target_id, results
            )

        return make_refnode(builder, fromdocname, todocname, target_id, contnode, target_id)

    def add_function(self, sig: str, anchor: str) -> None:
        """
        Add a function to the domain.
        """
        signature, _ = parse_signature(sig)
        signature["docname"] = self.env.docname
        signature["anchor"] = anchor
        self.data["functions"].append(signature)


def setup(app: Sphinx) -> None:
    app.add_domain(StanDomain)

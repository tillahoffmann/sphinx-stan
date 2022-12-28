from __future__ import annotations
from docutils import nodes
from docutils.statemachine import StringList
from pathlib import Path
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
from typing import Callable, Iterable, Optional, Union
import uuid


LOGGER = getLogger(__name__)


class MatchNotFoundError(ValueError):
    """
    No regular expression match was found.
    """


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
        raise MatchNotFoundError(f"{pattern} did not match `{text}`")
    return match, text[match.span()[1]:]


class TypedIdentifier:
    TYPE_PATTERN = re.compile(r"(?:array\s*\[(?P<dims>[,\s]*)\])?\s*(?P<base_type>\w+)")
    IDENTIFIER_PATTERN = re.compile(r"(?P<identifier>\w+)\s*")
    WHITESPACE_PATTERN = re.compile(r"\s+")

    def __init__(self, identifier: str, type: str, dims: Optional[int] = None,
                 text: Optional[str] = None) -> None:
        self.identifier = identifier
        self.type = type
        self.dims = dims
        self.text = text

    @classmethod
    def parse(cls, text: str, parse_type: bool = True, parse_identifier: bool = True,
              return_remainder: bool = False, **kwargs) -> tuple[TypedIdentifier, str]:
        """
        Parse a typed identifier.

        Args:
            text: Text to parse.
            parse_type: Whether to parse the type.
            parse_identifier: Whether to parse the identifier.
            **kwargs: Keyword arguments passed to the constructor.

        Returns: Parsed typed identifier.
        """
        identifier = type = dims = None
        remainder = text
        if parse_type:
            match, remainder = match_and_consume(cls.TYPE_PATTERN, remainder)
            type = match.group("base_type")
            dims = match.group("dims")
            if dims is not None:
                dims = dims.count(",") + 1
        if parse_type and parse_identifier:
            _, remainder = match_and_consume(cls.WHITESPACE_PATTERN, remainder)
        if parse_identifier:
            match, remainder = match_and_consume(cls.IDENTIFIER_PATTERN, remainder)
            identifier = match.group("identifier")
        instance = cls(identifier, type, dims, text=text, **kwargs)
        if return_remainder:
            return instance, remainder
        return instance

    def desc(self, node: addnodes.desc_signature, desc_name: Optional[Callable] = None) -> None:
        """
        Describe the object using Sphinx nodes.
        """
        if self.dims:
            node += addnodes.desc_sig_keyword_type("", "array")
            node += addnodes.desc_sig_space()
            node += addnodes.desc_sig_punctuation("", "[")
            for _ in range(self.dims - 1):
                node += addnodes.desc_sig_punctuation("", ",")
            node += addnodes.desc_sig_punctuation("", "]")
            node += addnodes.desc_sig_space()
        node += addnodes.desc_sig_keyword_type("", self.type)
        if self.identifier:
            node += addnodes.desc_sig_space()
            desc_name = desc_name or addnodes.desc_sig_name
            node += desc_name(self.identifier, self.identifier)

    def __eq__(self, other: TypedIdentifier) -> bool:
        return self.identifier == other.identifier and self.type == other.type \
            and self.dims == other.dims

    def __repr__(self) -> str:
        full_type = self.type
        if self.dims:
            full_type = f"array [{',' * (self.dims - 1)}] {full_type}"
        parts = [full_type, self.identifier]
        if not any(parts):
            return "..."
        return " ".join([str(part) for part in parts if part])


class Signature(TypedIdentifier):
    """
    Stan function signature.
    """
    OPEN_PATTERN = re.compile(r"\(\s*")
    CLOSE_PATTERN = re.compile(r"\)\s*")
    SEPARATOR_PATTERN = re.compile(r",\s*")

    def __init__(self, identifier: str, type: str, dims: Optional[int] = None,
                 args: list[TypedIdentifier] = None, doc: Optional[str] = None,
                 source_info: Optional[tuple[str, int]] = None, text: Optional[str] = None) -> None:
        super().__init__(identifier, type, dims, text)
        self.args = args
        self.doc = doc
        self.source_info = source_info

    @classmethod
    def parse(cls, text: str, parse_type: bool = True, parse_identifier: bool = True,
              parse_arg_identifiers: bool = True, doc: Optional[str] = None,
              source_info: Optional[tuple[str, int]] = None, return_remainder: bool = False,
              **kwargs) -> tuple[TypedIdentifier, str]:
        instance, text = super().parse(text, parse_type, parse_identifier, doc=doc,
                                       source_info=source_info, return_remainder=True, **kwargs)
        try:
            _, text = match_and_consume(cls.OPEN_PATTERN, text)
        except MatchNotFoundError:
            if return_remainder:
                return instance, text
            return instance
        args = []
        while True:
            try:
                arg, text = TypedIdentifier.parse(text, parse_identifier=parse_arg_identifiers,
                                                  return_remainder=True)
                args.append(arg)
                _, text = match_and_consume(cls.SEPARATOR_PATTERN, text)
            except MatchNotFoundError:
                break
        _, text = match_and_consume(cls.CLOSE_PATTERN, text)
        instance.args = args
        if return_remainder:
            return instance, text
        return instance

    def matches(self, other: Signature) -> int:
        """
        Determine if the signature matches another for the purposes of resolving overloaded
        functions.

        Args:
            other: Fully-qualified signature to match.

        Returns:

            - 0 if the signature does not match
            - 1 if the signature matches by identifier only
            - 2 if the signature matches by identifier and argument types
        """
        if other.args is None:
            raise ValueError("signature to match is missing its argument list")
        if self.identifier != other.identifier:
            return 0
        if self.type and self.type != other.type:
            return 0
        if self.args is None:
            return 1
        if len(self.args) != len(other.args):
            return 0
        for a, b in zip(self.args, other.args):
            if a.type != b.type or a.dims != b.dims:
                return 0
            if a.identifier and a.identifier != b.identifier:
                return 0
        return 2

    def desc(self, node: addnodes.desc_signature) -> None:
        super().desc(node, addnodes.desc_name)
        if self.args is None:
            LOGGER.warning("signature `%s` is missing arguments for its description")
        params = addnodes.desc_parameterlist()
        for arg in self.args:
            param = addnodes.desc_parameter()
            arg.desc(param)
            params += param
        node += params

    def __eq__(self, other: TypedIdentifier) -> bool:
        return super().__eq__(other) and self.args == other.args

    def __repr__(self) -> str:
        value = super().__repr__()
        if self.args is None:
            return value
        value = f"{value}({', '.join(map(str, self.args))})"
        if self.source_info:
            filename, lineno = self.source_info
            value = f"{value} at {filename}:{lineno}"
        return value


class StanFunctionDirective(ObjectDescription):
    """
    Directive for displaying user-defined functions.
    """
    NAMED_FIELD_PATTERN = re.compile(r"@(?P<field>param)\s+(?P<value>\w+)")
    FIELD_PATTERN = re.compile(r"@(?P<field>return|throws)")
    COMMENT_PREFIX_PATTERN = re.compile(r"^(?:(/\*\*)|(\*/)|(\*\s?))")

    doc_field_types = [
        TypedField("parameter", label="Parameters", names=("param",), typerolename="class",
                   typenames=("paramtype", "type"), can_collapse=True),
        Field("returnvalue", label="Returns", has_arg=False, names=("return",)),
        Field("throws", label="Throws", has_arg=False, names=("throws",)),
    ]

    def handle_signature(self, text: str, node: addnodes.desc_signature) -> str:
        signature = Signature.parse(text, source_info=self.get_source_info())
        signature.desc(node)
        return signature.identifier

    def run(self):
        if self.has_content:
            self.content.data = [self._replace_doxygen_fields(line) for line in self.content.data]
        return super().run()

    def add_target_and_index(self, name: str, sig: str, signode: addnodes.desc_signature) -> None:
        node_id = str(uuid.uuid4())
        signode["ids"].append(node_id)
        signature = Signature.parse(sig, source_info=self.get_source_info())
        self.env.get_domain("stan").add_function(sig, node_id, signature)

    @classmethod
    def _replace_doxygen_fields(cls, line: str) -> str:
        """
        Replace doxygen-style fields with sphinx fields. See
        https://mc-stan.org/docs/stan-users-guide/documenting-functions.html for details.
        """
        line = cls.COMMENT_PREFIX_PATTERN.sub("", line)
        line = cls.NAMED_FIELD_PATTERN.sub(r":\g<field> \g<value>:", line)
        line = cls.FIELD_PATTERN.sub(r":\g<field>:", line)
        return line


class StanAutoDocDirective(SphinxDirective):
    TYPED_IDENTIFIER_PATTERN = re.compile(r"(?:array\s*\[[,\s]*\]\s*)?\w+\s+\w+")
    FUNCTION_PATTERN = re.compile(
        fr"(?:/\*\*(?P<doc>.*?)\*/\s*)?(?P<signature>{TYPED_IDENTIFIER_PATTERN.pattern}"
        fr"\(\s*(?:{TYPED_IDENTIFIER_PATTERN.pattern})*"
        fr"(?:\s*,\s*{TYPED_IDENTIFIER_PATTERN.pattern})*\s*\))",
        re.S
    )

    @staticmethod
    def _parse_members(args: str):
        if not args:
            return []
        members = []
        for arg in args.split(";"):
            arg = arg.strip()
            try:
                signature = Signature.parse(arg, parse_arg_identifiers=False, parse_type=False)
            except MatchNotFoundError:
                signature = Signature(arg, None)
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
        stan_file = Path(self.env.srcdir) / Path(self.env.docname).parent / stan_file
        try:
            with open(stan_file) as fp:
                text = fp.read()
        except FileNotFoundError:
            LOGGER.warning("`%s` does not exist")
            return []

        candidate_signatures = []
        for match in self.FUNCTION_PATTERN.finditer(text):
            groups = match.groupdict()
            unparsed_signature = groups["signature"].replace("\n", " ")
            lineno = text[:match.end()].count("\n") + 1
            source_info = (stan_file, lineno)
            signature = Signature.parse(unparsed_signature, doc=groups["doc"],
                                        source_info=source_info)
            candidate_signatures.append(signature)
        if not candidate_signatures:
            LOGGER.warning("no signatures found in `%s`; is it empty?", stan_file)

        # Use all signatures if no members are given or filter preserving the requested order.
        if members := self.options.get("members"):
            signatures = []
            member: Signature
            for member in members:
                num_signatures = 0
                for candidate in candidate_signatures:
                    if member.matches(candidate):
                        signatures.append(candidate)
                        num_signatures += 1
                if num_signatures == 0:
                    LOGGER.warning("found no match for `%s` in `%s`", member, stan_file)
        else:
            signatures = candidate_signatures

        # TODO: deduplicate signatures

        # Add all the functions to document by calling the documentation directive.
        container = nodes.container()
        signature: Signature
        for signature in signatures:
            if signature.doc:
                content = StringList([line.rstrip("\n") for line in signature.doc.split("\n")])
            else:
                content = StringList([])
            directive = StanFunctionDirective(
                "stan:function", [signature.text], {}, content, 0, 0, None, self.state,
                self.state_machine,
            )
            container += directive.run()

        return [container]


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
        for docname, anchor, signature in self.data["functions"]:
            yield (signature.identifier, signature.identifier, "function", docname, anchor, 1)

    def resolve_xref(self, env, fromdocname: str, builder, typ: str, target: str, node, contnode):
        # Try to parse the full signature and revert to just the name if not possible.
        try:
            target = Signature.parse(target, parse_arg_identifiers=False, parse_type=False)
        except ValueError:
            target = Signature(target, None)
        # Iterate over all functions to try and match the requested target.
        results = []
        for docname, anchor, signature in self.data["functions"]:
            match = target.matches(signature)
            if not match:
                continue
            # This was a fully-qualified match.
            if match == 2:
                results = [(docname, anchor, signature)]
                break
            results.append((docname, anchor, signature))

        if not results:
            LOGGER.warning("Stan func reference target not found `%s`", target)
            return

        for todocname, target_id, target_signature in results:
            break

        if len(results) > 1:
            LOGGER.warning(
                "multiple Stan functions found for reference `%s` at `%s:%d`: %s (using `%s`); "
                "qualify the target by specifying argument types in the format "
                "`{function_name}({arg1_type}, {arg2_type})`, e.g., `add(array [,] real, int)`",
                target, node.source, node.line,
                "; ".join([str(signature) for *_, signature in results]), target_signature,
            )

        return make_refnode(builder, fromdocname, todocname, target_id, contnode, target_id)

    def add_function(self, sig: str, anchor: str, signature: Signature) -> None:
        """
        Add a function to the domain.
        """
        self.data["functions"].append((self.env.docname, anchor, signature))


def setup(app: Sphinx) -> None:
    app.add_domain(StanDomain)

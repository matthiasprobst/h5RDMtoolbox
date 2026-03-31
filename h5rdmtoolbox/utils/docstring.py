"""Docstring parsing utilities for h5rdmtoolbox."""

import re
import warnings
from typing import Callable, Dict, List, Tuple, Optional


class DocStringParser:
    """Parses a docstring into abstract, parameters, returns and notes, allowing for additional parameters to be added
    and then reassembled into a new docstring."""

    def __init__(
        self, cls_or_method: Callable, additional_parameters: Optional[Dict] = None
    ):
        """Initialize the DocStringParser.

        Parameters
        ----------
        cls_or_method : Callable
            Class or method to parse docstring from.
        additional_parameters : dict, optional
            Additional parameters to add to the docstring.
        """
        self._callable = cls_or_method
        self.original_docstring = cls_or_method.__doc__
        self.abstract, self.parameters, self.returns, self.notes = (
            DocStringParser.parse_docstring(self.original_docstring)
        )
        self.additional_parameters = {}
        if additional_parameters is None:
            additional_parameters = {}
        self.add_additional_parameters(additional_parameters)

    def get_original_doc_string(self) -> str:
        """Returns the original docstring.

        Returns
        -------
        str
            Original docstring.
        """
        return self.original_docstring

    def get_docstring(self) -> str:
        """Reassembles the docstring from the parsed components.

        Returns
        -------
        str
            Reassembled docstring.
        """
        from ..convention.standard_attributes import DefaultValue

        new_doc = ""
        if self.abstract:
            for a in self.abstract:
                new_doc += f"{a}\n"
        new_doc += f"\n\nParameters\n----------"
        for k in self.parameters:
            new_doc += (
                f"\n{k['name']}: {k['type']} = {k['default']}\n\t{k['description']}"
            )

        new_doc += f"\n\nStandard Attributes\n-------------------"
        for ak, av in self.additional_parameters.items():
            if av["default"] == DefaultValue.EMPTY:
                new_doc += f"\n{ak}: {av['type']} \n\t{av['description']}"
            else:
                new_doc += (
                    f"\n{ak}: {av['type']} = {av['default']}\n\t{av['description']}"
                )
        new_doc += "\n"

        if self.returns:
            new_doc += f"\n\nReturns\n-------"

            for k in self.returns:
                new_doc += f"\n{k['name']}: {k['type']}\n\t{k['description']}"

        if self.notes:
            new_doc += f"\n\nNotes"
            for n in self.notes:
                new_doc += f"\n{n}"

        return new_doc

    def restore_docstring(self):
        """Restores the original docstring."""
        self._callable.__doc__ = self.original_docstring

    def update_docstring(self) -> None:
        """Updates the docstring of the class, method or function with the new docstring."""
        import h5rdmtoolbox as h5tbx

        if self._callable.__name__ == "create_dataset":
            h5tbx.Group.__dict__[self._callable.__name__].__doc__ = self.get_docstring()
        elif self._callable.__name__ == "create_group":
            h5tbx.Group.__dict__[self._callable.__name__].__doc__ = self.get_docstring()
        else:
            h5tbx.File.__dict__["__init__"].__doc__ = self.get_docstring()

    def add_additional_parameters(self, additional_parameters: Dict):
        """Adds additional parameters to the docstring.

        Parameters
        ----------
        additional_parameters : dict
            Dictionary of additional parameters to add to the docstring.
            Must contain 'description', 'default', and 'type' keys.
        """
        _required = ("description", "default", "type")
        for k, v in additional_parameters.items():
            for _r in _required:
                if _r not in v:
                    raise ValueError(
                        f'Item "{_r}" missing for additional parameter "{k}"'
                    )
        for k, v in additional_parameters.items():
            self.additional_parameters.update({k: v})

    @staticmethod
    def parse_parameter(param_str: str) -> Tuple[str, str, Optional[str]]:
        """Parse a parameter string.

        Parameters
        ----------
        param_str : str
            Parameter string to parse.

        Returns
        -------
        tuple
            Tuple of (param_name, param_type, param_default).
        """
        pattern = r"^\s*([\w\d_*]+)\s*:\s*(.+?)(?:\s*,\s*optional(?:\s*=\s*(.*))?)?$"
        match = re.match(pattern, param_str)

        if match:
            param_name = match.group(1).strip()
            param_type = match.group(2).strip()
            param_default = match.group(3).strip() if match.group(3) else None
            return param_name, param_type, param_default
        return None, None, None

    @staticmethod
    def parse_docstring(docstring) -> Tuple[List, List, List, List]:
        """Parses a docstring into abstract, parameters, returns and notes.

        Parameters
        ----------
        docstring : str or None
            Docstring to parse.

        Returns
        -------
        tuple
            Tuple of (abstract, parameters, returns, notes).
        """
        abstract = None
        kw = []
        rkw = []
        notes_lines = []

        if not docstring:
            return abstract, kw, rkw, notes_lines

        lines = docstring.strip().split("\n")

        current_section = None
        nlines = len(lines)
        for iline, line in enumerate(lines):
            line = line.strip()

            if line in ["Parameters", "Returns", "Notes"]:
                current_section = line.lower()
                if abstract is None:
                    abstract = [l.strip() for l in lines[:iline]]
            elif current_section == "parameters":
                if line:
                    param_info = line.split(":")
                    if len(param_info) >= 2:
                        param_name, param_type, param_default = (
                            DocStringParser.parse_parameter(line)
                        )

                        desc_lines = []
                        for i in range(iline + 1, nlines):
                            if (
                                lines[i] == ""
                                or DocStringParser.parse_parameter(lines[i]) is not None
                            ):
                                break
                            desc_lines.append(lines[i].strip())
                        desc = "\n\t".join(desc_lines)
                        current_param = {
                            "name": param_name,
                            "type": param_type,
                            "default": param_default,
                            "description": desc.strip(),
                        }
                        kw.append(current_param)
            elif current_section == "notes":
                notes_lines.append(line.strip())
            elif current_section == "returns":
                param_info = line.split(":")
                if len(param_info) >= 2:
                    param_name, param_type, param_default = (
                        DocStringParser.parse_parameter(line)
                    )
                    desc_lines = []
                    for i in range(iline + 1, nlines):
                        if (
                            lines[i] == ""
                            or DocStringParser.parse_parameter(lines[i]) is not None
                        ):
                            break
                        desc_lines.append(lines[i].strip())
                    desc = "\n\t".join(desc_lines)
                    current_ret_param = {
                        "name": param_name,
                        "type": param_type,
                        "default": param_default,
                        "description": desc.strip(),
                    }
                    rkw.append(current_ret_param)

        return abstract, kw, rkw, notes_lines


def deprecated(version: str, msg: str, removing_in: Optional[str] = None):
    """Decorator for deprecated methods or functions.

    Parameters
    ----------
    version : str
        Version when the deprecation started.
    msg : str
        Deprecation message.
    removing_in : str, optional
        Version when the feature will be removed.

    Returns
    -------
    Callable
        Decorator function.
    """

    def deprecated_decorator(func: Callable) -> Callable:
        def depr_func(*args, **kwargs):
            if removing_in:
                warnings.warn(
                    f"{func.__name__} is deprecated since {version}. Will be removed in {removing_in}."
                    f" {msg}",
                    DeprecationWarning,
                )
            else:
                warnings.warn(
                    f"{func.__name__} is deprecated since {version}. {msg}",
                    DeprecationWarning,
                )
            return func(*args, **kwargs)

        return depr_func

    return deprecated_decorator

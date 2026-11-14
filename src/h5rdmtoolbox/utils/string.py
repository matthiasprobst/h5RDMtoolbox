"""String utilities for h5rdmtoolbox."""

from re import sub as re_sub


def remove_special_chars(
    input_string: str, keep_special: str = "/_", replace_spaces: str = "_"
) -> str:
    """Generally removes all characters that are no number or letter.

    Per default, underscores and forward slashes are kept and spaces are replaced
    with underscores. Typically used to clean up dataset names that contain special
    characters or spaces which are not allowed for usage in natural naming.

    Parameters
    ----------
    input_string : str
        String with special characters to be removed.
    keep_special : str, optional
        Specifies which special characters to keep. Put them in one single string.
        Default is '/_'.
    replace_spaces : str, optional
        The string that replaces spaces in the input string. Default is '_'.
        If no action wanted, put False.

    Returns
    -------
    str
        Processed string without special characters and replaced spaces.
    """
    if keep_special:
        _cleaned_str = re_sub("[^a-zA-Z0-9%s ]" % keep_special, "", input_string)
    else:
        _cleaned_str = re_sub("[^a-zA-Z0-9 ]", "", input_string)
    if replace_spaces:
        return _cleaned_str.replace(" ", replace_spaces)
    return _cleaned_str

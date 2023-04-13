import typing


def flatten(list_of_lists: typing.List[typing.List]) -> typing.List:
    """flattens a list of lists"""
    # https://stackabuse.com/python-how-to-flatten-list-of-lists/
    if len(list_of_lists) == 0:
        return list_of_lists
    if isinstance(list_of_lists[0], list):
        return flatten(list_of_lists[0]) + flatten(list_of_lists[1:])
    return list_of_lists[:1] + flatten(list_of_lists[1:])

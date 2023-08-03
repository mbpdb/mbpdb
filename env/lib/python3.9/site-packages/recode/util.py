"""
Utils for use throughout the package
"""

from itertools import islice, chain


def take(n, iterable):
    """
    >>> assert take(3, [1,2,3,4,5]) == [1,2,3]
    """
    return list(islice(iterable, n))


def spy(iterable, n=1):
    """
    >>> peek, it = spy([1,2,3], 1)
    >>> assert peek == [1]
    >>> assert next(it) == 1
    >>> assert list(it) == [2,3]
    """
    it = iter(iterable)
    head = take(n, it)

    return head.copy(), chain(head, it)


type_to_struct = {"<class 'int'>": 'h', "<class 'float'>": 'd'}


def get_struct(str_type):
    """
    >>> assert get_struct(type(1)) == 'h'
    >>> assert get_struct(type(1.001)) == 'd'
    """
    str_type = str(str_type)
    return type_to_struct[str_type]


def list_of_dicts(cols, vals):
    """
    >>> cols = ['foo', 'bar']
    >>> vals = [[1,2], [3,4], [5,6]]
    >>> list_of_dicts(cols, vals)
    [{'foo': 1, 'bar': 2}, {'foo': 3, 'bar': 4}, {'foo': 5, 'bar': 6}]
    """
    frames = []
    for group in vals:
        row = {}
        for i in range(len(group)):
            row[cols[i]] = group[i]
        frames.append(row)
    return frames

def _get_first_N_lines_from_file(filename, N):
    """
    Returns the first N lines from a file
    """
    with open(filename, "r") as f:
        head = [next(f) for x in range(N)]
    return head


def _get_headernames_from_pivview_dat(filename):
    header_names = ''
    with open(filename, "r") as f:
        lines = f.readlines()
        for l in lines:
            if "VARIABLES" in l:
                header_names = l.strip().split(' = ')
    return header_names[1].replace(',', '').replace('"', '').split(' ')


def _get_ijk_from_pivview_dat(filename):
    with open(filename, "r") as f:
        lines = f.readlines()
        for l in lines:
            if "ZONE" in l:
                data = l.strip().split(' ')[1:4]
    I, J = int(data[0][2:-1]), int(data[1][2:-1])
    try:
        K = int(data[2][2:-1])
    except:
        K = 1
    return I, J, K


def _get_header_line(fname):
    """searches for the first line without a hashtag"""
    i = -1
    with open(fname, "r") as f:
        _lines = f.readlines()
        for i, _line in enumerate(_lines):
            if _line[0] == '#':
                pass
            else:
                break
    return i


def explain_flags(piv_flag_value: int) -> str:
    _dict_hex = {"inactive": "0x0", "active": "0x1", "masked": "0x2",
                 "noresult": "0x4", "disabled": "0x8", "filtered": "0x10",
                 "interpolated": "0x20", "replaced": "0x40", "manualedit": "0x80"}
    _dict_int = {}
    for (k, v) in _dict_hex.items():
        _dict_int[k] = int(v, 16)

    def _int_string(val):

        for (k1, v1) in _dict_int.items():
            if v1 == val:
                return k1

        for (k1, v1) in _dict_int.items():
            for (k2, v2) in _dict_int.items():
                if v1 + v2 == val and v1 != v2:
                    return "%s+%s" % (k1, k2)

        for (k1, v1) in _dict_int.items():
            for (k2, v2) in _dict_int.items():
                for (k3, v3) in _dict_int.items():
                    if v1 + v2 + v3 == val and v1 != v2:
                        return "%s+%s+%s" % (k1, k2, k3)

    return _int_string(piv_flag_value)

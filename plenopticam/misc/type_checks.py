def isfloat(x):
    try:
        float(x)
    except TypeError:
        return False
    except ValueError:
        return False
    else:
        return True


def isint(x):
    try:
        a = float(x)
        b = int(a)
    except ValueError:
        return False
    else:
        return a == b


def islist(x):
    return True if x.count(',') > 0 else False


def isbool(x):
    return x.lower() in ("true", "false")


def str2type(x):
    try:
        if isint(x):
            return int(x)
        elif isfloat(x):
            return float(x)
        elif islist(x):
            return str2list(x)
        else:
            return x
    except:
        return x


def str2list(x):
    # remove list brackets from string
    if x.startswith('[') and x.endswith(']'):
        x = x[1:-1]

    try:
        x = [int(k) if isint(k) else float(k) if isfloat(k) else k for k in x.replace(' ', '').split(',')]
    except:
        return False

    return x


def rint(val):
    return int(round(val))

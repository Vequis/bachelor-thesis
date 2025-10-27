HELP = "Remove o último elemento: remove_last a b c -> ['a', 'b']"

def run(args):
    if not args:
        return []

    return list(args[:-1])

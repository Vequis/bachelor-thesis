def run(args):
    if not args:
        return 0.0

    out = {}

    counter = 0

    for arg in args:
        if type(arg) == list:
            out.update({"average_" + str(counter): sum(arg) / len(arg)})
            counter += 1

    return out
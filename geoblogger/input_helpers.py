def continue_or_exit(prompt=True, msg="Continue?"):
    if not prompt:
        return

    cont = raw_input("%s [y|n]: " % msg)
    if cont and cont.lower() != "y":
        print "Exiting"
        exit(0)


def continue_or_skip(prompt=True, msg="Continue?"):
    if not prompt:
        return

    cont = raw_input("%s [y|n]: " % msg)
    if cont and cont.lower() != "y":
        print "Skipping."
        return False

    return True

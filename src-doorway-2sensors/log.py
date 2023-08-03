import datetime


def msg(s):
    print(f"{datetime.datetime.now()}; {s}")


def debug(s):
    msg(s)


def info(s):
    msg(s)


def error(s):
    msg(s)

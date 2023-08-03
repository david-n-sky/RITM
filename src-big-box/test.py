r = 1
y = 1


def fun():
    if r == 1 and y == 1:  # motors are close
        return True
    elif r == 1 or y == 1:  # one of two
        return 'reopen'
    else:
        return False


if fun() == 'reopen':
    print('reopen')
elif not fun():
    print('open')
else:
    print('close')

# if fun():
#     print('close')
# else:
#     print('open')
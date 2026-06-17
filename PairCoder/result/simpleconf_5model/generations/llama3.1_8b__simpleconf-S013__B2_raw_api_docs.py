def use_then_with_restore(profiles):
    prod = profiles['prod']
    with_profile(prod, 'default')
    mid = conf.x
    return (mid, prod.x)
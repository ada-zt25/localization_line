import simpleconf

def switch_two_profiles(profiles):
    prod = profiles['prod']
    default = profiles['default']

    prod_x = prod.get('x')
    default.load()
    default_x = default.get('x')
    default.unload()

    return (prod_x, default_x)
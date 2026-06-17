import simpleconf

def double_use_persistent(profiles):
    with Config(profiles) as conf:
        conf.set('profile', 'prod')
        conf.save()
        conf.switch('prod', persistent=True)
        conf.set('profile', 'default')
        conf.save()
        conf.switch('default', persistent=True)
        return conf.x
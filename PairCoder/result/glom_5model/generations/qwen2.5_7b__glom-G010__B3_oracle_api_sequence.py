def summarize(data):
    return glom(data, {
        'total': Coalesce(Assign('sum', T['nums'] | sum)),
        'count': Coalesce(Assign('len', T['nums'] | len))
    })
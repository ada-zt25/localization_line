def summarize(data):
    return glom(data, {
        'total': Coalesce(Assign('0'), Path('nums') | sum),
        'count': Coalesce(Assign('0'), Path('nums') | len)
    })
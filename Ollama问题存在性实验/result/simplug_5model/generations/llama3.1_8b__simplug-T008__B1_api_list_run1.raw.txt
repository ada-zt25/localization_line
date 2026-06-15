from simplug import Simplug
sp, alpha, beta, gamma = make_last_score_manager()

def last_score(value):
    return sp.hooks.score(value)
from simplug import Simplug
sp, alpha, beta, gamma = make_score_manager()

def only_beta_score(value):
    with sp.plugins_context(["beta"]):
        return sp.hooks.score(value)
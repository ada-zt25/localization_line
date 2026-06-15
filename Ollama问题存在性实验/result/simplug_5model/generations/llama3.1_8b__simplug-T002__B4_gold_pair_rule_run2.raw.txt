from simplug import Simplug
sp, alpha, beta, gamma = make_score_manager()

def only_alpha_gamma_score(value):
    with sp.plugins_context(["alpha", "gamma"]):
        return sp.hooks.score(value)
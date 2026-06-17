from simplug import Simplug

def only_beta_score(value):
    sp, _, beta, _ = make_score_manager()
    with sp.plugins_context(plugins=(beta,)):
        return sp.hooks.score(value)
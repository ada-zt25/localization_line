from simplug import Simplug
sp, alpha, beta, gamma = make_score_manager()

def get_beta_wrapper_disable_then_score(value):
    wrapper = sp.get_plugin('beta')
    wrapper.disable()
    return sp.hooks.score(value)
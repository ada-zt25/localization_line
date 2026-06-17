from simplug import Simplug

def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([alpha]):
        alpha.disable()
    with sp.plugins_context([gamma]):
        gamma.disable()
    result = sp.hooks.score(value)
    return result
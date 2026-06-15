def only_alpha_gamma_score(value):
    with plugins_context([alpha, gamma]):
        sp.hooks.score(value)
        sp.hooks.score(value, disable=[beta])
        results = sp.hooks.results()
        return results[alpha.name] if alpha.name in results else None
from contextlib import ExitStack

def atomic_add(A, batch):
    with ExitStack() as stack:
        temp = OrderedBidict()
        try:
            for key, value in batch:
                temp.forceput(key, value)
            A.putall(temp)
            result = dict(A)
        except (ValueDuplicationError, KeyDuplicationError, DuplicationError) as e:
            result = {}
        stack.enter_context(frozenbidict(A))
    return result
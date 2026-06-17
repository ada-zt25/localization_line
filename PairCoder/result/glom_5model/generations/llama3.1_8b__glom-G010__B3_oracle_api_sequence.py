def summarize(data):
    return glom(data, 'nums[*].total(count) + nums[*].value(coalesce=0)')
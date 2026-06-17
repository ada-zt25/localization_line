def switch_two_profiles(profiles):
  prod = profiles['prod']
  default = profiles['default']
  prod_x = prod.get('x')
  default.switch_profile('prod')
  default_x = default.get('x')
  return (prod_x, default_x)
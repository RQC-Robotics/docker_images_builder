from gen_setings import ex

cfg_list = ['ssh', 'conda', 'github', 'sensor']
ex.run(named_configs=['base'] + cfg_list + ['post_cfg'])

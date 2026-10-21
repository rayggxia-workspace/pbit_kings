"""Identify the user-selected original backend release, not a new/DC netlist."""
OLD_NETLIST_SHA256 = '0570bcffafb4be8cd807b6e58477f122045f7c0f7b8ff7a6d875f61b61054e22'
OLD_BASELINE = 'backend_20261009_111934'


def old_baseline(digest):
    if digest != OLD_NETLIST_SHA256:
        raise ValueError('Wrong netlist revision: expected original sdf_netlist_261010/pbit_io_wrapper.vg '
                         '(SHA256 '+OLD_NETLIST_SHA256+'), got '+digest+
                         '. Upload the original file without text conversion; do not substitute the new PT netlist.')
    return dict(id=OLD_BASELINE,generated_on='2026-10-09 11:19:34',sha256=digest)
